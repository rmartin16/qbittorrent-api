from typing import Dict
from typing import Iterable
from typing import MutableMapping
from typing import Text
from urllib.parse import ParseResult

from requests import Response
from requests import Session

from qbittorrentapi.app import Application
from qbittorrentapi.auth import Authorization
from qbittorrentapi.definitions import APINames
from qbittorrentapi.log import Log
from qbittorrentapi.rss import RSS
from qbittorrentapi.search import Search
from qbittorrentapi.sync import Sync
from qbittorrentapi.torrents import TorrentCategories
from qbittorrentapi.torrents import Torrents
from qbittorrentapi.torrents import TorrentTags
from qbittorrentapi.transfer import Transfer

class URL(object):
    client: Request
    def __init__(self, client: Request) -> None: ...
    def build_url(
        self,
        api_namespace: APINames | Text,
        api_method: Text,
        headers: MutableMapping,
        requests_kwargs: MutableMapping,
    ) -> str: ...
    def build_base_url(
        self, headers: MutableMapping, requests_kwargs: MutableMapping
    ) -> str: ...
    def detect_scheme(
        self,
        base_url: ParseResult,
        alt_scheme: Text,
        default_scheme: Text,
        headers: MutableMapping,
        requests_kwargs: MutableMapping,
    ) -> str: ...
    def build_url_path(
        self, api_namespace: APINames | Text, api_method: Text
    ) -> str: ...

class Request(object):
    host: Text
    port: Text | int
    username: Text
    _password: Text
    _url: URL
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

    _EXTRA_HEADERS: MutableMapping | None
    _REQUESTS_ARGS: MutableMapping | None
    _VERIFY_WEBUI_CERTIFICATE: bool | None
    _FORCE_SCHEME_FROM_HOST: bool | None
    _RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool | None
    _RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool | None
    _RAISE_UNSUPPORTEDVERSIONERROR: bool | None
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
        EXTRA_HEADERS: MutableMapping = None,
        REQUESTS_ARGS: MutableMapping = None,
        VERIFY_WEBUI_CERTIFICATE: bool = True,
        FORCE_SCHEME_FROM_HOST: bool = False,
        RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool = False,
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool = False,
        RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS: bool = False,
        VERBOSE_RESPONSE_LOGGING: bool = False,
        PRINT_STACK_FOR_EACH_REQUEST: bool = False,
        SIMPLE_RESPONSES: bool = False,
        DISABLE_LOGGING_DEBUG_OUTPUT: bool = False,
        MOCK_WEB_API_VERSION: Text = None,
    ) -> None: ...
    @classmethod
    def _list2string(cls, input_list: Iterable = None, delimiter: Text = "|"): ...
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
        requests_args: MutableMapping = None,
        requests_params: MutableMapping = None,
        headers: MutableMapping = None,
        params: MutableMapping = None,
        data: MutableMapping = None,
        files: MutableMapping = None,
        **kwargs
    ) -> Response: ...
    def _trim_known_kwargs(self, **kwargs) -> Dict: ...
    def _get_requests_kwargs(
        self,
        requests_args: MutableMapping = None,
        requests_params: MutableMapping = None,
    ): ...
    def _get_headers(
        self, headers: MutableMapping = None, requests_kwargs: MutableMapping = None
    ): ...
    def _get_data(
        self,
        http_method: Text,
        params: MutableMapping = None,
        data: MutableMapping = None,
        files: MutableMapping = None,
        **kwargs
    ): ...
    @property
    def _session(self) -> Session: ...
    @staticmethod
    def _handle_error_responses(
        data: MutableMapping, params: MutableMapping, response: Response
    ): ...
    def _verbose_logging(
        self,
        http_method: Text,
        url: Text,
        data: MutableMapping,
        params: MutableMapping,
        requests_kwargs: MutableMapping,
        response: Response,
    ): ...
