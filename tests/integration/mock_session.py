
class MockResponse:

    _reasons = {
        200: 'OK',
        404: 'Not Found',
    }

    def __init__(self, json=None, status=200, headers=None):
        self.status = status
        self.reason = self._reasons[status]
        self.headers = headers or {}
        self._json = json

    async def __aenter__(self):
        return self

    async def __aexit__(self, *tb):
        pass

    async def json(self, encoding=None):
        return self._json


class MockSession:

    def __init__(self):
        self.request_map = {}

    def add(
        self,
        method,
        url,
        params,
        response_status,
        response_json,
        response_headers=None,
    ):
        self.request_map[
            method,
            url,
            tuple(sorted(params.items())),
        ] = MockResponse(
            response_json,
            response_status,
            response_headers,
        )

    def request(
        self,
        method,
        url,
        *, params=None,
        json=None,
        headers=None,
        data=None,
    ):
        return self.request_map[
            method,
            url,
            tuple(sorted((params or {}).items())),
        ]
