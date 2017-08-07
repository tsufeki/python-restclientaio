"""Relations between resource types."""

import importlib
from functools import lru_cache
from typing import Any, AsyncIterable, Awaitable, Callable, Dict, Generic, \
    Sequence, Type, TypeVar, Union, cast

from ._util import format_recur
from .collection import Collection
from .hydrator import AwaitableDescriptor, BaseDescriptor, Descriptor, \
    HydrationTypeError, Serializer
from .manager import ResourceManager
from .resource import Resource, ResourceError

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
        save_field: str = None,
        readonly: bool = False,
        name: str = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(  # type: ignore
            field=field, save_field=save_field, readonly=readonly, name=name,
        )
        self._target_class = target_class
        self._meta = kwargs

    @lru_cache(maxsize=256)
    def target_class(self, owner: Type[S]) -> Type[R]:
        """Get class on the other side of this relation."""
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

    @lru_cache(maxsize=256)
    def meta(self, instance: S) -> Dict[str, Any]:
        """Get processed meta for this model instance."""
        return format_recur(self._meta, instance)


class OneToMany(Relation[R], Descriptor[Collection[R]]):
    r"""One to many relation.

    Example::

        class User(Resource):
            id: int

        class Group(Resource):
            users = OneToMany(User, params={'group_id': '{0.id}'})

    When accessed, returns a `.Collection`.

    When deserializing, related resources may be (partially) included
    in instance's JSON. They will be properly hydrated as much as possible
    without additional HTTP requests made.

    :param target_class: Target class or its name (useful for circular
        dependencies).
    :param field: Override the key in the serialized dictionary. Default is
        the variable name this descriptor is assigned to.
    :param save_field: Same as *field* but only for saving (serializing).
    :param readonly: Must be `True`, currently collections are not editable.
    :param kwargs: Rest of the parameters are `str.format`\ ed with instance
        as parameter ``0`` and passed to `.ResourceManager.list`.
    """

    def __init__(
        self,
        target_class: Union[Type[R], str],
        *, field: str = None,
        save_field: str = None,
        readonly: bool = True,
        name: str = None,
        **kwargs: Any,
    ) -> None:
        if not readonly:
            raise ValueError(f'{type(self).__name__}.readonly must be True')
        super().__init__(
            target_class, field=field, save_field=save_field,
            readonly=readonly, name=name, **kwargs,
        )


class ManyToOne(Relation[R], AwaitableDescriptor[R]):
    r"""Many to one relation.

    Example::

        class Group(Resource):
            id: int

        class User(Resource):
            group = ManyToOne(Group, field='group_id')

    When accessed returns an awaitable (to be used with ``await``).

    When deserializing, related resources may be (partially) included
    in instance's JSON. They will be properly hydrated as much as possible
    without additional HTTP requests made. Otherwise, data is assumed to be
    target object id.

    :param target_class: Target class or its name (useful for circular
        dependencies).
    :param field: Override the key in the serialized dictionary. Default is
        the variable name this descriptor is assigned to.
    :param save_field: Same as *field* but only for saving (serializing).
    :param readonly: Don't allow setting the field by user code.
    :param save_by_value: Whether to save by value or by id.
    :param kwargs: Rest of the parameters are `str.format`\ ed with instance
        as parameter ``0`` and passed to `.ResourceManager.get`.
    """

    def __init__(
        self,
        target_class: Union[Type[R], str],
        *, field: str = None,
        save_field: str = None,
        readonly: bool = False,
        name: str = None,
        save_by_value: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            target_class, field=field, save_field=save_field,
            readonly=readonly, name=name, **kwargs,
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
    """`OneToMany` serializer.

    :param resource_manager:
    """

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
    """`ManyToOne` serializer.

    :param resource_manager:
    """

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
