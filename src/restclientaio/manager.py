
from collections import defaultdict
from typing import Any, AsyncIterable, AsyncIterator, Dict, Sequence, Type, \
    TypeVar, cast
from weakref import WeakValueDictionary

from aiostream import stream

from .hydrator import Hydrator
from .request import Requester
from .resource import Resource, ResourceError

__all__ = ('ResourceManager',)

R = TypeVar('R', bound=Resource)


class ResourceManager:
    """Manages retrieval and saving of resource objects.

    Generally, this class should not be used directly -- use explicit
    `.Repository` for the wanted resource type instead.

    `ResourceManager` uses an identity map to avoid double-instantiating of
    resources if they have an id field.

    :param requester:
    :param hydrator:
    """

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
        """Get meta info for class and action, including overrides."""
        meta: Dict[str, Any] = {}
        if hasattr(cls, '_Meta'):
            meta = getattr(cls._Meta, action, {})
        meta.update(overrides)
        return meta

    def _get_id_attr(self, resource_class: Type[R]) -> str:
        """Get identifier attribute name, if any."""
        return str(getattr(getattr(resource_class, '_Meta', None), 'id', 'id'))

    def get_id(self, resource: R) -> Any:
        """Get identifier value, or `None`.

        :param resource:
        """
        idattr = self._get_id_attr(type(resource))
        return getattr(resource, idattr, None)

    def is_new(self, resource: R) -> Any:
        """Check if resource was created but not saved yet.

        :param resource:
        """
        return self.get_id(resource) is None

    def _track(self, resource: R) -> None:
        """Add resource to the identity map."""
        id = self.get_id(resource)  # noqa: B001
        if id is not None:
            self._identity_map[type(resource)][id] = resource

    def _get_or_instantiate(
        self,
        resource_class: Type[R],
        data: Dict[str, Any],
    ) -> R:
        """Return an object hydrated with `data`.

        If a matching object can be found in the identity map, use it,
        otherwise instatiate a new one.

        :param resource_class: Type of the resource.
        :param data:
        """
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
        """Fetch a resource by id.

        :param resource_class: Type of the resource.
        :param id: Identifier value.
        :param meta: Additional info to pass to the `.Requester`.
        """
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
        """Fetch a list of resources.

        :param resource_class: Type of the resource.
        :param meta: Additional info to pass to the `.Requester` (like filters,
            etc.).
        """
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
    ) -> R:
        """Create a new instance, but don't save it.

        :param resource_class: Type of the resource.
        """
        resource = resource_class()
        self._hydrator.hydrate(resource, {}, force_clear=True)
        return resource

    async def save(self, resource: R, meta: Dict[str, Any] = {}) -> None:
        """Save resource.

        :param resource: The resource to save.
        :param meta: Additional info to pass to the `.Requester`.
        """
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
