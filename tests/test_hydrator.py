
from datetime import date, datetime

import pytest

from restclientaio.hydrator import *

from restclientaio.hydrator import annotation_descriptor  # isort:skip


class TestHydrationTypeError:

    def test_str(self):
        e = HydrationTypeError((int, bool), 'foo')
        assert str(e) == "Wrong type: expected int or bool, got 'foo'"
        e.cls = object
        e.attr = 'bar'
        assert str(e) == 'Wrong type for builtins.object.bar: ' \
            "expected int or bool, got 'foo'"


class TestDescriptor:

    @pytest.mark.parametrize('descr_cls', [Descriptor, AwaitableDescriptor])
    @pytest.mark.parametrize('readonly', [True, False])
    def test_returns_self_on_class(self, descr_cls, readonly):
        class C:
            field = descr_cls(readonly=readonly)
        assert isinstance(C.field, descr_cls)

    def test_sets_value(self):
        class C:
            field = Descriptor()
        c = C()
        c.field = 42
        assert c.field == 42

    @pytest.mark.asyncio
    async def test_sets_value_await(self):
        class C:
            field = AwaitableDescriptor()
        c = C()
        c.field = 42
        assert await c.field == 42

    @pytest.mark.parametrize('descr_cls', [Descriptor, AwaitableDescriptor])
    def test_throws_on_readonly_set(self, descr_cls):
        class C:
            field = descr_cls(readonly=True)
        c = C()
        with pytest.raises(Exception):
            c.field = 42

    @pytest.mark.parametrize('readonly', [True, False])
    def test_side_sets_value(self, readonly):
        class C:
            field = Descriptor(readonly=readonly)
        c = C()
        C.field.set(c, 42)
        assert c.field == 42

    @pytest.mark.parametrize('readonly', [True, False])
    @pytest.mark.asyncio
    async def test_side_sets_value_instant(self, readonly):
        class C:
            field = AwaitableDescriptor(readonly=readonly)
        c = C()
        C.field.set_instant(c, 42)
        assert await c.field == 42

    @pytest.mark.parametrize('readonly', [True, False])
    @pytest.mark.asyncio
    async def test_side_sets_value_await(self, readonly):
        class C:
            field = AwaitableDescriptor(readonly=readonly)
        c = C()

        async def value():
            return 42
        C.field.set_awaitable(c, value)
        assert await c.field == 42

    @pytest.mark.parametrize('readonly', [True, False])
    def test_returns_none_when_not_set(self, readonly):
        class C:
            field = Descriptor(readonly=readonly)
        c = C()
        assert c.field is None

    @pytest.mark.parametrize('readonly', [True, False])
    @pytest.mark.asyncio
    async def test_returns_none_when_not_set_await(self, readonly):
        class C:
            field = AwaitableDescriptor(readonly=readonly)
        c = C()
        assert await c.field is None


class Resource:
    pass


class TestScalarSerializer:

    @pytest.mark.parametrize('annot,serialized,value', [
        (str, 'foo', 'foo'),
        (int, 42, 42),
        (float, 42, 42),
        (float, 42.5, 42.5),
        (bool, False, False),
        (None, 'bar', 'bar'),
        (type(None), 7, 7),
        (str, None, None),
        (int, None, None),
        (None, None, None),
    ])
    def test_load(self, annot, serialized, value):
        s = ScalarSerializer()
        obj = Resource()
        descr = annotation_descriptor(annot)(name='foo')
        s.load(descr, serialized, obj)
        assert obj.foo == value
        assert s.dump(descr, obj) == serialized

    @pytest.mark.parametrize('annot,value', [
        (str, 7),
        (int, 42.5),
        (float, 'foo'),
        (float, False),
        (str, True),
        (bool, 0),
        (None, []),
    ])
    def test_load_throws(self, annot, value):
        s = ScalarSerializer()
        obj = Resource()
        descr = annotation_descriptor(annot)(name='foo')
        with pytest.raises(HydrationTypeError):
            s.load(descr, value, obj)
        obj.foo = value
        with pytest.raises(HydrationTypeError):
            s.dump(descr, obj)


class TestDateTimeSerializer:

    @pytest.mark.parametrize('annot,serialized,value', [
        (date, None, None),
        (datetime, None, None),
        (date, '2017-08-09', date(2017, 8, 9)),
        (datetime, '2017-08-09T11:09:23Z', datetime(2017, 8, 9, 11, 9, 23)),
    ])
    def test_load(self, annot, serialized, value):
        s = DateTimeSerializer()
        obj = Resource()
        descr = annotation_descriptor(annot)(name='foo')
        s.load(descr, serialized, obj)
        assert obj.foo == value
        assert s.dump(descr, obj) == serialized

    @pytest.mark.parametrize('annot,value', [
        (date, 7),
        (datetime, False),
        (date, 'foo'),
        (datetime, 'foo'),
        (date, []),
    ])
    def test_load_throws(self, annot, value):
        s = DateTimeSerializer()
        obj = Resource()
        descr = annotation_descriptor(annot)(name='foo')
        with pytest.raises(HydrationTypeError):
            s.load(descr, value, obj)
        obj.foo = value
        with pytest.raises(HydrationTypeError):
            s.dump(descr, obj)


class TestHydrator:

    @pytest.fixture
    def annot_serializer(self, mocker):
        annot_serializer = ScalarSerializer()
        annot_serializer.supported_descriptors = {annotation_descriptor(int)}
        mocker.spy(annot_serializer, 'load')
        mocker.spy(annot_serializer, 'dump')
        return annot_serializer

    @pytest.fixture
    def descr_serializer(self, mocker):
        class DescriptorSerializer(Serializer):

            supported_descriptors = {Descriptor}

            def load(self, descr, value, resource):
                descr.set(resource, value)

            def dump(self, descr, resource):
                return descr.__get__(resource, None)

        descr_serializer = DescriptorSerializer()
        mocker.spy(descr_serializer, 'load')
        mocker.spy(descr_serializer, 'dump')
        return descr_serializer

    @pytest.fixture
    def hydrator(self, annot_serializer, descr_serializer):
        hydrator = Hydrator()
        hydrator.add_serializer(annot_serializer)
        hydrator.add_serializer(descr_serializer)
        return hydrator

    def test_hydrate(self, hydrator, annot_serializer, descr_serializer):
        class C:
            foo: int
            bar = Descriptor()
        obj = C()
        data = {'bar': 'baz', 'foo': 42}
        hydrator.hydrate(obj, data)
        assert annot_serializer.load.call_args[0][1:] == (42, obj)
        assert descr_serializer.load.call_args == ((C.bar, 'baz', obj),)
        assert obj.__dict__ == data
        assert hydrator.dehydrate(obj) == data
        assert annot_serializer.dump.call_args[0][1:] == (obj,)
        assert descr_serializer.dump.call_args == ((C.bar, obj),)

    def test_ignores_missing_field(
        self,
        hydrator,
        annot_serializer,
        descr_serializer,
    ):
        class C:
            foo: int
            bar = Descriptor()
        obj = C()
        data = {'bar': 'baz'}
        hydrator.hydrate(obj, data)
        assert annot_serializer.load.call_args is None
        assert descr_serializer.load.call_args == ((C.bar, 'baz', obj),)
        assert obj.__dict__ == data
        assert hydrator.dehydrate(obj) == {'bar': 'baz', 'foo': None}

    def test_ignores_unknown_fields(
        self,
        hydrator,
        annot_serializer,
        descr_serializer,
    ):
        class C:
            foo: list
            bar = object()
            _baz: int
        obj = C()
        data = {'foo': [], 'bar': 42, '_baz': 53}
        hydrator.hydrate(obj, data)
        assert annot_serializer.load.call_args is None
        assert descr_serializer.load.call_args is None
        assert obj.__dict__ == {}
        obj._baz = 7
        obj.baz = 9
        assert hydrator.dehydrate(obj) == {}

    def test_throws_on_bad_type(self, hydrator, annot_serializer):
        class C:
            foo: int
        obj = C()
        data = {'foo': 'bar'}
        with pytest.raises(HydrationTypeError):
            hydrator.hydrate(obj, data)
        obj.foo = 'bar'
        with pytest.raises(HydrationTypeError):
            assert hydrator.dehydrate(obj)

    def test_renamed_field(self, hydrator, descr_serializer):
        class C:
            foo = Descriptor(field='bar')
        obj = C()
        data = {'bar': 'baz'}
        hydrator.hydrate(obj, data)
        assert descr_serializer.load.call_args == ((C.foo, 'baz', obj),)
        assert obj.__dict__ == {'foo': 'baz'}
        assert hydrator.dehydrate(obj) == data

    def test_renamed_field_for_saving(self, hydrator, descr_serializer):
        class C:
            foo = Descriptor(save_field='bar')
        obj = C()
        data = {'foo': 'baz'}
        hydrator.hydrate(obj, data)
        assert descr_serializer.load.call_args == ((C.foo, 'baz', obj),)
        assert obj.__dict__ == data
        assert hydrator.dehydrate(obj) == {'bar': 'baz'}

    def test_ignores_readonly_field(
        self,
        hydrator,
        descr_serializer,
    ):
        class C:
            foo = Descriptor(readonly=True)
        obj = C()
        C.foo.set(obj, 42)
        assert hydrator.dehydrate(obj) == {}
        assert descr_serializer.dump.call_args is None
