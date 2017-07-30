
from typing import AsyncIterable, Awaitable, AsyncContextManager, TypeVar

_T = TypeVar('_T')

class AsyncIteratorContext(AsyncIterable[_T], AsyncContextManager[AsyncIterable[_T]]): ...

def aitercontext(ait: AsyncIterable[_T]) -> AsyncIteratorContext[_T]: ...
def anext(ait: AsyncIterable[_T]) -> Awaitable[_T]: ...