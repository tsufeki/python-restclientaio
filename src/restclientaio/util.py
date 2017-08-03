
from typing import Type

__all__ = ('full_attr_name',)


def full_attr_name(cls: Type, attr: str) -> str:
    return f'{cls.__module__}.{cls.__qualname__}.{attr}'
