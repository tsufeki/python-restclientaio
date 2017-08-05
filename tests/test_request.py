
import aiohttp
import pytest

from restclientaio.request import *


async def coro(return_value=None):
    return return_value


class TestHttp:

    @pytest.mark.asyncio
    async def test_http(self, mocker):
        session = mocker.MagicMock(spec=aiohttp.ClientSession)
        aio_resp = mocker.Mock()
        aio_resp.status = 404
        aio_resp.reason = 'Not Found'
        aio_resp.headers = {'X-Response-Header': 'foo'}
        aio_resp.json.return_value = coro({'json': 'data'})
        aio_resp_class = type(session.request.return_value)
        aio_resp_class.__aexit__ = mocker.Mock(return_value=coro())
        aio_resp_class.__aenter__ = mocker.Mock(return_value=coro(aio_resp))

        req = Request(
            method='POST',
            url='http://example.com',
            params={'foo': 'x'},
            data={'bar': 'y'},
            headers={'X-Header': 'baz'},
        )
        resp = await http(session)(req)
        aio_req_args = session.request.call_args
        assert aio_req_args == (
            (req.method, req.url),
            {
                'params': req.params,
                'data': None,
                'json': req.data,
                'headers': req.headers,
            },
        )
        assert resp.status == 404
        assert resp.reason == 'Not Found'
        assert resp.headers == {'X-Response-Header': 'foo'}
        assert resp.data == {'json': 'data'}


def mock_handler(response, expected_request=None):
    async def handler(request):
        assert expected_request is None or \
            request.__dict__ == expected_request.__dict__
        return response
    return handler


class TestHandlers:

    @pytest.mark.parametrize('status', [200, 301])
    @pytest.mark.asyncio
    async def test_check_status_ok(self, status):
        req = Request()
        resp = Response(status=status)
        handler = mock_handler(resp, req)
        assert await check_status(handler)(req) == resp

    @pytest.mark.parametrize('status', [404, 500])
    @pytest.mark.asyncio
    async def test_check_status_not_ok(self, status):
        req = Request()
        resp = Response(status=status)
        handler = mock_handler(resp, req)
        with pytest.raises(Exception):
            await check_status(handler)(req)

    @pytest.mark.asyncio
    async def test_inject_params(self):
        req = Request(params={'foo': 'x', 'bar': 'y'})
        expected_request = req.copy()
        params = {'foo': 'z', 'baz': 'ww'}
        expected_request.params.update(params)
        resp = Response()
        handler = mock_handler(resp, expected_request)
        assert await inject_params(handler, **params)(req) == resp

    @pytest.mark.asyncio
    async def test_unwrap(self):
        req = Request(meta={'key': 'objects'})
        objects = [{'foo': 1}, {}]
        orig_resp = Response(data={'objects': objects, 'page': 1})
        handler = mock_handler(orig_resp, req)
        resp = await unwrap(handler)(req)
        assert resp.data == objects
        assert resp.extra == {'page': 1}

    @pytest.mark.asyncio
    async def test_unwrap_on_no_key(self):
        req = Request(meta={'key': 'objects'})
        data = []
        orig_resp = Response(data=data)
        handler = mock_handler(orig_resp, req)
        resp = await unwrap(handler)(req)
        assert resp.data == data
        assert resp.extra == {}

    def paging(self, pages):
        async def next_handler(request):
            nonlocal c
            c += 1
            return Response(data=pages[c])
        c = -1
        paging = Paging(next_handler)
        paging.set_next = lambda req, _: req if c + 1 < len(pages) else None
        return paging

    @pytest.mark.parametrize('pages,result', [
        ([[0, 1], [2], [3, 4]], [0, 1, 2, 3, 4]),
        ([[0]], [0]),
    ])
    @pytest.mark.asyncio
    async def test_paging(self, pages, result):
        paging = self.paging(pages)
        resp = await paging(Request())
        all_pages = []
        async for item in resp.data:
            all_pages.append(item)

        assert all_pages == result

    @pytest.mark.parametrize('pages', [
        [True],
        [[0, 1], True],
    ])
    @pytest.mark.asyncio
    async def test_paging_bad_type(self, pages):
        paging = self.paging(pages)
        with pytest.raises(Exception):
            resp = await paging(Request())
            async for item in resp.data:  # noqa: F841
                pass


class TestRequester:

    @pytest.mark.parametrize('action,method,kwargs', [
        ('get', 'GET', {}),
        ('list', 'GET', {}),
        ('create', 'POST', {'data': {}}),
        ('update', 'PUT', {'data': {}}),
    ])
    @pytest.mark.asyncio
    async def test_requester(self, action, method, kwargs, mocker):
        http = mocker.patch('restclientaio.request.http', autospec=True)
        data = {'foo': 'bar'}
        http.return_value.return_value = coro(Response(data=data))
        requester = Requester('http://example.com', mocker.Mock())
        result = await getattr(requester, action)(
            dict(
                uri='/foo.json',
                params={'bar': 'baz'},
            ),
            **kwargs,
        )
        req = http.return_value.call_args[0][0]
        assert isinstance(req, Request)
        assert req.method == method
        assert result == data
