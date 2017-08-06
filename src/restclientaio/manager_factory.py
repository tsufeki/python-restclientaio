"""`.ResourceManager` factory."""

from typing import List, Sequence  # noqa: F401

from .hydrator import DateTimeSerializer, Hydrator, ScalarSerializer, \
    Serializer
from .manager import ResourceManager
from .relation import ManyToOneSerializer, OneToManySerializer
from .request import Requester

__all__ = ('create_manager',)


def create_manager(
    requester: Requester,
    custom_serializers: Sequence[Serializer] = (),
) -> ResourceManager:
    """Create new `.ResourceManager`.

    :param requester:
    :param custom_serializers: Additional serializer to register with
        the `.Hydrator`.
    """
    hydrator = Hydrator()
    manager = ResourceManager(requester, hydrator)
    serializers: List[Serializer] = [
        ScalarSerializer(),
        DateTimeSerializer(),
        OneToManySerializer(manager),
        ManyToOneSerializer(manager),
    ]
    serializers.extend(custom_serializers)
    for serializer in serializers:
        hydrator.add_serializer(serializer)
    return manager
