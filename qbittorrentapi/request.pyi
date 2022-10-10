from typing import IO
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Text
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union
from urllib.parse import ParseResult

import six
from requests import Response
from requests import Session

from qbittorrentapi.app import Application
from qbittorrentapi.auth import Authorization
from qbittorrentapi.definitions import APINames
from qbittorrentapi.definitions import Dictionary
from qbittorrentapi.definitions import List
from qbittorrentapi.log import Log
from qbittorrentapi.rss import RSS
from qbittorrentapi.search import Search
from qbittorrentapi.sync import Sync
from qbittorrentapi.torrents import TorrentCategories
from qbittorrentapi.torrents import Torrents
from qbittorrentapi.torrents import TorrentTags
from qbittorrentapi.transfer import Transfer

KWARGS = Any
TorrentFilesT = (
    Tuple[Mapping[Text, IO[bytes] | Tuple[Text, IO[bytes]]], List[IO[bytes]]]
    | Tuple[None, None]
)
FinalResponseT = TypeVar(
    "FinalResponseT",
    bound=Union[six.text_type, int, bytes, List[Any], Dictionary[Any, Any]],
)

class URL(object):
    client: Request
    def __init__(self, client: Request) -> None: ...
    def build_url(
        self,
        api_namespace: APINames | Text,
        api_method: Text,
        headers: Mapping[Text, Text],
        requests_kwargs: Mapping[Text, Any],
    ) -> str: ...
    def build_base_url(
        self, headers: Mapping[Text, Text], requests_kwargs: Mapping[Text, Any]
    ) -> str: ...
    def detect_scheme(
        self,
        base_url: ParseResult,
        alt_scheme: Text,
        default_scheme: Text,
        headers: Mapping[Text, Text],
        requests_kwargs: Mapping[Text, Any],
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

    _EXTRA_HEADERS: Mapping[Text, Text] | None
    _REQUESTS_ARGS: Mapping[Text, Any] | None
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
        host: Optional[Text] = None,
        port: Optional[Text | int] = None,
        username: Optional[Text] = None,
        password: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    def _initialize_context(self) -> None: ...
    def _initialize_lesser(
        self,
        EXTRA_HEADERS: Optional[Mapping[Text, Text]] = None,
        REQUESTS_ARGS: Optional[Mapping[Text, Any]] = None,
        VERIFY_WEBUI_CERTIFICATE: bool = True,
        FORCE_SCHEME_FROM_HOST: bool = False,
        RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool = False,
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool = False,
        RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS: bool = False,
        VERBOSE_RESPONSE_LOGGING: bool = False,
        PRINT_STACK_FOR_EACH_REQUEST: bool = False,
        SIMPLE_RESPONSES: bool = False,
        DISABLE_LOGGING_DEBUG_OUTPUT: bool = False,
        MOCK_WEB_API_VERSION: Optional[Text] = None,
    ) -> None: ...
    @classmethod
    def _list2string(
        cls, input_list: Optional[Iterable[Any]] = None, delimiter: Text = "|"
    ) -> Text: ...
    def _trigger_session_initialization(self) -> None: ...
    def _get(
        self,
        _name: APINames | Text,
        _method: Text,
        requests_args: Optional[Mapping[Text, Any]] = None,
        requests_params: Optional[Mapping[Text, Any]] = None,
        headers: Optional[Mapping[Text, Text]] = None,
        params: Optional[Mapping[Text, Any]] = None,
        data: Optional[Mapping[Text, Any]] = None,
        files: Optional[TorrentFilesT] = None,
        response_class: Optional[Type[FinalResponseT]] = None,
        **kwargs: KWARGS
    ) -> FinalResponseT: ...
    def _post(
        self,
        _name: APINames | Text,
        _method: Text,
        requests_args: Optional[Mapping[Text, Any]] = None,
        requests_params: Optional[Mapping[Text, Any]] = None,
        headers: Optional[Mapping[Text, Text]] = None,
        params: Optional[Mapping[Text, Any]] = None,
        data: Optional[Mapping[Text, Any]] = None,
        files: Optional[TorrentFilesT] = None,
        response_class: Optional[Type[FinalResponseT]] = None,
        **kwargs: KWARGS
    ) -> FinalResponseT: ...
    def _request_manager(
        self,
        _retries: int,
        _retry_backoff_factor: float,
        api_namespace: APINames | Text,
        api_method: Text,
        http_method: Text,
        requests_args: Optional[Mapping[Text, Any]] = None,
        requests_params: Optional[Mapping[Text, Any]] = None,
        headers: Optional[Mapping[Text, Text]] = None,
        params: Optional[Mapping[Text, Any]] = None,
        data: Optional[Mapping[Text, Any]] = None,
        files: Optional[TorrentFilesT] = None,
        response_class: Optional[Type[FinalResponseT]] = None,
        **kwargs: KWARGS
    ) -> FinalResponseT: ...
    def _request(
        self,
        http_method: Text,
        api_namespace: APINames | Text,
        api_method: Text,
        requests_args: Optional[Mapping[Text, Any]] = None,
        requests_params: Optional[Mapping[Text, Any]] = None,
        headers: Optional[Mapping[Text, Text]] = None,
        params: Optional[Mapping[Text, Any]] = None,
        data: Optional[Mapping[Text, Any]] = None,
        files: Optional[TorrentFilesT] = None,
        response_class: Optional[Type[FinalResponseT]] = None,
        **kwargs: KWARGS
    ) -> FinalResponseT: ...
    def _get_response_kwargs(
        self, kwargs: Mapping[Text, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]: ...
    def _get_requests_kwargs(
        self,
        requests_args: Optional[Mapping[Text, Any]] = None,
        requests_params: Optional[Mapping[Text, Any]] = None,
    ) -> Dict[Text, Any]: ...
    def _get_headers(
        self,
        headers: Optional[Mapping[Text, Text]] = None,
        requests_kwargs: Optional[Mapping[Text, Any]] = None,
    ) -> Dict[Text, Text]: ...
    def _get_data(
        self,
        http_method: Text,
        params: Optional[Mapping[Text, Any]] = None,
        data: Optional[Mapping[Text, Any]] = None,
        files: Optional[TorrentFilesT] = None,
        **kwargs: KWARGS
    ) -> Tuple[Dict[Text, Any], Dict[Text, Any], TorrentFilesT]: ...
    def _cast(
        self,
        response: Response,
        response_class: Type[FinalResponseT],
        **response_kwargs: KWARGS
    ) -> FinalResponseT: ...
    @property
    def _session(self) -> Session: ...
    @staticmethod
    def _handle_error_responses(
        data: Mapping[Text, Any],
        params: Mapping[Text, Any],
        response: Response,
    ) -> None: ...
    def _verbose_logging(
        self,
        http_method: Text,
        url: Text,
        data: Mapping[Text, Any],
        params: Mapping[Text, Any],
        requests_kwargs: Mapping[Text, Any],
        response: Response,
    ) -> None: ...
