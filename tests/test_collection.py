
import pytest

from restclientaio.collection import Collection


@pytest.mark.asyncio
class TestCollection:

    async def arange(self, n=3):
        for i in range(1, n + 1):
            yield i

    async def test_create_from_list(self):
        coll = Collection([1, 2, 3])
        assert await coll.to_list() == [1, 2, 3]

    async def test_create_from_async_iter(self):
        coll = Collection(self.arange())
        assert await coll.to_list() == [1, 2, 3]
        assert await coll.to_list() == [1, 2, 3]

    async def test_aiter(self):
        coll = Collection(self.arange())
        res = []
        async for i in coll:
            res.append(i)
        assert res == [1, 2, 3]

    async def test_aiter_second_time(self):
        coll = Collection(self.arange())
        assert await coll.to_list() == [1, 2, 3]

        res = []
        async for i in coll:
            res.append(i)
        assert res == [1, 2, 3]

    async def test_aiter_from_list(self):
        coll = Collection([1, 2, 3])
        res = []
        async for i in coll:
            res.append(i)
        assert res == [1, 2, 3]

    async def test_get_item(self):
        coll = Collection(self.arange(5))
        assert await coll[2] == 3

    async def test_get_item_from_list(self):
        coll = Collection([1, 2, 3, 4, 5])
        assert await coll[2] == 3

    async def test_get_slice(self):
        coll = Collection(self.arange(5))
        assert await coll[2:4] == [3, 4]

    async def test_get_slice_from_list(self):
        coll = Collection((1, 2, 3, 4, 5))
        assert await coll[2:4] == [3, 4]

    async def test_loaded(self):
        coll = Collection(self.arange(5))
        assert not coll.loaded
        await coll.to_list()
        assert coll.loaded
        coll = Collection((1, 2, 3, 4, 5))
        assert coll.loaded
