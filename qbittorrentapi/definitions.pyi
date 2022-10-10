from enum import Enum
from typing import Any
from typing import Iterable
from typing import List as ListT
from typing import Mapping
from typing import Optional
from typing import Text
from typing import Type
from typing import TypeVar

try:
    from collections import UserList
except ImportError:
    from UserList import UserList  # type: ignore

from qbittorrentapi._attrdict import AttrDict
from qbittorrentapi.client import Client
from qbittorrentapi.request import Request

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
KWARGS = Any

class APINames(Enum):
    Authorization: Text
    Application: Text
    Log: Text
    Sync: Text
    Transfer: Text
    Torrents: Text
    RSS: Text
    Search: Text
    EMPTY: Text

class TorrentStates(Enum):
    ERROR: Text
    MISSING_FILES: Text
    UPLOADING: Text
    PAUSED_UPLOAD: Text
    QUEUED_UPLOAD: Text
    STALLED_UPLOAD: Text
    CHECKING_UPLOAD: Text
    FORCED_UPLOAD: Text
    ALLOCATING: Text
    DOWNLOADING: Text
    METADATA_DOWNLOAD: Text
    FORCED_METADATA_DOWNLOAD: Text
    PAUSED_DOWNLOAD: Text
    QUEUED_DOWNLOAD: Text
    FORCED_DOWNLOAD: Text
    STALLED_DOWNLOAD: Text
    CHECKING_DOWNLOAD: Text
    CHECKING_RESUME_DATA: Text
    MOVING: Text
    UNKNOWN: Text
    @property
    def is_downloading(self) -> bool: ...
    @property
    def is_uploading(self) -> bool: ...
    @property
    def is_complete(self) -> bool: ...
    @property
    def is_checking(self) -> bool: ...
    @property
    def is_errored(self) -> bool: ...
    @property
    def is_paused(self) -> bool: ...

class ClientCache:
    _client: Client
    def __init__(
        self, *args: ListT[Any], client: Request, **kwargs: KWARGS
    ) -> None: ...

class Dictionary(ClientCache, AttrDict[K, V]):
    def __init__(
        self,
        data: Optional[Mapping[K, V]] = None,
        client: Optional[Request] = None,
    ): ...
    @staticmethod
    def _normalize(data: Mapping[K, V]) -> AttrDict[K, V]: ...

class List(ClientCache, UserList[T]):
    def __init__(
        self,
        list_entries: Optional[Iterable[ListEntry[Any, Any]]] = None,
        entry_class: Optional[Type[ListEntry[Any, Any]]] = None,
        client: Optional[Request] = None,
    ) -> None: ...

class ListEntry(Dictionary[K, V]): ...
