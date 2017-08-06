
from typing import Any, ClassVar

from ._util import full_name

__all__ = ('Resource', 'ResourceError')


class ResourceError(Exception):
    """Base resource error."""

    pass


class Resource:
    """Base model class."""

    _Meta: ClassVar[Any]

    def __repr__(self) -> str:
        cls = type(self)
        idattr = getattr(getattr(cls, '_Meta', None), 'id', 'id')
        idvalue = getattr(self, idattr, None)
        return f'<{full_name(cls)} {idattr}={idvalue!r}>'
