from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Text
from typing import TypeVar
from typing import Union

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import Dictionary

K = TypeVar("K")
V = TypeVar("V")
KWARGS = Any
JsonValueT = Union[None, int, Text, bool, List[JsonValueT], Dict[Text, JsonValueT]]

class SyncMainDataDictionary(Dictionary[K, V]): ...
class SyncTorrentPeersDictionary(Dictionary[K, V]): ...

class Sync(ClientCache):
    maindata: _MainData
    torrent_peers: _TorrentPeers
    torrentPeers: _TorrentPeers
    def __init__(self, client: SyncAPIMixIn) -> None: ...

    class _MainData(ClientCache):
        _rid: int | None
        def __init__(self, client: SyncAPIMixIn) -> None: ...
        def __call__(
            self, rid: Optional[Text | int] = None, **kwargs: KWARGS
        ) -> SyncMainDataDictionary[Text, JsonValueT]: ...
        def delta(
            self, **kwargs: KWARGS
        ) -> SyncMainDataDictionary[Text, JsonValueT]: ...
        def reset_rid(self) -> None: ...

    class _TorrentPeers(ClientCache):
        _rid: int | None
        def __init__(self, client: SyncAPIMixIn) -> None: ...
        def __call__(
            self,
            torrent_hash: Optional[Text] = None,
            rid: Optional[Text | int] = None,
            **kwargs: KWARGS
        ) -> SyncTorrentPeersDictionary[Text, JsonValueT]: ...
        def delta(
            self, torrent_hash: Optional[Text] = None, **kwargs: KWARGS
        ) -> SyncTorrentPeersDictionary[Text, JsonValueT]: ...
        def reset_rid(self) -> None: ...

class SyncAPIMixIn(AppAPIMixIn):
    @property
    def sync(self) -> Sync: ...
    def sync_maindata(
        self, rid: Text | int = 0, **kwargs: KWARGS
    ) -> SyncMainDataDictionary[Text, JsonValueT]: ...
    def sync_torrent_peers(
        self, torrent_hash: Optional[Text] = None, rid: Text | int = 0, **kwargs: KWARGS
    ) -> SyncTorrentPeersDictionary[Text, JsonValueT]: ...
    sync_torrentPeers = sync_torrent_peers
