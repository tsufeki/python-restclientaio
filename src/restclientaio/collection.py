
from typing import Any, AsyncIterable, AsyncIterator, List, Sequence, \
    TypeVar, Union, overload

from aiostream import stream

__all__ = ('Collection',)

T = TypeVar('T')


class Collection(AsyncIterable[T]):

    def __init__(
        self,
        collection: Union[Sequence[T], AsyncIterable[T]] = (),
    ) -> None:
        if isinstance(collection, Sequence):
            self._collection = collection
        else:
            self._collection = None
            self._aiterable = collection

    @property
    def loaded(self) -> bool:
        return self._collection is not None

    async def to_list(self) -> List[T]:
        return await self[:]

    async def __aiter__(self) -> AsyncIterator[T]:
        if self.loaded:
            for item in self._collection:
                yield item
        else:
            collection = []
            async with stream.iterate(self._aiterable).stream() as s:
                async for item in s:
                    collection.append(item)
                    yield item
            self._collection = collection

    @overload
    async def __getitem__(self, index: int) -> T:  # pragma: no cover
        pass

    @overload  # noqa: F811
    async def __getitem__(self, index: slice) -> List[T]:  # pragma: no cover
        pass

    async def __getitem__(self, index: Any) -> Any:  # noqa: F811
        if self.loaded:
            result = self._collection[index]
            if isinstance(index, slice) and not isinstance(result, list):
                result = list(result)
            return result
        else:
            s = stream.iterate(self)[index]
            if isinstance(index, slice):
                return await stream.list(s)
            else:
                return await s
