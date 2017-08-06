
from datetime import date

import pytest

from .api import API
from .mock_session import MockSession


class TestIntegration:

    @pytest.fixture
    def session(self):
        return MockSession()

    @pytest.fixture
    def api(self, session):
        return API('https://example.com', session)

    @pytest.mark.asyncio
    async def test_get(self, api):
        api.session.add('GET', 'https://example.com/project/1.json', {}, 200, {
            'id': 1,
            'name': 'First project',
            'created_on': '2017-07-01',
        })

        project = await api.projects.get(1)
        assert project.id == 1
        assert project.name == 'First project'
        assert project.created_on == date(2017, 7, 1)

    @pytest.mark.asyncio
    async def test_list(self, api):
        api.session.add('GET', 'https://example.com/projects.json', {}, 200, [
            {
                'id': 1,
                'name': 'First project',
                'created_on': '2017-07-01',
            },
            {
                'id': 2,
                'name': 'Second project',
                'created_on': '2017-07-02',
            },
        ])

        projects = await api.projects.all().to_list()
        assert projects[0].id == 1
        assert projects[0].name == 'First project'
        assert projects[0].created_on == date(2017, 7, 1)
        assert projects[1].id == 2
        assert projects[1].name == 'Second project'
        assert projects[1].created_on == date(2017, 7, 2)
