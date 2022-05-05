from typing import Text

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.auth import AuthAPIMixIn
from qbittorrentapi.log import LogAPIMixIn
from qbittorrentapi.request import Request
from qbittorrentapi.rss import RSSAPIMixIn
from qbittorrentapi.search import SearchAPIMixIn
from qbittorrentapi.sync import SyncAPIMixIn
from qbittorrentapi.torrents import TorrentsAPIMixIn
from qbittorrentapi.transfer import TransferAPIMixIn

class Client(
    AppAPIMixIn,
    AuthAPIMixIn,
    LogAPIMixIn,
    SyncAPIMixIn,
    TransferAPIMixIn,
    TorrentsAPIMixIn,
    Request,
    RSSAPIMixIn,
    SearchAPIMixIn,
):
    def __init__(
        self,
        host: Text = "",
        port: Text | int = None,
        username: Text = None,
        password: Text = None,
        **kwargs
    ) -> None: ...
