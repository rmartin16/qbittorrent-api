from typing import Dict, Mapping, Iterable, Text

from requests import Response, Session

from qbittorrentapi.app import Application
from qbittorrentapi.auth import Authorization
from qbittorrentapi.definitions import APINames
from qbittorrentapi.log import Log
from qbittorrentapi.rss import RSS
from qbittorrentapi.search import Search
from qbittorrentapi.sync import Sync
from qbittorrentapi.torrents import TorrentCategories
from qbittorrentapi.torrents import TorrentTags
from qbittorrentapi.torrents import Torrents
from qbittorrentapi.transfer import Transfer

class HelpersMixIn:
    @classmethod
    def _list2string(cls, input_list: Iterable = None, delimiter: Text = "|"): ...
    @classmethod
    def _suppress_context(cls, exc: Exception): ...
    @classmethod
    def _is_version_less_than(cls, ver1: Text, ver2: Text, lteq: bool = True): ...

class Request(HelpersMixIn):
    host: Text
    port: Text | int
    username: Text
    _password: Text

    _http_session: Session | None

    _application: Application | None
    _authorization: Authorization | None
    _transfer: Transfer | None
    _torrents: Torrents | None
    _torrent_categories: TorrentCategories | None
    _torrent_tags: TorrentTags | None
    _log: Log | None
    _sync: Sync | None
    _rss: RSS | None
    _search: Search | None

    _API_BASE_URL: Text | None
    _API_BASE_PATH: Text | None

    _EXTRA_HEADERS: Mapping | None
    _REQUESTS_ARGS: Mapping | None
    _VERIFY_WEBUI_CERTIFICATE: bool | None
    _FORCE_SCHEME_FROM_HOST: bool | None
    _RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool | None
    _RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool | None
    _VERBOSE_RESPONSE_LOGGING: bool | None
    _PRINT_STACK_FOR_EACH_REQUEST: bool | None
    _SIMPLE_RESPONSES: bool | None
    _DISABLE_LOGGING_DEBUG_OUTPUT: bool | None
    _MOCK_WEB_API_VERSION: Text | None
    def __init__(
        self,
        host: Text = None,
        port: Text | int = None,
        username: Text = None,
        password: Text = None,
        **kwargs
    ) -> None: ...
    def _initialize_context(self) -> None: ...
    def _initialize_lesser(
        self,
        EXTRA_HEADERS: Mapping = None,
        REQUESTS_ARGS: Mapping = None,
        VERIFY_WEBUI_CERTIFICATE: bool = True,
        FORCE_SCHEME_FROM_HOST: bool = False,
        RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool = False,
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool = False,
        VERBOSE_RESPONSE_LOGGING: bool = False,
        PRINT_STACK_FOR_EACH_REQUEST: bool = False,
        SIMPLE_RESPONSES: bool = False,
        DISABLE_LOGGING_DEBUG_OUTPUT: bool = False,
        MOCK_WEB_API_VERSION: Text = None,
    ) -> None: ...
    def _trigger_session_initialization(self) -> None: ...
    def _get(self, _name: APINames | Text, _method: Text, **kwargs) -> Response: ...
    def _post(self, _name: APINames | Text, _method: Text, **kwargs) -> Response: ...
    def _request_manager(
        self, _retries: int, _retry_backoff_factor: float, **kwargs
    ) -> Response: ...
    def _request(
        self,
        http_method: Text,
        api_namespace: APINames | Text,
        api_method: Text,
        **kwargs
    ) -> Response: ...
    def _normalize_args(
        self,
        http_method: Text,
        headers: Mapping = None,
        data: Mapping = None,
        params: Mapping = None,
        files: Mapping = None,
        requests_params: Mapping = None,
        requests_args: Mapping = None,
    ): ...
    def _trim_known_kwargs(self, **kwargs) -> Dict: ...
    def _get_requests_args(self, **kwargs) -> Dict: ...
    def _build_url(
        self, api_namespace: APINames | Text, api_method: Text, requests_args: Mapping
    ): ...
    @property
    def _session(self) -> Session: ...
    @staticmethod
    def _handle_error_responses(args: Mapping, response: Response): ...
    def _verbose_logging(
        self, http_method: Text, url: Text, http_args: Mapping, response: Response
    ): ...
