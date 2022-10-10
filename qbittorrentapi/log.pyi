from typing import Any
from typing import Dict
from typing import Iterable
from typing import List as ListT
from typing import Optional
from typing import Text
from typing import TypeVar
from typing import Union

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import List
from qbittorrentapi.definitions import ListEntry

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
KWARGS = Any
JsonValueT = Union[None, int, Text, bool, ListT[JsonValueT], Dict[Text, JsonValueT]]

class LogPeersList(List[T]):
    def __init__(
        self,
        list_entries: Optional[Iterable[ListEntry[Text, JsonValueT]]] = None,
        client: Optional[LogAPIMixIn] = None,
    ) -> None: ...

class LogPeer(ListEntry[K, V]): ...

class LogMainList(List[T]):
    def __init__(
        self,
        list_entries: Optional[Iterable[ListEntry[Text, JsonValueT]]] = None,
        client: Optional[LogAPIMixIn] = None,
    ) -> None: ...

class LogEntry(ListEntry[K, V]): ...

class Log(ClientCache):
    main: _Main
    def __init__(self, client: LogAPIMixIn) -> None: ...
    def peers(
        self, last_known_id: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> LogPeersList[LogPeer[Text, JsonValueT]]: ...

    class _Main(ClientCache):
        def _api_call(
            self,
            normal: Optional[bool] = None,
            info: Optional[bool] = None,
            warning: Optional[bool] = None,
            critical: Optional[bool] = None,
            last_known_id: Optional[bool] = None,
            **kwargs: KWARGS
        ) -> LogMainList[LogEntry[Text, JsonValueT]]: ...
        def __call__(
            self,
            normal: Optional[bool] = None,
            info: Optional[bool] = None,
            warning: Optional[bool] = None,
            critical: Optional[bool] = None,
            last_known_id: Optional[bool] = None,
            **kwargs: KWARGS
        ) -> LogMainList[LogEntry[Text, JsonValueT]]: ...
        def info(
            self, last_known_id: Optional[Text | int] = None, **kwargs: KWARGS
        ) -> LogMainList[LogEntry[Text, JsonValueT]]: ...
        def normal(
            self, last_known_id: Optional[Text | int] = None, **kwargs: KWARGS
        ) -> LogMainList[LogEntry[Text, JsonValueT]]: ...
        def warning(
            self, last_known_id: Optional[Text | int] = None, **kwargs: KWARGS
        ) -> LogMainList[LogEntry[Text, JsonValueT]]: ...
        def critical(
            self, last_known_id: Optional[Text | int] = None, **kwargs: KWARGS
        ) -> LogMainList[LogEntry[Text, JsonValueT]]: ...

class LogAPIMixIn(AppAPIMixIn):
    @property
    def log(self) -> Log: ...
    def log_main(
        self,
        normal: Optional[bool] = None,
        info: Optional[bool] = None,
        warning: Optional[bool] = None,
        critical: Optional[bool] = None,
        last_known_id: Optional[bool] = None,
        **kwargs: KWARGS
    ) -> LogMainList[LogEntry[Text, JsonValueT]]: ...
    def log_peers(
        self, last_known_id: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> LogPeersList[LogPeer[Text, JsonValueT]]: ...
