
from collections import defaultdict
from typing import Any, AsyncIterable, AsyncIterator, Dict, Sequence, Type, \
    TypeVar, cast

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
        self._identity_map = defaultdict(lambda: {}) \
            # type: Dict[Type[Resource], Dict[Any, Resource]]

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
            if id is not None:
                self._identity_map[resource_class][id] = resource
        self._hydrator.hydrate(resource, data)
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
        return self._get_or_instantiate(resource_class, response.data)

    async def list(
        self,
        resource_class: Type[R],
        meta: Dict[str, Any] = {},
    ) -> AsyncIterator[R]:
        meta = self._get_meta(resource_class, 'list', meta)
        response = await self._requester.list(meta)
        if not isinstance(response.data, (Sequence, AsyncIterable)):
            raise ResourceError(
                f'Expected an iterable, got {type(response.data)!r}',
            )
        async with stream.iterate(response.data).stream() as s:
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

    def detach(
        self,
        resource: Resource,
    ) -> None:
        idattr = self._get_id_attr(type(resource))
        id = getattr(resource, idattr, None)  # noqa: B001
        if id:
            try:
                del self._identity_map[type(R)][id]
            except KeyError:
                pass

    def clear(self) -> None:
        self._identity_map.clear()
