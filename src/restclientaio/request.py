
from copy import deepcopy
from typing import Any, AsyncIterable, AsyncIterator, Awaitable, Callable, \
    Dict, Mapping, Optional, Sequence

import aiohttp
from aiostream import stream

__all__ = ('Request', 'Response', 'Handler', 'http', 'check_status',
           'inject_params', 'unwrap', 'Paging', 'Requester')


class Request:

    def __init__(
        self,
        method: str = 'GET',
        url: str = None,
        params: Dict[str, str] = None,
        data: Dict[str, Any] = None,
        form_data: Dict[str, str] = None,
        headers: Dict[str, str] = None,
        meta: Dict[str, Any] = None,
    ) -> None:
        self.method = method
        self.url = url
        self.params = params or {}
        self.data = data or {}
        self.form_data = form_data or {}
        self.headers = headers or {}
        self.meta = meta or {}

    def copy(self) -> 'Request':
        return deepcopy(self)


class Response:

    def __init__(
        self,
        status: int = None,
        reason: str = None,
        headers: Mapping[str, str] = None,
        data: Any = None,
        extra: Dict[str, Any] = None,
    ) -> None:
        self.status = status
        self.reason = reason
        self.headers = headers or {}
        self.data = data
        self.extra = extra or {}

    def copy_no_data(self) -> 'Response':
        data = self.data
        headers = self.headers
        self.data = None
        self.headers = None
        c = deepcopy(self)
        self.data = data
        self.headers = headers
        c.headers = headers
        return c


Handler = Callable[[Request], Awaitable[Response]]


def http(session: aiohttp.ClientSession) -> Handler:
    async def handler(request: Request) -> Response:
        async with session.request(
            request.method,
            request.url,
            params=request.params or None,
            data=request.form_data or None,
            json=request.data or None,
            headers=request.headers or None,
        ) as response:
            return Response(
                status=response.status,
                reason=response.reason,
                headers=response.headers,
                data=await response.json(encoding='utf-8'),
            )
    return handler


def check_status(next_handler: Handler) -> Handler:
    async def handler(request: Request) -> Response:
        response = await next_handler(request)
        if response.status >= 400:
            raise Exception(
                f'HTTP response: {response.status} {response.reason}',
            )
        return response
    return handler


def inject_params(next_handler: Handler, **params: str) -> Handler:
    async def handler(request: Request) -> Response:
        request.params.update(params)
        return await next_handler(request)
    return handler


def unwrap(next_handler: Handler) -> Handler:
    async def handler(request: Request) -> Response:
        key = request.meta.get('key')
        response = await next_handler(request)
        if key and isinstance(response.data, dict) and key in response.data:
            old_data = response.data
            response.data = response.data[key]
            for k, v in old_data.items():
                if k != key:
                    response.extra[k] = v
        return response
    return handler


class Paging:

    def __init__(self, next_handler: Handler) -> None:
        self._next_handler = next_handler

    def set_first(self, request: Request) -> Request:
        return request

    def set_next(self, request: Request, last: Response) -> Optional[Request]:
        return None  # pragma: no cover

    async def __call__(self, request: Request) -> Response:
        next_handler = self._next_handler
        req = self.set_first(request.copy())
        response = await next_handler(req)
        combined_response = response.copy_no_data()
        if not isinstance(response.data, (Sequence, AsyncIterable)):
            raise Exception('Page is not iterable')

        async def data_iter() -> AsyncIterator[Any]:
            nonlocal req
            nonlocal response
            while req:
                if not isinstance(response.data, (Sequence, AsyncIterable)):
                    raise Exception('Page is not iterable')
                async with stream.iterate(response.data).stream() as s:
                    async for item in s:
                        yield item
                req = self.set_next(request.copy(), response)
                if req:
                    response = await next_handler(req)

        combined_response.data = data_iter()
        return combined_response


class Requester:

    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url
        self.get_handler = http(session)
        self.list_handler = self.get_handler

    async def get(self, meta: Dict[str, Any]) -> Any:
        return (await self.get_handler(Request(
            'GET', self._base_url + meta['uri'],
            params=meta.get('params'),
            meta=meta,
        ))).data

    async def list(self, meta: Dict[str, Any]) -> Any:
        return (await self.list_handler(Request(
            'GET', self._base_url + meta['uri'],
            params=meta.get('params'),
            meta=meta,
        ))).data
