
import importlib
from typing import Any, AsyncIterable, Awaitable, Callable, Dict, Generic, \
    Sequence, Type, TypeVar, Union, cast

from .collection import Collection
from .hydrator import AwaitableDescriptor, BaseDescriptor, Descriptor, \
    HydrationTypeError, Serializer
from .manager import Resource, ResourceError, ResourceManager

__all__ = (
    'OneToMany',
    'ManyToOne',
    'OneToManySerializer',
    'ManyToOneSerializer',
)

R = TypeVar('R', bound=Resource)
S = TypeVar('S', bound=Resource)
U = TypeVar('U')
D = TypeVar('D', bound=BaseDescriptor)


class Relation(Generic[R]):

    def __init__(
        self,
        target_class: Union[Type[R], str],
        *, field: str = None,
        readonly: bool = False,
        name: str = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(  # type: ignore
            field=field, readonly=readonly, name=name,
        )
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
                v = v.format(instance)
            elif isinstance(v, dict):
                for knested, vnested in v.items():
                    if isinstance(vnested, str):
                        v[knested] = vnested.format(instance)
            meta[k] = v
        return meta


class OneToMany(Relation[R], Descriptor[Collection[R]]):

    def __init__(
        self,
        target_class: Union[Type[R], str],
        *, field: str = None,
        readonly: bool = True,
        name: str = None,
        **kwargs: Any,
    ) -> None:
        if not readonly:
            raise ValueError(f'{type(self).__name__}.readonly must be True')
        super().__init__(
            target_class, field=field, readonly=readonly, name=name, **kwargs,
        )


class ManyToOne(Relation[R], AwaitableDescriptor[R]):

    def __init__(
        self,
        target_class: Union[Type[R], str],
        *, field: str = None,
        readonly: bool = False,
        name: str = None,
        save_by_value: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            target_class, field=field, readonly=readonly, name=name, **kwargs,
        )
        self.save_by_value = save_by_value

    def __set_name__(self, owner: Type[U], name: str) -> None:
        super().__set_name__(owner, name)
        self._id_name = f'_{self.name}__id'

    def get_id(self, instance: U) -> Any:
        return instance.__dict__.get(self._id_name)

    def get_instant(self, instance: U) -> R:
        return cast(R, instance.__dict__.get(self.name))

    def set_instant(self, instance: U, value: R) -> None:
        super().set_instant(instance, value)
        instance.__dict__[self._id_name] = None

    def set_awaitable(
        self,
        instance: U,
        value: Callable[[], Awaitable[R]],
        id: Any = None,  # noqa: B002
    ) -> None:
        super().set_awaitable(instance, value)
        instance.__dict__[self._id_name] = id


class RelationSerializer(Serializer[D]):

    def __init__(self, resource_manager: ResourceManager) -> None:
        self._manager = resource_manager


class OneToManySerializer(RelationSerializer[OneToMany[R]]):

    supported_descriptors = {OneToMany}

    def load(
        self,
        descr: OneToMany[R],
        value: Any,
        resource: Any,
    ) -> None:
        if value is not None and not isinstance(value, Sequence):
            raise HydrationTypeError(Sequence, value)
        cls = type(resource)
        target_cls = descr.target_class(cls)
        if value is None:
            async def get() -> AsyncIterable[R]:
                meta = descr.meta(resource)
                async for r in self._manager.list(target_cls, meta):
                    yield r
            coll = Collection(get())
        else:
            coll = Collection([
                self._manager._get_or_instantiate(target_cls, e)
                for e in value
            ])
        descr.set(resource, coll)

    def dump(
        self,
        descr: OneToMany[R],
        resource: Any,
    ) -> Any:
        raise NotImplementedError()


class ManyToOneSerializer(RelationSerializer[ManyToOne[R]]):

    supported_descriptors = {ManyToOne}

    def load(
        self,
        descr: ManyToOne[R],
        value: Any,
        resource: Any,
    ) -> None:
        types = (dict, int, str)
        if value is None:
            descr.set_instant(resource, value)
            return
        if not isinstance(value, types):
            raise HydrationTypeError(types, value)
        cls = type(resource)
        target_cls = descr.target_class(cls)
        meta = descr.meta(resource)
        if isinstance(value, dict):
            descr.set_instant(
                resource,
                self._manager._get_or_instantiate(target_cls, value),
            )
        else:
            # assume it's id
            async def get() -> R:
                return await self._manager.get(target_cls, value, meta)
            descr.set_awaitable(resource, get, id=value)

    def dump(
        self,
        descr: ManyToOne[R],
        resource: Any,
    ) -> Any:
        if descr.save_by_value:
            raise NotImplementedError()
        else:
            target = descr.get_instant(resource)
            id = descr.get_id(resource)  # noqa: B001
            if not id and target:
                id = self._manager.get_id(target)  # noqa: B001
                if not id:
                    raise ResourceError("Can't save many-to-one relation, "
                                        'target has no id')
            return id
