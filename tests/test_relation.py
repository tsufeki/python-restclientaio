
import pytest

from restclientaio.hydrator import HydrationTypeError
from restclientaio.manager import ResourceManager
from restclientaio.relation import *


class Resource:
    pass


class Target:
    pass


@pytest.mark.parametrize('cls', [OneToMany, ManyToOne])
class TestRelation:

    @pytest.mark.parametrize('target', [Target, 'Target'])
    def test_returns_target_class(self, cls, target):
        r = cls(target)
        assert r.target_class(type(self)) is Target

    def test_throws_on_non_existing_target(self, cls):
        r = cls('NonExisting')
        with pytest.raises(NameError):
            r.target_class(type(self))

    def test_formats_meta(self, cls, mocker):
        r = cls(
            Target,
            foo='a{0.foo}',
            bar={
                'baz': '{0.baz}',
                'y': 9,
            },
            x=7,
        )
        obj = mocker.Mock(spec='foo,bar')
        obj.foo = 'FOO'
        obj.baz = 'BAZBAZ'
        assert r.meta(obj) == {
            'foo': 'aFOO',
            'bar': {
                'baz': 'BAZBAZ',
                'y': 9,
            },
            'x': 7,
        }

    def test_calls_parent_constructor(self, cls):
        r = cls(Target, field='foo', readonly=True, name='bar')
        assert r.field == 'foo'
        assert r.readonly
        assert r.name == 'bar'


class TestOneToManySerializer:

    def test_supported_descriptors(self):
        serializer = OneToManySerializer(None)
        assert serializer.supported_descriptors == {OneToMany}

    @pytest.mark.asyncio
    async def test_load_collection(self, mocker):
        rm = mocker.Mock(spec=ResourceManager)
        rm._get_or_instantiate.return_value = target = Target()

        serializer = OneToManySerializer(rm)
        descr = mocker.Mock()
        descr.target_class.return_value = Target

        res = Resource()
        serializer.load(descr, [1, 2], res)
        assert rm._get_or_instantiate.call_args_list == [
            ((Target, 1),),
            ((Target, 2),),
        ]
        assert descr.target_class.call_args_list == [((Resource,),)]
        assert await descr.set.call_args[0][1].to_list() == [
            target, target,
        ]

    @pytest.mark.asyncio
    async def test_load_none(self, mocker):
        rm = mocker.Mock(spec=ResourceManager)
        targets = [Target(), Target()]

        async def rm_list():
            for t in targets:
                yield t
        rm.list.return_value = rm_list()

        serializer = OneToManySerializer(rm)
        descr = mocker.Mock()
        descr.target_class.return_value = Target
        descr.meta.return_value = meta = {'foo': 42}
        res = Resource()

        serializer.load(descr, None, res)
        result = []
        async for t in descr.set.call_args[0][1]:
            result.append(t)

        assert result == targets
        assert rm.list.call_args_list == [((Target, meta),)]
        assert descr.target_class.call_args_list == [((Resource,),)]
        assert descr.meta.call_args_list == [((res,),)]

    def test_throws_on_bad_type(self):
        serializer = OneToManySerializer(None)
        with pytest.raises(HydrationTypeError):
            serializer.load(object(), 7, object())


class TestManyToOneSerializer:

    def test_supported_descriptors(self):
        serializer = ManyToOneSerializer(None)
        assert serializer.supported_descriptors == {ManyToOne}

    def test_load_dict(self, mocker):
        rm = mocker.Mock(spec=ResourceManager)
        rm._get_or_instantiate.return_value = target = Target()

        serializer = ManyToOneSerializer(rm)
        descr = mocker.Mock()
        descr.target_class.return_value = Target
        descr.meta.return_value = {'bar': 42}
        data = {'foo': 1}
        res = Resource()

        serializer.load(descr, data, res)
        assert descr.set_instant.call_args_list == [((res, target),)]
        assert rm._get_or_instantiate.call_args_list == [((Target, data),)]
        assert descr.target_class.call_args_list == [((Resource,),)]
        assert descr.meta.call_args_list == [((res,),)]

    @pytest.mark.asyncio
    async def test_load_id(self, mocker):
        rm = mocker.Mock(spec=ResourceManager)
        target = Target()

        async def rm_get():
            return target
        rm.get.return_value = rm_get()

        serializer = ManyToOneSerializer(rm)
        descr = mocker.Mock()
        descr.target_class.return_value = Target
        descr.meta.return_value = meta = {'bar': 42}
        data = 7
        res = Resource()

        serializer.load(descr, data, res)
        assert await descr.set_awaitable.call_args[0][1]() is target
        assert rm.get.call_args_list == [((Target, data, meta),)]
        assert descr.target_class.call_args_list == [((Resource,),)]
        assert descr.meta.call_args_list == [((res,),)]

    def test_load_none(self, mocker):
        serializer = ManyToOneSerializer(None)
        descr = mocker.Mock()
        res = Resource()
        serializer.load(descr, None, res)
        assert descr.set_instant.call_args_list == [((res, None),)]

    def test_throws_on_bad_type(self):
        serializer = ManyToOneSerializer(None)
        with pytest.raises(HydrationTypeError):
            serializer.load(object(), [], object())
