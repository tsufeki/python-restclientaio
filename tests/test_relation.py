
import pytest

from restclientaio.collection import Collection
from restclientaio.hydrator import HydrationTypeError
from restclientaio.manager import ResourceManager
from restclientaio.relation import *


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

    def test_field_name(self, cls):
        r = cls(Target, field='foo')
        assert r.field == 'foo'

    def test_no_field_name(self, cls):
        r = cls(Target)
        assert r.field is None


class TestOneToMany:

    @pytest.mark.asyncio
    async def test_get(self):
        class Owner:
            otm = OneToMany(Target)
        assert isinstance(Owner.otm, OneToMany)
        obj = Owner()
        obj.otm = [1, 2, 3]
        assert isinstance(obj.otm, Collection)
        assert await obj.otm.to_list() == [1, 2, 3]


class TestManyToOne:

    async def async_get():
        return 42

    @pytest.mark.parametrize('value', [42, async_get])
    @pytest.mark.asyncio
    async def test_get(self, value):
        class Owner:
            otm = ManyToOne(Target)
        assert isinstance(Owner.otm, ManyToOne)
        obj = Owner()
        obj.otm = value
        assert await obj.otm == 42
        assert await obj.otm == 42


class TestOneToManySerializer:

    def test_supported_descriptors(self):
        serializer = OneToManySerializer(None)
        assert serializer.supported_descriptors == {OneToMany}
        assert serializer.supported_annotations == set()

    def test_load_list(self, mocker):
        rm = mocker.Mock(spec=ResourceManager)
        rm._get_or_instantiate.return_value = target = Target()

        serializer = OneToManySerializer(rm)
        descr = mocker.Mock()
        descr.target_class.return_value = Target

        assert serializer.load(descr, [1, 2], object()) == [
            target, target,
        ]
        assert rm._get_or_instantiate.call_args_list == [
            ((Target, 1),),
            ((Target, 2),),
        ]
        assert descr.target_class.call_args_list == [((object,),)]

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
        obj = object()

        agen = serializer.load(descr, None, obj)
        result = []
        async for t in agen:
            result.append(t)

        assert result == targets
        assert rm.list.call_args_list == [((Target, meta),)]
        assert descr.target_class.call_args_list == [((object,),)]
        assert descr.meta.call_args_list == [((obj,),)]

    def test_throws_on_bad_type(self):
        serializer = OneToManySerializer(None)
        with pytest.raises(HydrationTypeError):
            serializer.load(object(), 7, object())


class TestManyToOneSerializer:

    def test_supported_descriptors(self):
        serializer = ManyToOneSerializer(None)
        assert serializer.supported_descriptors == {ManyToOne}
        assert serializer.supported_annotations == set()

    def test_load_dict(self, mocker):
        rm = mocker.Mock(spec=ResourceManager)
        rm._get_or_instantiate.return_value = target = Target()

        serializer = ManyToOneSerializer(rm)
        descr = mocker.Mock()
        descr.target_class.return_value = Target
        descr.meta.return_value = {'bar': 42}
        data = {'foo': 1}
        obj = object()

        assert serializer.load(descr, data, obj) == target
        assert rm._get_or_instantiate.call_args_list == [((Target, data),)]
        assert descr.target_class.call_args_list == [((object,),)]
        assert descr.meta.call_args_list == [((obj,),)]

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
        obj = object()

        assert await serializer.load(descr, data, obj)() == target
        assert rm.get.call_args_list == [((Target, data, meta),)]
        assert descr.target_class.call_args_list == [((object,),)]
        assert descr.meta.call_args_list == [((obj,),)]

    def test_load_none(self):
        serializer = ManyToOneSerializer(None)
        assert serializer.load(object(), None, object()) is None

    def test_throws_on_bad_type(self):
        serializer = ManyToOneSerializer(None)
        with pytest.raises(HydrationTypeError):
            serializer.load(object(), [], object())
