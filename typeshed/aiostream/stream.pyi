
from typing import List, Iterable, Awaitable, AsyncIterable, \
        AsyncContextManager, Union, TypeVar

_T = TypeVar('_T')

class Stream(AsyncIterable[_T], Awaitable[_T]):
    def stream(self) -> 'Streamer': ...
    def __getitem__(self, index: Union[int, slice]) -> Stream[_T]: ...

class Streamer(Stream[_T], AsyncContextManager['Streamer[_T]']):
    pass

def iterate(source: Union[Iterable[_T], AsyncIterable[_T]]) -> Stream[_T]: ...
async def list(source: AsyncIterable[_T]) -> List[_T]: ...
