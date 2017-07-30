
from typing import Any, ClassVar

__all__ = ('Resource', 'ResourceError')


class ResourceError(Exception):
    pass


class Resource:
    _Meta: ClassVar[Any]

    def __repr__(self) -> str:
        cls = type(self)
        idattr = getattr(getattr(cls, '_Meta', None), 'id', 'id')
        idvalue = getattr(self, idattr, None)
        return f'<{cls.__module__}.{cls.__qualname__} {idattr}={idvalue!r}>'
