
import pytest

from restclientaio.manager import Hydrator, Requester, Resource, \
    ResourceError, ResourceManager


async def coro(return_value=None):
    return return_value


class TestManager:

    @pytest.fixture
    def requester(self, mocker):
        return mocker.Mock(spec=Requester)

    @pytest.fixture
    def hydrator(self, mocker):
        return mocker.Mock(spec=Hydrator)

    @pytest.mark.asyncio
    async def test_get(self, mocker, requester, hydrator):
        rm = ResourceManager(requester, hydrator)
        data = {'id': 42, 'bar': 33}

        class ResourceA(Resource):
            create_count = 0

            def __init__(self):
                type(self).create_count += 1

            class _Meta:
                get = dict(uri='/foo')

        for i in (0, 1):
            requester.get.return_value = coro(data)
            obj = await rm.get(ResourceA, 42, {'foo': 'bar'})
            assert isinstance(obj, ResourceA)
            assert requester.get.call_args == (({
                'foo': 'bar',
                'id': 42,
                'uri': '/foo',
            },),)
            assert hydrator.hydrate.call_args == ((obj, data),)

        assert ResourceA.create_count == 1

    @pytest.mark.asyncio
    async def test_get_throws_on_bad_type(self, mocker, requester, hydrator):
        rm = ResourceManager(requester, hydrator)
        data = True

        requester.get.return_value = coro(data)
        with pytest.raises(ResourceError):
            await rm.get(Resource, 42, {'uri': '/foo'})

    @pytest.mark.asyncio
    async def test_list(self, mocker, requester, hydrator):
        rm = ResourceManager(requester, hydrator)
        data = [{'id': 42, 'bar': 33}, {'baz': 45}]

        class ResourceA(Resource):
            class _Meta:
                list = dict(uri='/foo')  # noqa: B003

        requester.list.return_value = coro(data)
        i = 0
        async for obj in rm.list(ResourceA, {'foo': 'bar'}):
            assert isinstance(obj, ResourceA)
            assert hydrator.hydrate.call_args == ((obj, data[i]),)
            i += 1

        assert requester.list.call_args == (({
            'foo': 'bar',
            'uri': '/foo',
        },),)

    @pytest.mark.asyncio
    async def test_list_throws_on_bad_type(self, mocker, requester, hydrator):
        rm = ResourceManager(requester, hydrator)
        data = True

        requester.list.return_value = coro(data)
        with pytest.raises(ResourceError):
            async for obj in rm.list(Resource, {'uri': '/foo'}):  # noqa: F841
                pass

    def test_new(self, mocker, hydrator):
        rm = ResourceManager(None, hydrator)
        data = {'id': 42, 'bar': 33}

        class ResourceA(Resource):
            pass

        obj = rm.new(ResourceA, data)
        assert isinstance(obj, ResourceA)
        assert hydrator.hydrate.call_args == (
            (obj, data),
            {'force_clear': True},
        )

    def test_new_throws_on_bad_type(self, mocker, requester, hydrator):
        rm = ResourceManager(requester, hydrator)
        data = True

        with pytest.raises(ResourceError):
            rm.new(Resource, data)
