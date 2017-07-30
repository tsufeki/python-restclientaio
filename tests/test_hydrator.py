
from datetime import date, datetime

import pytest

from restclientaio.hydrator import DateTimeSerializer, HydrationTypeError, \
    Hydrator, ScalarSerializer, Serializer


class TestHydrationTypeError:

    def test_str(self):
        e = HydrationTypeError((int, bool), 'foo')
        assert str(e) == "Wrong type: expected int or bool, got 'foo'"
        e.cls = object
        e.attr = 'bar'
        assert str(e) == 'Wrong type for builtins.object.bar: ' \
            "expected int or bool, got 'foo'"


class TestScalarSerializer:

    @pytest.mark.parametrize('annot,value,expected', [
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
    def test_load(self, annot, value, expected):
        s = ScalarSerializer()
        assert s.load(annot, value, object()) == expected

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
        with pytest.raises(HydrationTypeError):
            s.load(annot, value, object())


class TestDateTimeSerializer:

    @pytest.mark.parametrize('annot,value,expected', [
        (date, None, None),
        (datetime, None, None),
        (date, '2017-08-09', date(2017, 8, 9)),
        (datetime, '2017-08-09T11:09:23Z', datetime(2017, 8, 9, 11, 9, 23)),
    ])
    def test_load(self, annot, value, expected):
        s = DateTimeSerializer()
        assert s.load(annot, value, object()) == expected

    @pytest.mark.parametrize('annot,value', [
        (date, 7),
        (datetime, False),
        (date, 'foo'),
        (datetime, 'foo'),
        (date, []),
    ])
    def test_load_throws(self, annot, value):
        s = DateTimeSerializer()
        with pytest.raises(HydrationTypeError):
            s.load(annot, value, object())


class AnnotSerializer(Serializer):
    supported_annotations = {int}

    def load(self, typ, value, resource):
        assert typ is int
        assert isinstance(resource, ResourceMockBase)
        if not isinstance(value, int):
            raise HydrationTypeError(int, value)
        return value


class Descriptor:
    def __set__(self, instance, value):
        instance.descriptor_value = value


class DescrSerializer(Serializer):
    supported_descriptors = {Descriptor}

    def load(self, descr, value, resource):
        assert type(descr) is Descriptor
        assert isinstance(resource, ResourceMockBase)
        return value


class ResourceMockBase:
    pass


class ResourceMock(ResourceMockBase):
    foo: int
    bar = Descriptor()


class TestHydrator:

    def hydrate(self, res, data):
        hydrator = Hydrator([DescrSerializer(), AnnotSerializer()])
        hydrator.hydrate(res, data)

    def test_hydrate(self):
        res = ResourceMock()
        data = {'bar': 'baz', 'foo': 42}
        self.hydrate(res, data)
        assert len(res.__dict__) == 2
        assert res.foo == 42
        assert res.descriptor_value == 'baz'

    def test_ignores_missing_field(self):
        res = ResourceMock()
        data = {'bar': 'baz'}
        self.hydrate(res, data)
        assert len(res.__dict__) == 1
        assert res.descriptor_value == 'baz'

    def test_ignores_unknown_fields(self):
        class Mock(ResourceMockBase):
            foo: str
            bar: int
            baz = object()
            _ignored: int
        data = {
            'foo': 'baz',
            'bar': 1,
            'baz': 2,
            '_ignored': 3,
        }
        res = Mock()
        self.hydrate(res, data)
        assert len(res.__dict__) == 1
        assert res.bar == 1

    def test_throws_on_bad_type(self):
        res = ResourceMock()
        data = {'foo': 'bar'}
        with pytest.raises(HydrationTypeError):
            self.hydrate(res, data)
