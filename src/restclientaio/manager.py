
from collections import defaultdict
from typing import Any, AsyncIterable, AsyncIterator, Dict, Sequence, Type, \
    TypeVar, cast
from weakref import WeakValueDictionary

from aiostream import stream

from .hydrator import Hydrator
from .request import Requester
from .resource import Resource, ResourceError

__all__ = ('Resource', 'ResourceManager')

R = TypeVar('R', bound=Resource)


class ResourceManager:

    def __init__(self, requester: Requester, hydrator: Hydrator) -> None:
        self._requester = requester
        self._hydrator = hydrator
        self._identity_map = defaultdict(lambda: WeakValueDictionary()) \
            # type: Dict[Type[Resource], WeakValueDictionary[Any, Resource]]

    def _get_meta(
        self,
        cls: Type[R],
        action: str,
        overrides: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        if hasattr(cls, '_Meta'):
            meta = getattr(cls._Meta, action, {})
        meta.update(overrides)
        return meta

    def _get_id_attr(self, resource_class: Type[R]) -> str:
        return str(getattr(getattr(resource_class, '_Meta', None), 'id', 'id'))

    def get_id(self, resource: R) -> Any:
        idattr = self._get_id_attr(type(resource))
        return getattr(resource, idattr, None)

    def is_new(self, resource: R) -> Any:
        return self.get_id(resource) is None

    def _track(self, resource: R) -> None:
        id = self.get_id(resource)  # noqa: B001
        if id is not None:
            self._identity_map[type(resource)][id] = resource

    def _get_or_instantiate(
        self,
        resource_class: Type[R],
        data: Dict[str, Any],
    ) -> R:
        if not isinstance(data, dict):
            raise ResourceError(f'Expected a dict, got {type(data)!r}')

        idattr = self._get_id_attr(resource_class)
        id = data.get(idattr)  # noqa: B001

        resource = cast(R, self._identity_map[resource_class].get(id))
        if resource is None:
            resource = self.new(resource_class)
        self._hydrator.hydrate(resource, data)
        self._track(resource)
        return resource

    async def get(
        self,
        resource_class: Type[R],
        id: Any,
        meta: Dict[str, Any] = {},
    ) -> R:
        idattr = self._get_id_attr(resource_class)
        meta = self._get_meta(resource_class, 'get', meta)
        meta[idattr] = id
        meta['uri'] = meta['uri'].format(**{idattr: id or ''})
        response = await self._requester.get(meta)
        return self._get_or_instantiate(resource_class, response)

    async def list(
        self,
        resource_class: Type[R],
        meta: Dict[str, Any] = {},
    ) -> AsyncIterator[R]:
        meta = self._get_meta(resource_class, 'list', meta)
        response = await self._requester.list(meta)
        if not isinstance(response, (Sequence, AsyncIterable)):
            raise ResourceError(
                f'Expected an iterable, got {type(response)!r}',
            )
        async with stream.iterate(response).stream() as s:
            async for data in s:
                yield self._get_or_instantiate(resource_class, data)

    def new(
        self,
        resource_class: Type[R],
        data: Dict[str, Any] = {},
    ) -> R:
        if not isinstance(data, dict):
            raise ResourceError(f'Expected a dict, got {type(data)!r}')

        resource = resource_class()
        self._hydrator.hydrate(resource, data, force_clear=True)
        return resource

    async def save(self, resource: R, meta: Dict[str, Any] = {}) -> None:
        data = self._hydrator.dehydrate(resource)
        if self.is_new(resource):
            meta = self._get_meta(type(resource), 'create', meta)
            data = await self._requester.create(meta, data)
        else:
            meta = self._get_meta(type(resource), 'update', meta)
            data = await self._requester.update(meta, data)

        if data and isinstance(data, dict):
            self._hydrator.hydrate(resource, data)
        self._track(resource)

    def detach(
        self,
        resource: Resource,
    ) -> None:
        id = self.get_id(resource)  # noqa: B001
        if id:
            try:
                del self._identity_map[type(R)][id]
            except KeyError:
                pass

    def clear(self) -> None:
        self._identity_map.clear()
