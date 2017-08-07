
from typing import Any, Set, Type, TypeVar, cast  # noqa: F401

__all__ = ('full_name', 'format_recur')

T = TypeVar('T')


def full_name(cls: Type, attr: str = None) -> str:
    """Get full name of a class or its attribute.

    :param cls:
    :param attr:
    """
    s = f'{cls.__module__}.{cls.__qualname__}'
    if attr:
        s += f'.{attr}'
    return s


def format_recur(value: T, *args: Any, **kwargs: Any) -> T:
    """Format string keys and values using `str.format` in *value* recursively.

    :param value:
    :param args: Passed to `str.format`.
    :param kwargs: Passed to `str.format`.
    """
    memo: Set[Any] = set()

    def format_value(val: Any) -> Any:
        if isinstance(val, str):
            return val.format(*args, **kwargs)
        if not isinstance(val, (list, dict)):
            return val

        val_id = id(val)
        if val_id in memo:
            raise ValueError('Self-referencing structure')
        memo.add(val_id)
        if isinstance(val, list):
            result: Any = [format_value(i) for i in val]
        if isinstance(val, dict):
            result = {format_value(k): format_value(v) for k, v in val.items()}
        memo.remove(val_id)
        return result

    return cast(T, format_value(value))
