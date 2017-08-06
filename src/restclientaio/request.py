"""Things related to making and processing HTTP requests."""

from copy import copy, deepcopy
from typing import Any, AsyncIterable, AsyncIterator, Awaitable, Callable, \
    Dict, Mapping, Optional, Sequence

import aiohttp
from aiostream import stream

__all__ = ('Request', 'Response', 'Handler', 'http', 'check_status',
           'inject_params', 'unwrap', 'Paging', 'Requester')


class Request:
    """Representation of HTTP request.

    :param method:
    :param url:
    :param params: "GET" query parameters.
    :param data: JSONable data to be included in body.
    :param form_data: "POST"-like form data dict.
    :param headers:
    :param meta: Additional info passed with this object.
    """

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
        """Make a deep copy."""
        return deepcopy(self)


class Response:
    """Representation of HTTP response.

    :param status:
    :param reason:
    :param headers:
    :param data: De-JSONed body.
    :param extra: Additional info passed with this object.
    """

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

    def copy_shallow(self) -> 'Response':
        """Make a shallow copy."""
        return copy(self)


Handler = Callable[[Request], Awaitable[Response]]
"""Middleware type."""


def http(session: aiohttp.ClientSession) -> Handler:
    """`aiohttp` based request handler.

    :param session:
    """
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
    """Raise an exception for status >= 400.

    :param next_handler:
    """
    async def handler(request: Request) -> Response:
        response = await next_handler(request)
        if response.status >= 400:
            raise Exception(
                f'HTTP response: {response.status} {response.reason}',
            )
        return response
    return handler


def inject_params(next_handler: Handler, **params: str) -> Handler:
    """Inject params into request.

    :param next_handler:
    :param params:
    """
    async def handler(request: Request) -> Response:
        request.params.update(params)
        return await next_handler(request)
    return handler


def unwrap(next_handler: Handler) -> Handler:
    """Unwrap data from containing `dict`.

    The key under which data is looked up should be passed in request's meta
    as 'key'.

    :param next_handler:
    """
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
    r"""Paging handler.

    This base implementation does not do anything. Subclass it and implement
    `set_first` and `set_next` method.

    `Response`.\ ``data`` must be a list when passed to this class. Use
    `unwrap` if necessary.

    Returned response will have a async iterator in ``data``.

    :param next_handler:
    """

    def __init__(self, next_handler: Handler) -> None:
        self._next_handler = next_handler

    def set_first(self, request: Request) -> Request:
        """Modify request for fetching first page of results.

        :param request:
        """
        return request

    def set_next(self, request: Request, last: Response) -> Optional[Request]:
        """Modify request for fetching subsequent pages.

        :param request:
        :param last: Response of the previous request.
        :return: Modified request or None if previous page was last.
        """
        return None  # pragma: no cover

    async def __call__(self, request: Request) -> Response:
        next_handler = self._next_handler
        req = self.set_first(request.copy())
        response = await next_handler(req)
        combined_response = response.copy_shallow()
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
    r"""Prepare and execute HTTP requests for resources.

    This is very basic implementation and should be sub-classed to make it
    useful.

    meta `dict`\ s passed to methods should generally have 'uri' key, which
    will be concatenated with *base_url*.

    :param base_url:
    :param session: `aiohttp` client session.
    """

    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url
        self.get_handler = http(session)
        self.list_handler = self.get_handler
        self.create_handler = self.get_handler
        self.update_handler = self.get_handler

    async def get(self, meta: Dict[str, Any]) -> Any:
        """Fetch single resource by id.

        :param meta: 'id' key should be included.
        """
        return (await self.get_handler(Request(
            'GET', self._base_url + meta['uri'],
            params=meta.get('params'),
            meta=meta,
        ))).data

    async def list(self, meta: Dict[str, Any]) -> Any:
        """Fetch list of resources, possibly filtered.

        :param meta: Can contain filters and other options.
        """
        return (await self.list_handler(Request(
            'GET', self._base_url + meta['uri'],
            params=meta.get('params'),
            meta=meta,
        ))).data

    async def create(self, meta: Dict[str, Any], data: Dict[str, Any]) -> Any:
        """Create a new resource.

        :param meta:
        :param data: Resource data.
        """
        return (await self.create_handler(Request(
            'POST', self._base_url + meta['uri'],
            params=meta.get('params'),
            meta=meta,
            data=data,
        ))).data

    async def update(self, meta: Dict[str, Any], data: Dict[str, Any]) -> Any:
        """Update an existing resource.

        :param meta:
        :param data: Resource data.
        """
        return (await self.update_handler(Request(
            'PUT', self._base_url + meta['uri'],
            params=meta.get('params'),
            meta=meta,
            data=data,
        ))).data
