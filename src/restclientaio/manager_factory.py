
from typing import Sequence

from .hydrator import DateTimeSerializer, Hydrator, ScalarSerializer, \
    Serializer
from .manager import ResourceManager
from .relation import ManyToOneSerializer, OneToManySerializer
from .request import Requester

__all__ = ('create_manager',)


def create_manager(
    requester: Requester,
    hydrator_serializers: Sequence[Serializer] = (),
) -> ResourceManager:
    manager = None
    serializers = [
        ScalarSerializer(),
        DateTimeSerializer(),
        OneToManySerializer(lambda: manager),
        ManyToOneSerializer(lambda: manager),
    ]
    serializers.extend(hydrator_serializers)
    hydrator = Hydrator(serializers)
    manager = ResourceManager(requester, hydrator)
    hydrator = None
    serializers = None
    return manager
