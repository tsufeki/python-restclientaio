
from datetime import date

from restclientaio.manager_factory import create_manager
from restclientaio.repository import Repository
from restclientaio.request import Requester


class Project:
    id: int
    name: str
    created_on: date

    class _Meta:
        get = dict(uri='/project/{id}.json')
        list = dict(uri='/projects.json')  # noqa: B003


class APIRequester(Requester):
    pass


class API:

    def __init__(self, base_url, session):
        self.session = session
        requester = APIRequester(base_url, session)
        self.manager = create_manager(requester)
        self.projects = Repository(self.manager, Project)
