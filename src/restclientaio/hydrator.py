
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Callable, Dict, Sequence, Set, Tuple, Type, Union

from .resource import ResourceError

__all__ = (
    'Hydrator',
    'Serializer',
    'HydrationTypeError',
    'ScalarSerializer',
    'DateTimeSerializer',
)

Types = Union[Type, Tuple[Type, ...]]


class HydrationTypeError(ResourceError):

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
            attr_desc = f' for {self.cls.__module__}.{self.cls.__qualname__}' \
                f'.{self.attr}'
        expected_types = ' or '.join(t.__name__ for t in self.expected_types)
        return f'{self.msg}{attr_desc}: expected {expected_types}, ' \
            f'got {self.actual_value!r:.50s}'


class Serializer:

    supported_annotations: Set[Type] = set()
    supported_descriptors: Set[Type] = set()

    def load(self, typ: Any, value: Any, resource: object) -> Any:
        pass  # pragma: no cover


class ScalarSerializer(Serializer):

    supported_types: Dict[Type, Types] = {
        None: (str, int, float, bool),
        type(None): (str, int, float, bool),
        str: str,
        int: int,
        float: (float, int),
        bool: bool,
    }
    supported_annotations = set(supported_types.keys())

    def load(self, typ: Any, value: Any, resource: object) -> Any:
        types = self.supported_types[typ]
        if value is None:
            return value
        if not isinstance(value, types) or \
                (typ is not bool and type(value) is bool):
            raise HydrationTypeError(types, value)
        return value


class DateTimeSerializer(Serializer):

    supported_annotations = {date, datetime}

    def __init__(
        self,
        date_fmt: str = '%Y-%m-%d',
        datetime_fmt: str = '%Y-%m-%dT%H:%M:%SZ',
    ) -> None:
        self.date_fmt = date_fmt
        self.datetime_fmt = datetime_fmt

    def load(self, typ: Any, value: Any, resource: object) -> Any:
        if value is None:
            return value
        if not isinstance(value, str):
            raise HydrationTypeError(typ, value)
        try:
            if typ is datetime:
                return datetime.strptime(value, self.datetime_fmt)
            if typ is date:  # pragma: no branch
                return datetime.strptime(value, self.date_fmt).date()
        except ValueError:
            raise HydrationTypeError(typ, value, msg='Bad format')


class Hydrator:

    def __init__(self, serializers: Sequence[Serializer]) -> None:
        self._annotation_serializers = {}  # type: Dict[Type, Serializer]
        self._descriptor_serializers = {}  # type: Dict[Type, Serializer]
        for serializer in serializers:
            for typ in serializer.supported_annotations:
                self._annotation_serializers[typ] = serializer
            for typ in serializer.supported_descriptors:
                self._descriptor_serializers[typ] = serializer

    def hydrate(
        self,
        resource: object,
        data: Dict[str, Any],
        force_clear: bool = False,
    ) -> None:
        cls = type(resource)
        fields, renames = self._get_fields(cls)
        for k, loader in fields.items():
            try:
                orig_k = renames.get(k, k)
                if orig_k in data or force_clear:
                    v = loader(data.get(orig_k), resource)
                    setattr(resource, k, v)
            except HydrationTypeError as e:
                e.cls = type(resource)
                e.attr = k
                raise

    @lru_cache(maxsize=64)
    def _get_fields(
        self,
        cls: Type,
    ) -> Tuple[Dict[str, Callable[[Any, object], Any]], Dict[str, str]]:
        fields: Dict[str, Callable[[Any, object], Any]] = {}
        renames: Dict[str, str] = {}
        for k, typ in getattr(cls, '__annotations__', {}).items():
            serializer = self._annotation_serializers.get(typ)
            if k and k[0] != '_' and serializer:

                def load_annotation(
                    value: Any,
                    resource: object,
                    typ: Any = typ,
                    serializer: Serializer = serializer,
                ) -> Any:
                    return serializer.load(typ, value, resource)
                fields[k] = load_annotation

        for k in dir(cls):
            if k and k[0] != '_':
                descr = cls.__dict__.get(k)
                serializer = self._descriptor_serializers.get(type(descr))
                if serializer:
                    renamed_k = getattr(descr, 'field', None)
                    if renamed_k and k != renamed_k:
                        renames[k] = renamed_k

                    def load_descriptor(
                        value: Any,
                        resource: object,
                        descr: Any = descr,
                        serializer: Serializer = serializer,
                    ) -> Any:
                        return serializer.load(descr, value, resource)
                    fields[k] = load_descriptor
        return fields, renames
