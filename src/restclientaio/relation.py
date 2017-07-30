
import asyncio
import importlib
from typing import Any, AsyncIterable, Awaitable, Callable, Dict, Generic, \
    Sequence, Type, TypeVar, Union, cast

from .collection import Collection
from .hydrator import HydrationTypeError, Serializer
from .manager import Resource, ResourceManager

__all__ = (
    'OneToMany',
    'ManyToOne',
    'OneToManySerializer',
    'ManyToOneSerializer',
)

R = TypeVar('R', bound=Resource)
S = TypeVar('S', bound=Resource)


class Relation(Generic[R]):

    def __init__(
        self,
        target_class: Union[Type[R], str],
        field: str = None,
        **kwargs: Any,
    ) -> None:
        self.field = field
        self._target_class = target_class
        self._meta = kwargs

    def target_class(self, owner: Type[S]) -> Type[R]:
        if isinstance(self._target_class, str):
            module = importlib.import_module(owner.__module__)
            cls = cast(Type[R], getattr(module, self._target_class, None))
            if cls is None:
                raise NameError(
                    f"Class '{owner.__module__}.{self._target_class}' "
                    f'is not defined',
                )
            self._target_class = cls
        return self._target_class

    def meta(self, instance: S) -> Dict[str, Any]:
        meta = {}
        for k, v in self._meta.items():
            if isinstance(v, str):
                meta[k] = v.format(instance)
            elif isinstance(v, dict):
                for knested, vnested in v.items():
                    if isinstance(vnested, str):
                        v[knested] = vnested.format(instance)
        return meta

    def __set_name__(self, owner: Type[S], name: str) -> None:
        self._name = name


class OneToMany(Relation[R]):

    def __get__(
        self,
        instance: S,
        owner: Type[S],
    ) -> Collection[R]:
        if instance is None:
            return self  # type: ignore

        return cast(Collection[R], instance.__dict__.get(self._name))

    def __set__(
        self,
        instance: S,
        value: Union[Sequence[R], AsyncIterable[R]],
    ) -> None:
        instance.__dict__[self._name] = Collection(value)


class ManyToOne(Relation[R]):

    def __get__(
        self,
        instance: S,
        owner: Type[S],
    ) -> Awaitable[R]:
        if instance is None:
            return self  # type: ignore

        async def get() -> R:
            value = instance.__dict__.get(self._name)
            if asyncio.iscoroutinefunction(value):
                value = instance.__dict__[self._name] = await value()
            return cast(R, value)
        return get()

    def __set__(
        self,
        instance: S,
        value: Union[R, Callable[[], Awaitable[R]]],
    ) -> None:
        instance.__dict__[self._name] = value


class RelationSerializer(Serializer):

    def __init__(
        self, resource_manager: Callable[[], ResourceManager],
    ) -> None:
        self._rm = resource_manager


class OneToManySerializer(RelationSerializer):

    supported_descriptors = {OneToMany}

    def load(self, descriptor: Any, value: Any, resource: object) -> Any:
        if value is not None and not isinstance(value, Sequence):
            raise HydrationTypeError(Sequence, value)
        cls = type(resource)
        target_cls = descriptor.target_class(cls)
        if value is None:
            async def get() -> AsyncIterable[Resource]:
                meta = descriptor.meta(resource)
                async for r in self._rm().list(target_cls, meta):
                    yield r
            return get()
        return [self._rm()._get_or_instantiate(target_cls, e) for e in value]


class ManyToOneSerializer(RelationSerializer):

    supported_descriptors = {ManyToOne}

    def load(self, descriptor: Any, value: Any, resource: object) -> Any:
        types = (dict, int, str)
        if value is None:
            return None
        if not isinstance(value, types):
            raise HydrationTypeError(types, value)
        cls = type(resource)
        target_cls = descriptor.target_class(cls)
        meta = descriptor.meta(resource)
        if isinstance(value, dict):
            return self._rm()._get_or_instantiate(target_cls, value)

        # assume it's id
        async def get() -> Resource:
            return await self._rm().get(target_cls, value, meta)
        return get
