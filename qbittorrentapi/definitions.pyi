from enum import Enum
from typing import Iterable
from typing import MutableMapping
from typing import Text
from typing import Type

try:
    from collections import UserList
except ImportError:
    from UserList import UserList

from qbittorrentapi._attrdict import AttrDict
from qbittorrentapi.client import Client
from qbittorrentapi.request import Request

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
    def __init__(self, *args, client: Request, **kwargs) -> None: ...

class Dictionary(ClientCache, AttrDict):
    def __init__(self, data: MutableMapping = None, client: Request = None): ...
    @staticmethod
    def _normalize(data: MutableMapping) -> AttrDict: ...

class List(ClientCache, UserList):
    def __init__(
        self,
        list_entries: Iterable = None,
        entry_class: Type[ListEntry] = None,
        client: Request = None,
    ) -> None: ...

class ListEntry(Dictionary): ...
