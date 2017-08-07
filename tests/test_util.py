
import pytest

from restclientaio._util import *


class TestFullName:

    @pytest.mark.parametrize('args,expected', [
        ((str,), 'builtins.str'),
        ((str, 'lower'), 'builtins.str.lower'),
    ])
    def test_full_name(self, args, expected):
        assert full_name(*args) == expected


class TestFormatRecur:

    @pytest.mark.parametrize('args,kwargs,expected', [
        (('{}', 42), {}, '42'),
        (({'{0}': '{foo}foo'}, 'bar'), {'foo': 'FOO'}, {'bar': 'FOOfoo'}),
        ((['{0.real:02d}'], 1), {}, ['01']),
    ])
    def test_format_recur(self, args, kwargs, expected):
        assert format_recur(*args, **kwargs) == expected

    def test_throws_on_self_referencing(self):
        d = {}
        d['foo'] = d
        with pytest.raises(ValueError):
            format_recur(d)
