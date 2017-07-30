
from restclientaio import Resource


class TestResource:

    def test_repr_normal_id(self):
        r = NormalIDResource()
        assert repr(r) == '<test_resource.NormalIDResource id=1>'

    def test_repr_no_id(self):
        r = NoIDResource()
        assert repr(r) == '<test_resource.NoIDResource id=None>'

    def test_repr_custom_id(self):
        r = CustomIDResource()
        assert repr(r) == "<test_resource.CustomIDResource cid='c2'>"


class NormalIDResource(Resource):
    id = 1  # noqa: B003


class NoIDResource(Resource):
    pass


class CustomIDResource(Resource):
    class _Meta:
        id = 'cid'  # noqa: B003
    cid = 'c2'
    id = 3  # noqa: B003
