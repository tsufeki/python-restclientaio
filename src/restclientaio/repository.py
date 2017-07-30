
from typing import Any, Generic, Type, TypeVar

from .collection import Collection
from .manager import Resource, ResourceManager

__all__ = ('Repository',)

R = TypeVar('R', bound=Resource)


class Repository(Generic[R]):

    def __init__(
        self,
        resource_manager: ResourceManager,
        resource_class: Type[R],
    ) -> None:
        self._resource_manager = resource_manager
        self._resource_class = resource_class

    def all(self) -> Collection[R]:
        return self.filter()

    def filter(self, **kwargs: Any) -> Collection[R]:
        return Collection(self._resource_manager.list(
            self._resource_class,
            meta={'params': kwargs},
        ))

    async def get(self, id: Any, **kwargs: Any) -> R:
        return await self._resource_manager.get(
            self._resource_class,
            id=id,
            meta={'params': kwargs},
        )

    def new(self, **kwargs: Any) -> R:
        return self._resource_manager.new(self._resource_class, kwargs)
