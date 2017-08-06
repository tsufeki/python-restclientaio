"""Serialization and deserialization of object to and from JSON."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from functools import lru_cache
from typing import AbstractSet, Any, Awaitable, Callable, ClassVar, Dict, \
    Generic, Sequence, Tuple, Type, TypeVar, Union, cast

from ._util import full_name
from .resource import ResourceError

__all__ = (
    'Hydrator',
    'HydrationTypeError',
    'BaseDescriptor',
    'Descriptor',
    'AwaitableDescriptor',
    'annotation_descriptor',
    'BaseAnnotationDescriptor',
    'Serializer',
    'ScalarSerializer',
    'DateTimeSerializer',
)

Types = Union[Type, Tuple[Type, ...]]
T = TypeVar('T')
U = TypeVar('U')
D = TypeVar('D', bound='BaseDescriptor')


class HydrationTypeError(ResourceError):
    """Field can't be (de-)serialized because of wrong type of its value."""

    def __init__(
        self,
        expected_types: Types,
        actual_value: Any,
        cls: Type = None,
        attr: str = None,
        msg: str = 'Wrong type',
    ) -> None:
        if not isinstance(expected_types, Sequence):
            expected_types = (expected_types,)
        self.expected_types = expected_types
        self.actual_value = actual_value
        self.cls = cls
        self.attr = attr
        self.msg = msg

    def __str__(self) -> str:
        attr_desc = ''
        if self.cls and self.attr:
            attr_desc = f' for {full_name(self.cls, self.attr)}'
        expected_types = ' or '.join(t.__name__ for t in self.expected_types)
        return f'{self.msg}{attr_desc}: expected {expected_types}, ' \
            f'got {self.actual_value!r:.50s}'


class BaseDescriptor(Generic[T]):
    """Base descriptor used to declare field on a model class.

    :param field: Override the key in the serialized dictionary. Default is
        the variable name this descriptor is assigned to.
    :param readonly: Don't allow setting the field by user code.

    Derived classes should return themselves when descriptor is used in class
    context.
    """

    def __init__(
        self,
        *, field: str = None,
        readonly: bool = False,
        name: str = None,
    ) -> None:
        self.field = field
        self.readonly = readonly
        self.name = name

    def __set_name__(self, owner: Type[U], name: str) -> None:
        if self.name is None:
            self.name = name
        if self.field is None:
            self.field = name


class Descriptor(BaseDescriptor[T]):
    """Simple eager field.

    Example::

        class Model:
            foo = Descriptor()

        m = Model()
        m.foo = 3
        print(m.foo)
    """

    def __get__(self, instance: U, owner: Type[U]) -> T:
        if instance is None:
            return self  # type: ignore
        return cast(T, instance.__dict__.get(self.name, None))

    def __set__(self, instance: U, value: T) -> None:
        if self.readonly:
            raise Exception(f'{full_name(type(instance), self.name)} '
                            f'is read-only')
        self.set(instance, value)

    def set(self, instance: U, value: T) -> None:
        """Set the field.

        This method is used when deserializing and works for read-only field
        as well.

        :param instance: Model instance to set the field on.
        :param value:
        """
        instance.__dict__[self.name] = value


class AwaitableDescriptor(BaseDescriptor[T]):
    """Lazy, async field.

    ``await`` should always be used when retrieving value.

    Example::

        class Model:
            foo = AwaitableDescriptor(readonly=True)

        async def main():
            m = Model()
            m.foo = 3
            print(await m.foo)
    """

    def __set_name__(self, owner: Type[U], name: str) -> None:
        super().__set_name__(owner, name)
        self._awaitable_name = f'_{self.name}__awaitable'

    def __get__(self, instance: U, owner: Type[U]) -> Awaitable[T]:
        if instance is None:
            return self  # type: ignore
        return self._get(instance)

    async def _get(self, instance: U) -> T:
        """Return value as awaitable."""
        d = instance.__dict__
        if self.name not in d:
            if self._awaitable_name in d:
                d[self.name] = await d[self._awaitable_name]()
                del d[self._awaitable_name]
            else:
                return None
        return cast(T, d[self.name])

    def __set__(self, instance: U, value: T) -> None:
        if self.readonly:
            raise Exception(f'{full_name(type(instance), self.name)} '
                            f'is read-only')
        self.set_instant(instance, value)

    def set_instant(self, instance: U, value: T) -> None:
        """Set the field with an instant (not lazy) value.

        This method is used when deserializing and works for read-only field
        as well.

        :param instance: Model instance to set the field on.
        :param value:
        """
        d = instance.__dict__
        d[self.name] = value
        try:
            del d[self._awaitable_name]
        except KeyError:
            pass

    def set_awaitable(
        self,
        instance: U,
        value: Callable[[], Awaitable[T]],
    ) -> None:
        """Set the field with a lazy value.

        This method is used when deserializing and works for read-only field
        as well.

        :param instance: Model instance to set the field on.
        :param value: A coroutine function (or any callable returning
            an awaitable) yielding a field value.
        """
        d = instance.__dict__
        d[self._awaitable_name] = value
        try:
            del d[self.name]
        except KeyError:
            pass


class Serializer(ABC, Generic[D]):
    """Abstract serializer.

    :ivar supported_descriptors: Set of descriptor types processable
        by this serializer.
    """

    supported_descriptors: AbstractSet[Type[D]] = set()

    @abstractmethod
    def load(self, descr: D, value: Any, resource: Any) -> None:
        """Deserialize value and set field on a model.

        :param descr: Descriptor instance.
        :param value: Serialized value.
        :param resource: Model instance.
        :raises HydrationTypeError:
        """
        pass

    @abstractmethod
    def dump(self, descr: D, resource: Any) -> Any:
        """Serialize field value.

        :param descr: Descriptor instance.
        :param resource: Model instance to retrieve field value from.
        :raises HydrationTypeError:
        """
        pass


class BaseAnnotationDescriptor(Descriptor[T]):

    typ: ClassVar[Type[T]]
    """Annotation type."""


@lru_cache(maxsize=None)
def annotation_descriptor(typ: Type[T]) -> Type[BaseAnnotationDescriptor[T]]:
    r"""Return a `Descriptor` class for given annotation type.

    Returned class can be used to register a serializer for a type annotated
    field (by including it in `Serializer`.\ ``supported_descriptors``).

    :param typ:
    """
    return type(
        'AnnotationDescriptor',
        (BaseAnnotationDescriptor[T],),
        {'typ': typ, '__module__': __name__},
    )


Scalar = Union[None, str, int, float, bool]


class ScalarSerializer(Serializer[BaseAnnotationDescriptor]):
    """Serializer for annotated scalar fields.

    Supports `str`, `int`, `float`, `bool`, `None` annotations.
    """

    _supported_types: Dict[Type[Scalar], Tuple[Type[Scalar], ...]] = {
        None: (str, int, float, bool),
        type(None): (str, int, float, bool),
        str: (str,),
        int: (int,),
        float: (float, int),
        bool: (bool,),
    }

    supported_descriptors = {
        annotation_descriptor(typ)
        for typ in _supported_types
    }

    def load(
        self,
        descr: BaseAnnotationDescriptor[Scalar],
        value: Any,
        resource: Any,
    ) -> None:
        types = self._supported_types[descr.typ]
        if value is not None and type(value) not in types:
            raise HydrationTypeError(types, value)
        descr.set(resource, value)

    def dump(
        self,
        descr: BaseAnnotationDescriptor[Scalar],
        resource: Any,
    ) -> Any:
        value = descr.__get__(resource, None)
        types = self._supported_types[descr.typ]
        if value is not None and type(value) not in types:
            raise HydrationTypeError(types, value)
        return value


class DateTimeSerializer(Serializer[BaseAnnotationDescriptor]):
    """Serializer for annotated `datetime.date` and `datetime.datetime` fields.

    :param date_fmt: Format of `datetime.date`, as
        in `datetime.datetime.strptime`.
    :param datetime_fmt: Format of `datetime.datetime`, as
        in `datetime.datetime.strptime`.
    """

    supported_descriptors = {
        annotation_descriptor(date),
        annotation_descriptor(datetime),
    }

    def __init__(
        self,
        date_fmt: str = '%Y-%m-%d',
        datetime_fmt: str = '%Y-%m-%dT%H:%M:%SZ',
    ) -> None:
        self.date_fmt = date_fmt
        self.datetime_fmt = datetime_fmt

    def load(
        self,
        descr: BaseAnnotationDescriptor[Union[date, datetime]],
        value: Any,
        resource: Any,
    ) -> None:
        if value is not None and not isinstance(value, str):
            raise HydrationTypeError(descr.typ, value)
        try:
            if value is not None:
                if descr.typ is datetime:
                    value = datetime.strptime(value, self.datetime_fmt)
                elif descr.typ is date:
                    value = datetime.strptime(value, self.date_fmt).date()
        except ValueError:
            raise HydrationTypeError(descr.typ, value, msg='Bad format')
        descr.set(resource, value)

    def dump(
        self,
        descr: BaseAnnotationDescriptor[Union[date, datetime]],
        resource: Any,
    ) -> str:
        value = descr.__get__(resource, None)
        if value is not None and not isinstance(value, (date, datetime)):
            raise HydrationTypeError(descr.typ, value)
        ret_value = None
        if value is not None:
            if descr.typ is datetime:
                ret_value = value.strftime(self.datetime_fmt)
            elif descr.typ is date:
                ret_value = value.strftime(self.date_fmt)
        return ret_value


class Hydrator:
    """Load and dump objects from and to JSON dict."""

    def __init__(self) -> None:
        self._serializers = {}  # type: Dict[Type, Serializer]

    def add_serializer(self, serializer: Serializer) -> None:
        """Register a field serializer."""
        for typ in serializer.supported_descriptors:
            self._serializers[typ] = serializer

    def hydrate(
        self,
        resource: Any,
        data: Dict[str, Any],
        force_clear: bool = False,
    ) -> None:
        """Deserialize data and set fields on resource.

        :param resource: Model instance to set fields on.
        :param data: A JSON dict with serialized fields.
        :param force_clear: If `True`, reset field when they are missing from
            data as well.
        """
        cls = type(resource)
        fields = self._get_fields(cls)
        for k, descr in fields.items():
            try:
                orig_k = descr.field or k
                if orig_k in data or force_clear:
                    serializer = self._serializers[type(descr)]
                    serializer.load(descr, data.get(orig_k), resource)
            except HydrationTypeError as e:
                e.cls = type(resource)
                e.attr = k
                raise

    def dehydrate(
        self,
        resource: Any,
    ) -> Dict[str, Any]:
        """Serialize object.

        :param resource: Model instance to serialize.
        """
        data: Dict[str, Any] = {}
        cls = type(resource)
        fields = self._get_fields(cls)
        for k, descr in fields.items():
            try:
                orig_k = descr.field or k
                if not descr.readonly:
                    serializer = self._serializers[type(descr)]
                    data[orig_k] = serializer.dump(descr, resource)
            except HydrationTypeError as e:
                e.cls = type(resource)
                e.attr = k
                raise
        return data

    @lru_cache(maxsize=64)
    def _get_fields(
        self,
        cls: Type,
    ) -> Dict[str, BaseDescriptor]:
        """Get fields definitions from class."""
        fields: Dict[str, BaseDescriptor] = {}
        descr: BaseDescriptor
        for k, typ in getattr(cls, '__annotations__', {}).items():
            descr = annotation_descriptor(typ)(name=k)
            if k and k[0] != '_':
                if type(descr) in self._serializers:
                    fields[k] = descr

        for k in dir(cls):
            descr = cls.__dict__.get(k)
            if k and k[0] != '_' and descr:
                if type(descr) in self._serializers:
                    fields[k] = descr

        return fields
