
from typing import Any, Generic, Type, TypeVar

from .collection import Collection
from .manager import ResourceManager
from .resource import Resource

__all__ = ('Repository',)

R = TypeVar('R', bound=Resource)


class Repository(Generic[R]):
    """Repository for single type of objects.

    :param resource_manager:
    :param resource_class:
    """

    def __init__(
        self,
        resource_manager: ResourceManager,
        resource_class: Type[R],
    ) -> None:
        self._resource_manager = resource_manager
        self._resource_class = resource_class

    def all(self) -> Collection[R]:
        """Return collection of all resources in this repository."""
        return self.filter()

    def filter(self, **kwargs: Any) -> Collection[R]:
        """Return collection of resources filtered by given criteria.

        :param kwargs: Filter criteria, passed as 'params' to
            `.ResourceManager.list`.
        """
        return Collection(self._resource_manager.list(
            self._resource_class,
            meta={'params': kwargs},
        ))

    async def get(self, id: Any) -> R:
        """Fetch resource by id.

        :param id:
        """
        return await self._resource_manager.get(
            self._resource_class,
            id=id,
        )

    def new(self) -> R:
        """Create a new instance, but don't save it."""
        return self._resource_manager.new(self._resource_class)

    async def save(self, resource: R) -> None:
        """Save resource.

        :param resource: The resource to save.
        """
        if not isinstance(resource, self._resource_class):
            raise ValueError('Resource does not belong to this repository')
        await self._resource_manager.save(resource)
