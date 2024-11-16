from __future__ import annotations

from collections.abc import Iterable, Mapping
from json import loads
from logging import Logger, NullHandler, getLogger
from os import environ
from time import sleep
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast
from urllib.parse import ParseResult, urljoin, urlparse

from requests import Response, Session
from requests import exceptions as requests_exceptions
from requests.adapters import HTTPAdapter
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry

from qbittorrentapi._version_support import v
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    Dictionary,
    FilesToSendT,
    List,
)
from qbittorrentapi.exceptions import (
    APIConnectionError,
    APIError,
    Conflict409Error,
    Forbidden403Error,
    HTTP5XXError,
    HTTP403Error,
    HTTPError,
    InternalServerError500Error,
    InvalidRequest400Error,
    MethodNotAllowed405Error,
    MissingRequiredParameters400Error,
    NotFound404Error,
    Unauthorized401Error,
    UnsupportedMediaType415Error,
)

if TYPE_CHECKING:
    from qbittorrentapi.app import Application
    from qbittorrentapi.auth import Authorization
    from qbittorrentapi.log import Log
    from qbittorrentapi.rss import RSS
    from qbittorrentapi.search import Search
    from qbittorrentapi.sync import Sync
    from qbittorrentapi.torrentcreator import TorrentCreator
    from qbittorrentapi.torrents import TorrentCategories, Torrents, TorrentTags
    from qbittorrentapi.transfer import Transfer

T = TypeVar("T")
ExceptionT = TypeVar("ExceptionT", bound=requests_exceptions.RequestException)
ResponseT = TypeVar("ResponseT")

logger: Logger = getLogger(__name__)
getLogger("qbittorrentapi").addHandler(NullHandler())


class QbittorrentURL:
    """Management for the qBittorrent Web API URL."""

    def __init__(self, client: Request):
        self.client = client
        self._base_url: str | None = None

    def build(
        self,
        api_namespace: APINames | str,
        api_method: str,
        headers: Mapping[str, str] | None = None,
        requests_kwargs: Mapping[str, Any] | None = None,
        base_path: str = "api/v2",
    ) -> str:
        """
        Create a fully qualified URL for the API endpoint.

        :param api_namespace: the namespace for the API endpoint (e.g. ``torrents``)
        :param api_method: the specific method for the API endpoint (e.g. ``info``)
        :param base_path: base path for URL (e.g. ``api/v2``)
        :param headers: HTTP headers for request
        :param requests_kwargs: kwargs for any calls to Requests
        :return: fully qualified URL string for endpoint
        """
        # since base_url is guaranteed to end in a slash and api_path will never
        # start with a slash, this join only ever append to the path in base_url
        return urljoin(
            self.build_base_url(headers or {}, requests_kwargs or {}),
            "/".join((base_path, api_namespace, api_method)).strip("/"),
        )

    def build_base_url(
        self,
        headers: Mapping[str, str],
        requests_kwargs: Mapping[str, Any],
    ) -> str:
        """
        Determine the Base URL for the Web API endpoints.

        A URL is only actually built here if it's the first time here or
        the context was re-initialized. Otherwise, the most recently
        built URL is used.

        If the user doesn't provide a scheme for the URL, it will try HTTP
        first and fall back to HTTPS if that doesn't work. While this is
        probably backwards, qBittorrent or an intervening proxy can simply
        redirect to HTTPS and that'll be respected.

        Additionally, if users want to augment the path to the API endpoints,
        any path provided here will be preserved in the returned Base URL
        and prefixed to all subsequent API calls.

        :param headers: HTTP headers for request
        :param requests_kwargs: arguments from user for HTTP ``HEAD`` request
        :return: base URL as a ``string`` for Web API endpoint
        """
        if self._base_url is not None:
            return self._base_url

        # Parse user host - urlparse requires some sort of scheme for parsing to work
        host = self.client.host
        if not host.lower().startswith(("http:", "https:", "//")):
            host = "//" + self.client.host
        base_url = urlparse(url=host)
        logger.debug("Parsed user URL: %r", base_url)

        # default to HTTP if user didn't specify
        user_scheme = base_url.scheme.lower()
        default_scheme = user_scheme or "http"
        alt_scheme = "https" if default_scheme == "http" else "http"

        # add port number if host doesn't contain one
        if self.client.port is not None and not base_url.port:
            host = "".join((base_url.netloc, ":", str(self.client.port)))
            base_url = base_url._replace(netloc=host)

        # detect whether Web API is configured for HTTP or HTTPS
        if not (user_scheme and self.client._FORCE_SCHEME_FROM_HOST):
            scheme = self.detect_scheme(
                base_url, default_scheme, alt_scheme, headers, requests_kwargs
            )
            base_url = base_url._replace(scheme=scheme)
            if user_scheme and user_scheme != base_url.scheme:
                logger.warning(
                    "Using '%s' instead of requested '%s'"
                    "to communicate with qBittorrent",
                    base_url.scheme,
                    user_scheme,
                )

        # ensure URL always ends with a forward-slash
        base_url_str = base_url.geturl()
        if not base_url_str.endswith("/"):
            base_url_str += "/"
        logger.debug("Base URL: %s", base_url_str)

        # force a new session to be created now that the URL is known
        self.client._trigger_session_initialization()

        self._base_url = base_url_str
        return self._base_url

    def detect_scheme(
        self,
        base_url: ParseResult,
        default_scheme: str,
        alt_scheme: str,
        headers: Mapping[str, str],
        requests_kwargs: Mapping[str, Any],
    ) -> str:
        """
        Determine if the URL endpoint is using HTTP or HTTPS.

        :param base_url: urllib :class:`~urllib.parse.ParseResult` URL object
        :param default_scheme: default scheme to use for URL
        :param alt_scheme: alternative scheme to use for URL if default doesn't work
        :param headers: HTTP headers for request
        :param requests_kwargs: kwargs for calls to Requests
        :return: scheme (i.e. ``HTTP`` or ``HTTPS``)
        """
        logger.debug("Detecting scheme for URL...")
        prefer_https = False
        for scheme in (default_scheme, alt_scheme):
            try:
                base_url = base_url._replace(scheme=scheme)
                r = self.client._session.request(
                    "head", base_url.geturl(), headers=headers, **requests_kwargs
                )
                scheme_to_use: str = urlparse(r.url).scheme
                break
            except requests_exceptions.SSLError:
                # an SSLError means that qBittorrent is likely listening on HTTPS
                # but the TLS connection is not trusted...so, if the attempt to
                # connect on HTTP also fails, this will tell us to switch back to HTTPS
                logger.debug("Encountered SSLError: will prefer HTTPS if HTTP fails")
                prefer_https = True
            except requests_exceptions.RequestException:
                logger.debug("Failed connection attempt with %s", scheme.upper())
        else:
            scheme_to_use = "https" if prefer_https else "http"
        # use detected scheme
        logger.debug("Using %s scheme", scheme_to_use.upper())
        return scheme_to_use


class QbittorrentSession(Session):
    """
    Wrapper to augment Requests Session.

    Requests doesn't allow Session to default certain configuration globally. This gets
    around that by setting defaults for each request.
    """

    def request(self, method: str, url: str, **kwargs: Any) -> Response:  # type: ignore[override]
        kwargs.setdefault("timeout", 15.1)
        kwargs.setdefault("allow_redirects", True)

        # send Content-Length as 0 for empty POSTs...Requests will not send
        # Content-Length if data is empty but qBittorrent will complain otherwise
        data = kwargs.get("data") or {}
        is_data = any(x is not None for x in data.values())
        if method.lower() == "post" and not is_data:
            kwargs.setdefault("headers", {}).update({"Content-Length": "0"})

        return super().request(method, url, **kwargs)


class Request:
    """Facilitates HTTP requests to qBittorrent's Web API."""

    def __init__(
        self,
        host: str | None = None,
        port: str | int | None = None,
        username: str | None = None,
        password: str | None = None,
        EXTRA_HEADERS: Mapping[str, str] | None = None,
        REQUESTS_ARGS: Mapping[str, Any] | None = None,
        HTTPADAPTER_ARGS: Mapping[str, Any] | None = None,
        VERIFY_WEBUI_CERTIFICATE: bool = True,
        FORCE_SCHEME_FROM_HOST: bool = False,
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool = False,
        RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS: bool = False,
        VERBOSE_RESPONSE_LOGGING: bool = False,
        SIMPLE_RESPONSES: bool = False,
        DISABLE_LOGGING_DEBUG_OUTPUT: bool = False,
    ) -> None:
        self.host = host or ""
        self.port = port
        self.username = username or ""
        self._password = password or ""

        self._initialize_settings(
            EXTRA_HEADERS=EXTRA_HEADERS,
            REQUESTS_ARGS=REQUESTS_ARGS,
            HTTPADAPTER_ARGS=HTTPADAPTER_ARGS,
            VERIFY_WEBUI_CERTIFICATE=VERIFY_WEBUI_CERTIFICATE,
            FORCE_SCHEME_FROM_HOST=FORCE_SCHEME_FROM_HOST,
            RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=(
                RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS
            ),
            RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=(
                RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS
            ),
            VERBOSE_RESPONSE_LOGGING=VERBOSE_RESPONSE_LOGGING,
            SIMPLE_RESPONSES=SIMPLE_RESPONSES,
            DISABLE_LOGGING_DEBUG_OUTPUT=DISABLE_LOGGING_DEBUG_OUTPUT,
        )

        self._url = QbittorrentURL(client=self)
        self._http_session: QbittorrentSession | None = None

        self._application: Application | None = None
        self._authorization: Authorization | None = None
        self._log: Log | None = None
        self._rss: RSS | None = None
        self._search: Search | None = None
        self._sync: Sync | None = None
        self._torrents: Torrents | None = None
        self._torrent_categories: TorrentCategories | None = None
        self._torrent_tags: TorrentTags | None = None
        self._torrentcreator: TorrentCreator | None = None
        self._transfer: Transfer | None = None

        # turn off console-printed warnings about SSL certificate issues.
        # these errors are only shown once the user has explicitly allowed
        # untrusted certs via VERIFY_WEBUI_CERTIFICATE...so printing them
        # in a console isn't particularly useful.
        if not self._VERIFY_WEBUI_CERTIFICATE:
            disable_warnings(InsecureRequestWarning)

    def _initialize_context(self) -> None:
        """
        Initialize and reset communications context with qBittorrent.

        This is necessary on startup or when the authorization cookie needs
        to be replaced...perhaps because it expired, qBittorrent was
        restarted, significant settings changes, etc.
        """
        logger.debug("Re-initializing context...")

        # reset URL so the full URL is derived again
        # (primarily allows for switching scheme for WebUI: HTTP <-> HTTPS)
        self._url = QbittorrentURL(client=self)

        # reset comm session so it is rebuilt with new auth cookie and all
        self._trigger_session_initialization()

        # reinitialize interaction layers
        self._application = None
        self._authorization = None
        self._transfer = None
        self._torrents = None
        self._torrent_categories = None
        self._torrent_tags = None
        self._torrentcreator = None
        self._log = None
        self._sync = None
        self._rss = None
        self._search = None

    def _initialize_settings(
        self,
        EXTRA_HEADERS: Mapping[str, str] | None = None,
        REQUESTS_ARGS: Mapping[str, Any] | None = None,
        HTTPADAPTER_ARGS: Mapping[str, Any] | None = None,
        VERIFY_WEBUI_CERTIFICATE: bool = True,
        FORCE_SCHEME_FROM_HOST: bool = False,
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: bool = False,
        RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS: bool = False,
        VERBOSE_RESPONSE_LOGGING: bool = False,
        SIMPLE_RESPONSES: bool = False,
        DISABLE_LOGGING_DEBUG_OUTPUT: bool = False,
    ) -> None:
        """Initialize lesser used configuration."""

        # Configuration parameters
        self._EXTRA_HEADERS = dict(EXTRA_HEADERS) if EXTRA_HEADERS is not None else {}
        self._REQUESTS_ARGS = dict(REQUESTS_ARGS) if REQUESTS_ARGS is not None else {}
        self._HTTPADAPTER_ARGS = (
            dict(HTTPADAPTER_ARGS) if HTTPADAPTER_ARGS is not None else {}
        )
        self._VERIFY_WEBUI_CERTIFICATE = bool(VERIFY_WEBUI_CERTIFICATE)
        self._VERBOSE_RESPONSE_LOGGING = bool(VERBOSE_RESPONSE_LOGGING)
        self._SIMPLE_RESPONSES = bool(SIMPLE_RESPONSES)
        self._FORCE_SCHEME_FROM_HOST = bool(FORCE_SCHEME_FROM_HOST)
        self._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS = bool(
            RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS
        )
        self._RAISE_UNSUPPORTEDVERSIONERROR = bool(
            RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS
        )
        if bool(DISABLE_LOGGING_DEBUG_OUTPUT):
            for logger_ in ["qbittorrentapi", "requests", "urllib3"]:
                if getLogger(logger_).level < 20:
                    getLogger(logger_).setLevel("INFO")

        # Environment variables have the lowest priority
        if not self.host:
            env_host = environ.get(
                "QBITTORRENTAPI_HOST",
                environ.get("PYTHON_QBITTORRENTAPI_HOST"),
            )
            if env_host is not None:
                logger.debug(
                    "Using QBITTORRENTAPI_HOST env variable for qBittorrent host"
                )
                self.host = env_host
        if not self.username:
            env_username = environ.get(
                "QBITTORRENTAPI_USERNAME",
                environ.get("PYTHON_QBITTORRENTAPI_USERNAME"),
            )
            if env_username is not None:
                logger.debug("Using QBITTORRENTAPI_USERNAME env variable for username")
                self.username = env_username
        if not self._password:
            env_password = environ.get(
                "QBITTORRENTAPI_PASSWORD",
                environ.get("PYTHON_QBITTORRENTAPI_PASSWORD"),
            )
            if env_password is not None:
                logger.debug("Using QBITTORRENTAPI_PASSWORD env variable for password")
                self._password = env_password
        if self._VERIFY_WEBUI_CERTIFICATE is True:
            env_verify_cert = environ.get(
                "QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE",
                environ.get("PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE"),
            )
            if env_verify_cert is not None:
                self._VERIFY_WEBUI_CERTIFICATE = False

        self._PRINT_STACK_FOR_EACH_REQUEST = False

    @classmethod
    def _list2string(cls, input_list: T, delimiter: str = "|") -> str | T:
        """
        Convert entries in a list to a concatenated string.

        :param input_list: list to convert
        :param delimiter: delimiter for concatenation
        """
        if isinstance(input_list, Iterable) and not isinstance(input_list, str):
            return delimiter.join(map(str, input_list))
        return input_list

    def _get(
        self,
        _name: APINames | str,
        _method: str,
        requests_args: Mapping[str, Any] | None = None,
        requests_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: FilesToSendT | None = None,
        response_class: type = Response,
        version_introduced: str = "",
        version_removed: str = "",
        **kwargs: APIKwargsT,
    ) -> Any:
        """
        Send ``GET`` request.

        :param api_namespace: the namespace for the API endpoint
            (e.g. :class:`~qbittorrentapi.definitions.APINames` or ``torrents``)
        :param api_method: the name for the API endpoint (e.g. ``add``)
        :param kwargs: see :meth:`~Request._request`
        :return: Requests :class:`~requests.Response`
        """
        return self._auth_request(
            http_method="get",
            api_namespace=_name,
            api_method=_method,
            requests_args=requests_args,
            requests_params=requests_params,
            headers=headers,
            params=params,
            data=data,
            files=files,
            response_class=response_class,
            version_introduced=version_introduced,
            version_removed=version_removed,
            **kwargs,
        )

    def _get_cast(
        self,
        _name: APINames | str,
        _method: str,
        response_class: type[ResponseT],
        requests_args: Mapping[str, Any] | None = None,
        requests_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: FilesToSendT | None = None,
        version_introduced: str = "",
        version_removed: str = "",
        **kwargs: APIKwargsT,
    ) -> ResponseT:
        """
        Send ``GET`` request with casted response.

        :param api_namespace: the namespace for the API endpoint
            (e.g. :class:`~qbittorrentapi.definitions.APINames` or ``torrents``)
        :param api_method: the name for the API endpoint (e.g. ``add``)
        :param kwargs: see :meth:`~Request._request`
        """
        return cast(
            ResponseT,
            self._auth_request(
                http_method="get",
                api_namespace=_name,
                api_method=_method,
                requests_args=requests_args,
                requests_params=requests_params,
                headers=headers,
                params=params,
                data=data,
                files=files,
                response_class=response_class,
                version_introduced=version_introduced,
                version_removed=version_removed,
                **kwargs,
            ),
        )

    def _post(
        self,
        _name: APINames | str,
        _method: str,
        requests_args: Mapping[str, Any] | None = None,
        requests_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: FilesToSendT | None = None,
        response_class: type = Response,
        version_introduced: str = "",
        version_removed: str = "",
        **kwargs: APIKwargsT,
    ) -> Any:
        """
        Send ``POST`` request.

        :param api_namespace: the namespace for the API endpoint
            (e.g. :class:`~qbittorrentapi.definitions.APINames` or ``torrents``)
        :param api_method: the name for the API endpoint (e.g. ``add``)
        :param kwargs: see :meth:`~Request._request`
        """
        return self._auth_request(
            http_method="post",
            api_namespace=_name,
            api_method=_method,
            requests_args=requests_args,
            requests_params=requests_params,
            headers=headers,
            params=params,
            data=data,
            files=files,
            response_class=response_class,
            version_introduced=version_introduced,
            version_removed=version_removed,
            **kwargs,
        )

    def _post_cast(
        self,
        _name: APINames | str,
        _method: str,
        response_class: type[ResponseT],
        requests_args: Mapping[str, Any] | None = None,
        requests_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: FilesToSendT | None = None,
        version_introduced: str = "",
        version_removed: str = "",
        **kwargs: APIKwargsT,
    ) -> ResponseT:
        """
        Send ``POST`` request with casted response.

        :param api_namespace: the namespace for the API endpoint
            (e.g. :class:`~qbittorrentapi.definitions.APINames` or ``torrents``)
        :param api_method: the name for the API endpoint (e.g. ``add``)
        :param kwargs: see :meth:`~Request._request`
        """
        return cast(
            ResponseT,
            self._auth_request(
                http_method="post",
                api_namespace=_name,
                api_method=_method,
                requests_args=requests_args,
                requests_params=requests_params,
                headers=headers,
                params=params,
                data=data,
                files=files,
                response_class=response_class,
                version_introduced=version_introduced,
                version_removed=version_removed,
                **kwargs,
            ),
        )

    def _auth_request(
        self,
        http_method: Literal["get", "GET", "post", "POST"],
        api_namespace: APINames | str,
        api_method: str,
        _retry_backoff_factor: float = 0.3,
        requests_args: Mapping[str, Any] | None = None,
        requests_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: FilesToSendT | None = None,
        response_class: type = Response,
        version_introduced: str = "",
        version_removed: str = "",
        **kwargs: APIKwargsT,
    ) -> Any:
        """Wraps API call with re-authorization if first attempt is not authorized."""
        try:
            return self._request_manager(
                http_method=http_method,
                api_namespace=api_namespace,
                api_method=api_method,
                requests_args=requests_args,
                requests_params=requests_params,
                headers=headers,
                params=params,
                data=data,
                files=files,
                response_class=response_class,
                version_introduced=version_introduced,
                version_removed=version_removed,
                **kwargs,
            )
        except HTTP403Error:
            # Do not retry auth endpoints for 403. If an auth endpoint is returning
            # 403, then trying again won't work because it is likely the credentials
            # are no longer valid. Furthermore, it leads to infinite recursion.
            if api_namespace == APINames.Authorization:
                raise
            logger.debug("Login may have expired...attempting new login")
            self.auth_log_in(  # type: ignore[attr-defined]
                requests_args=requests_args,
                requests_params=requests_params,
                headers=headers,
            )
            return self._request_manager(
                http_method=http_method,
                api_namespace=api_namespace,
                api_method=api_method,
                requests_args=requests_args,
                requests_params=requests_params,
                headers=headers,
                params=params,
                data=data,
                files=files,
                response_class=response_class,
                version_introduced=version_introduced,
                version_removed=version_removed,
                **kwargs,
            )

    def _request_manager(
        self,
        http_method: Literal["get", "GET", "post", "POST"],
        api_namespace: APINames | str,
        api_method: str,
        _retries: int = 1,
        _retry_backoff_factor: float = 0.3,
        requests_args: Mapping[str, Any] | None = None,
        requests_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: FilesToSendT | None = None,
        response_class: type = Response,
        version_introduced: str = "",
        version_removed: str = "",
        **kwargs: APIKwargsT,
    ) -> Any:
        """
        Wrapper to manage request retries and severe exceptions.

        This should retry at least once to account for the Web API switching from HTTP
        to HTTPS. During the second attempt, the URL is rebuilt using HTTP or HTTPS as
        appropriate.
        """
        if not self._is_endpoint_supported_for_version(
            endpoint=f"{api_namespace}/{api_method}",
            version_introduced=version_introduced,
            version_removed=version_removed,
        ):
            return None

        max_retries = _retries if _retries >= 1 else 1
        for retry in range(0, (max_retries + 1)):  # pragma: no branch
            try:
                return self._request(
                    http_method=http_method,
                    api_namespace=api_namespace,
                    api_method=api_method,
                    requests_args=requests_args,
                    requests_params=requests_params,
                    headers=headers,
                    params=params,
                    data=data,
                    files=files,
                    response_class=response_class,
                    **kwargs,
                )
            except HTTP5XXError:
                if retry >= max_retries:
                    raise
            except APIError:
                raise
            except Exception as exc:
                if retry >= max_retries:
                    err_msg = "Failed to connect to qBittorrent. " + {
                        requests_exceptions.SSLError: "This is likely due to using an "
                        "untrusted certificate (likely self-signed) for HTTPS "
                        "qBittorrent WebUI. To suppress this error (and skip "
                        "certificate verification consequently exposing the HTTPS "
                        "connection to man-in-the-middle attacks), set "
                        "VERIFY_WEBUI_CERTIFICATE=False when instantiating Client or "
                        "set environment variable "
                        "QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE to a "
                        f"non-null value. SSL Error: {repr(exc)}",
                        requests_exceptions.HTTPError: f"Invalid HTTP Response: {repr(exc)}",  # noqa: E501
                        requests_exceptions.TooManyRedirects: f"Too many redirects: {repr(exc)}",  # noqa: E501
                        requests_exceptions.ConnectionError: f"Connection Error: {repr(exc)}",  # noqa: E501
                        requests_exceptions.Timeout: f"Timeout Error: {repr(exc)}",
                        requests_exceptions.RequestException: f"Requests Error: {repr(exc)}",  # noqa: E501
                    }.get(
                        type(exc),  # type: ignore[arg-type]
                        f"Unknown Error: {repr(exc)}",
                    )
                    logger.debug(err_msg)
                    response: Response | None = getattr(exc, "response", None)
                    raise APIConnectionError(err_msg, response=response)

            if retry > 0:
                sleep(min(_retry_backoff_factor * 2**retry, 10))
            logger.debug("Retry attempt %d", retry + 1)

            self._initialize_context()  # reset connection for each retry

    def _is_endpoint_supported_for_version(
        self,
        endpoint: str,
        version_introduced: str,
        version_removed: str,
    ) -> bool:
        """
        Prevent using an API methods that doesn't exist in this version of qBittorrent.

        :param endpoint: name of the removed endpoint, e.g. torrents/ban_peers
        :param version_introduced: the Web API version the endpoint was introduced
        :param version_removed: the Web API version the endpoint was removed
        """
        error_message = ""

        if version_introduced and v(self.app.web_api_version) < v(version_introduced):  # type: ignore[attr-defined]
            error_message = (
                f"ERROR: Endpoint '{endpoint}' is Not Implemented in this version of "
                f"qBittorrent. This endpoint is available starting in Web API "
                f"v{version_introduced}."
            )

        if version_removed and v(self.app.web_api_version) >= v(version_removed):  # type: ignore[attr-defined]
            error_message = (
                f"ERROR: Endpoint '{endpoint}' is Not Implemented in this version of "
                f"qBittorrent. This endpoint was removed in Web API v{version_removed}."
            )

        if error_message:
            logger.debug(error_message)
            if self._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS:
                raise NotImplementedError(error_message)
            return False
        return True

    def _request(
        self,
        http_method: str,
        api_namespace: APINames | str,
        api_method: str,
        requests_args: Mapping[str, Any] | None = None,
        requests_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: FilesToSendT | None = None,
        response_class: type = Response,
        **kwargs: APIKwargsT,
    ) -> Any:
        """
        Meat and potatoes of sending requests to qBittorrent.

        :param http_method: ``get`` or ``post``
        :param api_namespace: the namespace for the API endpoint
            (e.g. :class:`~qbittorrentapi.definitions.APINames` or ``torrents``)
        :param api_method: the name for the API endpoint (e.g. ``add``)
        :param requests_args: default location for Requests kwargs
        :param requests_params: alternative location for Requests kwargs
        :param headers: HTTP headers to send with the request
        :param params: key/value pairs to send with a ``GET`` request
        :param data: key/value pairs to send with a ``POST`` request
        :param files: files to be sent with the request
        :param response_class: class to use to cast the API response
        :param kwargs: arbitrary keyword arguments to send with the request
        """
        http_method = http_method.lower()

        # keyword args that influence response handling
        response_kwargs = {
            "SIMPLE_RESPONSES": kwargs.pop(
                "SIMPLE_RESPONSES", kwargs.pop("SIMPLE_RESPONSE", False)
            )
        }

        # merge arguments for invoking Requests Session
        requests_kwargs = {
            **self._REQUESTS_ARGS,
            **(requests_args or requests_params or {}),
        }

        # merge HTTP headers to include with request
        final_headers = {
            **requests_kwargs.pop("headers", {}),
            **(headers or {}),
        }

        url = self._url.build(api_namespace, api_method, headers, requests_kwargs)

        final_params, final_data, final_files = self._format_payload(
            http_method, params, data, files, **kwargs
        )

        response = self._session.request(
            method=http_method,
            url=url,
            headers=final_headers,
            params=final_params,
            data=final_data,
            files=final_files,
            **requests_kwargs,
        )

        self._verbose_logging(url, final_data, final_params, requests_kwargs, response)
        self._handle_error_responses(final_data, final_params, response)
        return self._cast(response, response_class, **response_kwargs)

    @staticmethod
    def _format_payload(
        http_method: str,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        files: FilesToSendT | None = None,
        **kwargs: APIKwargsT,
    ) -> tuple[dict[str, Any], dict[str, Any], FilesToSendT]:
        """
        Determine ``data``, ``params``, and ``files`` for the Requests call.

        :param http_method: ``get`` or ``post``
        :param params: key value pairs to send with GET calls
        :param data: key value pairs to send with POST calls
        :param files: dictionary of files to send with request
        """
        params = dict(params) if params is not None else {}
        data = dict(data) if data is not None else {}
        files = dict(files) if files is not None else {}

        # any other keyword arguments are sent to qBittorrent as part of the request.
        # These are user-defined since this Client will put everything in
        # data/params/files that needs to be sent to qBittorrent.
        if kwargs:
            if http_method == "get":
                params.update(kwargs)
            if http_method == "post":
                data.update(kwargs)

        return params, data, files

    def _cast(
        self,
        response: Response,
        response_class: type,
        **response_kwargs: APIKwargsT,
    ) -> Any:
        """
        Returns the API response casted to the requested class.

        :param response: requests ``Response`` from API
        :param response_class: class to return response as; if none, response is returned
        :param response_kwargs: request-specific configuration for response
        """  # noqa: E501
        try:
            if response_class is Response:
                return response
            if response_class is str:
                return response.text
            if response_class is int:
                return int(response.text)
            if response_class is bytes:
                return response.content
            if issubclass(response_class, (Dictionary, List)):
                try:
                    json_response = response.json()
                except AttributeError:
                    # just in case the requests package doesn't contain json()
                    json_response = loads(response.text)
                if self._SIMPLE_RESPONSES or response_kwargs.get("SIMPLE_RESPONSES"):
                    return json_response
                else:
                    return response_class(json_response, client=self)
        except Exception as exc:
            logger.debug("Exception during response parsing.", exc_info=True)
            raise APIError(f"Exception during response parsing. Error: {exc!r}")
        else:
            logger.debug("No handler defined to cast response.", exc_info=True)
            raise APIError(f"No handler defined to cast response to {response_class}")

    @property
    def _session(self) -> QbittorrentSession:
        """Create or return existing HTTP session."""

        if self._http_session is not None:
            return self._http_session

        self._http_session = QbittorrentSession()

        # add any user-defined headers to be sent in all requests
        self._http_session.headers.update(self._EXTRA_HEADERS)

        # enable/disable TLS verification for all requests
        self._http_session.verify = self._VERIFY_WEBUI_CERTIFICATE

        # enable retries in Requests if HTTP call fails.
        # this is sorta doubling up on retries since request_manager() will
        # attempt retries as well. however, these retries will not delay.
        # so, if the problem is just a network blip then Requests will
        # automatically retry (with zero delay) and probably fix the issue
        # without coming all the way back to requests_wrapper. if this retries
        # is increased much above 1, and backoff_factor is non-zero, this
        # will start adding noticeable delays in these retry attempts...which
        # would then compound with similar delay logic in request_manager.
        # at any rate, the retries count in request_manager should always be
        # at least 2 to accommodate significant settings changes in qBittorrent
        # such as enabling HTTPs in Web UI settings.
        default_adapter_config = {
            "max_retries": Retry(
                total=1,
                read=1,
                connect=1,
                status_forcelist={500, 502, 504},
                raise_on_status=False,
            )
        }
        adapter = HTTPAdapter(
            **{
                **default_adapter_config,
                **self._HTTPADAPTER_ARGS,
            }
        )
        self._http_session.mount("http://", adapter)
        self._http_session.mount("https://", adapter)

        return self._http_session

    def __del__(self) -> None:
        """
        Close HTTP Session before destruction.

        This isn't strictly necessary since this will automatically
        happen when the Session is garbage collected...but it makes
        Python's ResourceWarning logging for unclosed sockets cleaner.
        """
        self._trigger_session_initialization()

    def _trigger_session_initialization(self) -> None:
        """
        Effectively resets the HTTP session by removing the reference to it.

        During the next request, a new session will be created.
        """
        if self._http_session is not None:
            self._http_session.close()
        self._http_session = None

    @staticmethod
    def _handle_error_responses(
        data: Mapping[str, Any],
        params: Mapping[str, Any],
        response: Response,
    ) -> None:
        """Raise proper exception if qBittorrent returns Error HTTP Status."""
        if response.status_code < 400:
            # short circuit for non-error statuses
            return

        request = response.request

        if response.status_code == 400:
            # Returned for malformed requests such as missing or invalid parameters.
            # If an error_message isn't returned, qbt didn't get all required params.
            # APIErrorType::BadParams
            # name of the error (i.e. Bad Request) started being returned in v4.3.0
            if response.text in ("", "Bad Request"):
                raise MissingRequiredParameters400Error(
                    request=request, response=response
                )
            raise InvalidRequest400Error(
                response.text, request=request, response=response
            )

        if response.status_code == 401:
            # Primarily reserved for XSS and host header issues.
            raise Unauthorized401Error(
                response.text, request=request, response=response
            )

        if response.status_code == 403:
            # Not logged in or calling an API method that isn't public
            # APIErrorType::AccessDenied
            raise Forbidden403Error(response.text, request=request, response=response)

        if response.status_code == 404:
            # API method doesn't exist or more likely, torrent not found
            # APIErrorType::NotFound
            error_message = response.text
            if error_message in ("", "Not Found"):
                hash_source = data or params or {}
                error_hash = hash_source.get("hashes", hash_source.get("hash", ""))
                if error_hash:
                    error_message = f"Torrent hash(es): {error_hash}"
            raise NotFound404Error(error_message, request=request, response=response)

        if response.status_code == 405:
            # HTTP method not allowed for the API endpoint.
            # This should only be raised if qbt changes the requirement for endpoint...
            raise MethodNotAllowed405Error(
                response.text, request=request, response=response
            )

        if response.status_code == 409:
            # APIErrorType::Conflict
            raise Conflict409Error(response.text, request=request, response=response)

        if response.status_code == 415:
            # APIErrorType::BadData
            raise UnsupportedMediaType415Error(
                response.text, request=request, response=response
            )

        if response.status_code >= 500:
            http500_error = InternalServerError500Error(
                response.text, request=request, response=response
            )
            http500_error.http_status_code = response.status_code
            raise http500_error

        # Unaccounted for API errors
        http_error = HTTPError(response.text, request=request, response=response)
        http_error.http_status_code = response.status_code
        raise http_error

    def _verbose_logging(
        self,
        url: str,
        data: Mapping[str, Any],
        params: Mapping[str, Any],
        requests_kwargs: Mapping[str, Any],
        response: Response,
    ) -> None:
        """Log verbose information about request; can be useful during development."""
        if self._VERBOSE_RESPONSE_LOGGING:
            resp_logger = logger.debug
            max_text_length_to_log = 254
            if response.status_code != 200:
                # log as much as possible in an error condition
                max_text_length_to_log = 10000

            resp_logger("Request URL: (%s) %s", response.request.method, response.url)
            resp_logger("Request Headers: %s", response.request.headers)
            if "auth/login" not in url:
                resp_logger("Request HTTP Data: %s", {"data": data, "params": params})
            resp_logger("Requests Config: %s", requests_kwargs)
            if isinstance(response.request.body, str) and "auth/login" not in url:
                body_len = (
                    max_text_length_to_log
                    if len(response.request.body) > max_text_length_to_log
                    else len(response.request.body)
                )
                resp_logger(
                    "Request body: %s%s",
                    response.request.body[:body_len],
                    "...<truncated>" if body_len >= 200 else "",
                )

            resp_logger(
                "Response status: %s (%s)",
                response.status_code,
                response.reason,
            )
            if response.text:
                text_len = (
                    max_text_length_to_log
                    if len(response.text) > max_text_length_to_log
                    else len(response.text)
                )
                resp_logger(
                    "Response text: %s%s",
                    response.text[:text_len],
                    "...<truncated>" if text_len >= 80 else "",
                )
        if self._PRINT_STACK_FOR_EACH_REQUEST:
            from traceback import print_stack

            print_stack()
