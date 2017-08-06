
from typing import Type

__all__ = ('full_name',)


def full_name(cls: Type, attr: str = None) -> str:
    s = f'{cls.__module__}.{cls.__qualname__}'
    if attr:
        s += f'.{attr}'
    return s
