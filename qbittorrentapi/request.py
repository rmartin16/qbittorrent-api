from copy import deepcopy
from logging import NullHandler
from logging import getLogger
from os import environ
from time import sleep

try:  # python 3
    from collections.abc import Iterable
    from collections.abc import Mapping
    from urllib.parse import urljoin
    from urllib.parse import urlparse
except ImportError:  # python 2
    from collections import Iterable
    from collections import Mapping
    from urlparse import urljoin
    from urlparse import urlparse

from requests import exceptions as requests_exceptions
from requests import Session
from requests.adapters import HTTPAdapter
from six import string_types as six_string_types
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry

from qbittorrentapi.definitions import APINames
from qbittorrentapi.exceptions import APIConnectionError
from qbittorrentapi.exceptions import HTTPError
from qbittorrentapi.exceptions import HTTP5XXError
from qbittorrentapi.exceptions import MissingRequiredParameters400Error
from qbittorrentapi.exceptions import InvalidRequest400Error
from qbittorrentapi.exceptions import Unauthorized401Error
from qbittorrentapi.exceptions import Forbidden403Error
from qbittorrentapi.exceptions import NotFound404Error
from qbittorrentapi.exceptions import Conflict409Error
from qbittorrentapi.exceptions import UnsupportedMediaType415Error
from qbittorrentapi.exceptions import InternalServerError500Error

logger = getLogger(__name__)
getLogger("qbittorrentapi").addHandler(NullHandler())


class Request(object):
    """
    Facilitates HTTP requests to qBittorrent's Web API.
    """

    def __init__(self, host="", port=None, username=None, password=None, **kwargs):
        self.host = host
        self.port = port
        self.username = username or ""
        self._password = password or ""

        self._initialize_context()
        self._initialize_lesser(**kwargs)

        # turn off console-printed warnings about SSL certificate issues.
        # these errors are only shown once the user has explicitly allowed
        # untrusted certs via VERIFY_WEBUI_CERTIFICATE...so printing them
        # in a console isn't particularly useful.
        if not self._VERIFY_WEBUI_CERTIFICATE:
            disable_warnings(InsecureRequestWarning)

    def _initialize_context(self):
        """
        Initialize and/or reset communications context with qBittorrent.
        This is necessary on startup or when the auth cookie needs to be replaced...perhaps
        because it expired, qBittorrent was restarted, significant settings changes, etc.
        """
        logger.debug("Re-initializing context...")
        # base path for all API endpoints
        self._API_BASE_PATH = "api/v2"

        # reset URL so the full URL is derived again
        # (primarily allows for switching scheme for WebUI: HTTP <-> HTTPS)
        self._API_BASE_URL = None

        # reset Requests session so it is rebuilt with new auth cookie and all
        self._trigger_session_initialization()

        # reinitialize interaction layers
        self._application = None
        self._authorization = None
        self._transfer = None
        self._torrents = None
        self._torrent_categories = None
        self._torrent_tags = None
        self._log = None
        self._sync = None
        self._rss = None
        self._search = None

    def _initialize_lesser(
        self,
        EXTRA_HEADERS=None,
        REQUESTS_ARGS=None,
        VERIFY_WEBUI_CERTIFICATE=True,
        FORCE_SCHEME_FROM_HOST=False,
        RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False,
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False,
        RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
        VERBOSE_RESPONSE_LOGGING=False,
        PRINT_STACK_FOR_EACH_REQUEST=False,
        SIMPLE_RESPONSES=False,
        DISABLE_LOGGING_DEBUG_OUTPUT=False,
        MOCK_WEB_API_VERSION=None,
    ):
        """Initialize lessor used configuration"""

        # Configuration parameters
        self._EXTRA_HEADERS = EXTRA_HEADERS or {}
        self._REQUESTS_ARGS = REQUESTS_ARGS or {}
        self._VERIFY_WEBUI_CERTIFICATE = bool(VERIFY_WEBUI_CERTIFICATE)
        self._VERBOSE_RESPONSE_LOGGING = bool(VERBOSE_RESPONSE_LOGGING)
        self._PRINT_STACK_FOR_EACH_REQUEST = bool(PRINT_STACK_FOR_EACH_REQUEST)
        self._SIMPLE_RESPONSES = bool(SIMPLE_RESPONSES)
        self._FORCE_SCHEME_FROM_HOST = bool(FORCE_SCHEME_FROM_HOST)
        self._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS = bool(
            RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS
            or RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS
        )
        self._RAISE_UNSUPPORTEDVERSIONERROR = bool(
            RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS
        )
        if bool(DISABLE_LOGGING_DEBUG_OUTPUT):
            for logger_ in ("qbittorrentapi", "requests", "urllib3"):
                if getLogger(logger_).level < 20:
                    getLogger(logger_).setLevel("INFO")

        # Environment variables have lowest priority
        if self.host == "" and environ.get("PYTHON_QBITTORRENTAPI_HOST") is not None:
            logger.debug(
                "Using PYTHON_QBITTORRENTAPI_HOST env variable for qBittorrent hostname"
            )
            self.host = environ["PYTHON_QBITTORRENTAPI_HOST"]
        if (
            self.username == ""
            and environ.get("PYTHON_QBITTORRENTAPI_USERNAME") is not None
        ):
            logger.debug(
                "Using PYTHON_QBITTORRENTAPI_USERNAME env variable for username"
            )
            self.username = environ["PYTHON_QBITTORRENTAPI_USERNAME"]
        if (
            self._password == ""
            and environ.get("PYTHON_QBITTORRENTAPI_PASSWORD") is not None
        ):
            logger.debug(
                "Using PYTHON_QBITTORRENTAPI_PASSWORD env variable for password"
            )
            self._password = environ["PYTHON_QBITTORRENTAPI_PASSWORD"]
        if (
            self._VERIFY_WEBUI_CERTIFICATE is True
            and environ.get("PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE")
            is not None
        ):
            self._VERIFY_WEBUI_CERTIFICATE = False

        # Mocking variables until better unit testing exists
        self._MOCK_WEB_API_VERSION = MOCK_WEB_API_VERSION

    @classmethod
    def _list2string(cls, input_list=None, delimiter="|"):
        """
        Convert entries in a list to a concatenated string

        :param input_list: list to convert
        :param delimiter: delimiter for concatenation
        :return: if input is a list, concatenated string...else whatever the input was
        """
        is_string = isinstance(input_list, six_string_types)
        is_iterable = isinstance(input_list, Iterable)
        if is_iterable and not is_string:
            return delimiter.join(map(str, input_list))
        return input_list

    def _get(self, _name=APINames.EMPTY, _method="", **kwargs):
        return self._request_manager(
            http_method="get", api_namespace=_name, api_method=_method, **kwargs
        )

    def _post(self, _name=APINames.EMPTY, _method="", **kwargs):
        return self._request_manager(
            http_method="post", api_namespace=_name, api_method=_method, **kwargs
        )

    def _request_manager(self, _retries=1, _retry_backoff_factor=0.3, **kwargs):
        """
        Wrapper to manage request retries and severe exceptions.

        This should retry at least once to account for the Web API switching from HTTP to HTTPS.
        During the second attempt, the URL is rebuilt using HTTP or HTTPS as appropriate.
        """

        def build_error_msg(exc):
            """Create error message for exception to be raised to user."""
            error_prologue = "Failed to connect to qBittorrent. "
            error_messages = {
                requests_exceptions.SSLError: "This is likely due to using an untrusted certificate "
                "(likely self-signed) for HTTPS qBittorrent WebUI. To suppress this error (and skip "
                "certificate verification consequently exposing the HTTPS connection to man-in-the-middle "
                "attacks), set VERIFY_WEBUI_CERTIFICATE=False when instantiating Client or set "
                "environment variable PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE "
                "to a non-null value. SSL Error: %s" % repr(exc),
                requests_exceptions.HTTPError: "Invalid HTTP Response: %s" % repr(exc),
                requests_exceptions.TooManyRedirects: "Too many redirects: %s"
                % repr(exc),
                requests_exceptions.ConnectionError: "Connection Error: %s" % repr(exc),
                requests_exceptions.Timeout: "Timeout Error: %s" % repr(exc),
                requests_exceptions.RequestException: "Requests Error: %s" % repr(exc),
            }
            err_msg = error_messages.get(type(exc), "Unknown Error: %s" % repr(exc))
            err_msg = error_prologue + err_msg
            logger.debug(err_msg)
            return err_msg

        def retry_backoff(retry_count):
            """
            Back off on attempting each subsequent request retry.
            The first retry is always immediate. if the backoff factor is 0.3,
            then will sleep for 0s then .3s, then .6s, etc. between retries.
            """
            if retry_count > 0:
                backoff_time = _retry_backoff_factor * (2 ** ((retry_count + 1) - 1))
                sleep(backoff_time if backoff_time <= 10 else 10)
            logger.debug("Retry attempt %d", retry_count + 1)

        max_retries = _retries if _retries >= 1 else 1
        for retry in range(0, (max_retries + 1)):
            try:
                return self._request(**kwargs)
            except HTTPError as exc:
                # retry the request for HTTP 500 statuses;
                # raise immediately for other HTTP errors (e.g. 4XX statuses)
                if retry >= max_retries or not isinstance(exc, HTTP5XXError):
                    raise
            except Exception as exc:
                if retry >= max_retries:
                    error_message = build_error_msg(exc=exc)
                    response = getattr(exc, "response", None)
                    raise APIConnectionError(error_message, response=response)

            retry_backoff(retry_count=retry)
            self._initialize_context()

    def _request(self, http_method, api_namespace, api_method, **kwargs):
        """
        Meat and potatoes of sending requests to qBittorrent.

        :param http_method: 'get' or 'post'
        :param api_namespace: the namespace for the API endpoint (e.g. torrents)
        :param api_method: the namespace for the API endpoint (e.g. torrents)
        :param kwargs: see _normalize_requests_params for additional support
        :return: Requests response
        """
        api_args, requests_args = self._normalize_args(http_method, **kwargs)
        url = self._build_url(api_namespace, api_method, requests_args=requests_args)

        http_args = api_args.copy()
        http_args.update(requests_args)
        response = self._session.request(http_method, url, **http_args)

        self._verbose_logging(http_method, url, http_args, response)
        self._handle_error_responses(api_args, response)
        return response

    def _normalize_args(
        self,
        http_method,
        headers=None,
        data=None,
        params=None,
        files=None,
        requests_params=None,
        requests_args=None,
        **kwargs
    ):
        """
        Extract several keyword arguments to send in the request.

        :param headers: additional headers to send with the request
        :param data: key/value pairs to send as body
        :param params: key/value pairs to send as query parameters
        :param files: key/value pairs to include as multipart POST requests
        :param requests_params: original name for requests_args
        :param requests_args: keyword arguments for call to Requests
        :return: dictionary of parameters for Requests call
        """
        kwargs = self._trim_known_kwargs(**kwargs)

        # these are completely user defined and intended to allow users
        # of this client to control the behavior of Requests
        override_requests_args = self._get_requests_args(
            headers=headers,
            requests_params=requests_params,
            requests_args=requests_args,
        )

        # these are expected to be populated by this client as necessary for qBittorrent
        data = data or {}
        params = params or {}
        files = files or {}

        # send Content-Length as 0 for empty POSTs...Requests will not send Content-Length
        # if data is empty but qBittorrent will complain otherwise
        is_data_content = any(filter(lambda x: x is None, data.values()))
        if http_method.lower() == "post" and not is_data_content:
            override_requests_args.setdefault("headers", {})
            override_requests_args["headers"].update({"Content-Length": "0"})

        # any other keyword arguments are sent to qBittorrent as part of the request.
        # These are user-defined since this Client will put everything in data/params/files
        # that needs to be sent to qBittorrent.
        if kwargs:
            if http_method == "get":
                params.update(kwargs)
            if http_method == "post":
                data.update(kwargs)

        # arguments specified during Client construction
        requests_args = deepcopy(self._REQUESTS_ARGS)
        # incorporate arguments specified for this specific API call
        requests_args.update(override_requests_args)
        # qbittorrent api call arguments
        api_args = dict(data=data, params=params, files=files)
        return api_args, requests_args

    @staticmethod
    def _trim_known_kwargs(**kwargs):
        """
        Since any extra keyword arguments from the user are automatically
        included in the request to qBittorrent, this removes any "known"
        arguments that definitely shouldn't be sent to qBittorrent.
        Generally, these are removed in previous processing, but in
        certain circumstances, they can survive in to request.

        :param kwargs: extra keywords arguments to be passed along in request
        :return: sanitized arguments
        """
        kwargs.pop("SIMPLE_RESPONSES", None)
        kwargs.pop("SIMPLE_RESPONSE", None)
        return kwargs

    @staticmethod
    def _get_requests_args(**kwargs):
        """
        Return any user-supplied arguments for Requests.
        Users are expected to specify requests-specific parameters in requests_args.
        Headers have historically been treated specially and are supported as a
        naked argument to the generalized request methods (i.e. _get, _post, _request).
        Going forward, additional parameters for managing the behavior of Requests
        should only be supported the requests_args parameter.
        """
        args = kwargs.get("requests_args") or kwargs.get("requests_params") or {}
        if "headers" in kwargs:
            args.setdefault("headers", {}).update(kwargs["headers"] or {})
        return args

    def _build_url(self, api_namespace, api_method, requests_args):
        """
        Create a fully qualified URL for the API endpoint.

        :param api_namespace: the namespace for the API endpoint (e.g. torrents)
        :param api_method: the specific method for the API endpoint (e.g. info)
        :return: urllib URL object
        """

        def build_base_url(
            client,
            base_url=None,
            host="",
            port=None,
            force_user_scheme=False,
            requests_args=None,
        ):
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

            :param client: this larger qbittorrent client
            :param base_url: if the URL was already built, this is the base URL
            :param host: user provided hostname for WebUI
            :param port: TCP port to attempt HTTP connection on
            :param force_user_scheme: use the scheme in the host instead of detecting the proper scheme
            :param requests_args: additional parameters from user for making HTTP HEAD request
            :return: base URL for Web API endpoint
            """
            if base_url is not None:
                return base_url

            # Parse user host - urlparse requires some sort of schema for parsing to work at all
            if not host.lower().startswith(("http:", "https:", "//")):
                host = "//" + host
            base_url = urlparse(url=host)
            logger.debug("Parsed user URL: %r", base_url)

            # default to HTTP if user didn't specify
            user_scheme = base_url.scheme
            default_scheme = user_scheme or "http"
            alt_scheme = "https" if default_scheme == "http" else "http"

            # add port number if host doesn't contain one
            if port is not None and not base_url.port:
                host = "".join((base_url.netloc, ":", str(port)))
                base_url = base_url._replace(netloc=host)

            # detect whether Web API is configured for HTTP or HTTPS
            if not (user_scheme and force_user_scheme):
                logger.debug("Detecting scheme for URL...")
                prefer_https = False
                for scheme in (default_scheme, alt_scheme):
                    try:
                        base_url = base_url._replace(scheme=scheme)
                        r = client._session.request(
                            "head", base_url.geturl(), **requests_args
                        )
                        scheme_to_use = urlparse(r.url).scheme
                        break
                    except requests_exceptions.SSLError:
                        # an SSLError means that qBittorrent is likely listening on HTTPS
                        # but the TLS connection is not trusted...so, if the attempt to
                        # connect on HTTP also fails, this will tell us to switch back to HTTPS
                        logger.debug(
                            "Encountered SSLError: will prefer HTTPS if HTTP fails"
                        )
                        prefer_https = True
                    except requests_exceptions.RequestException:
                        logger.debug(
                            "Failed connection attempt with %s", scheme.upper()
                        )
                else:
                    scheme_to_use = "https" if prefer_https else "http"

                # use detected scheme
                logger.debug("Using %s scheme", scheme_to_use.upper())
                base_url = base_url._replace(scheme=scheme_to_use)
                if user_scheme and user_scheme != scheme_to_use:
                    logger.warning(
                        "Using '%s' instead of requested '%s' to communicate with qBittorrent",
                        scheme_to_use,
                        user_scheme,
                    )

            # ensure URL always ends with a forward-slash
            base_url = base_url.geturl()
            if not base_url.endswith("/"):
                base_url = base_url + "/"
            logger.debug("Base URL: %s", base_url)

            # force a new session to be created now that the URL is known
            client._trigger_session_initialization()

            return base_url

        def build_url_path(base_url, api_base_path, api_namespace, api_method):
            """
            Determine the full URL path for the API endpoint.

            :param base_url: base URL for API (e.g. http://localhost:8080 or http://example.com/qbt/)
            :param api_base_path: qBittorrent defined API path prefix (i.e. api/v2/)
            :param api_namespace: the namespace for the API endpoint (e.g. torrents)
            :param api_method: the specific method for the API endpoint (e.g. info)
            :return: full urllib URL object for API endpoint
                     (e.g. http://localhost:8080/api/v2/torrents/info or http://example.com/qbt/api/v2/torrents/info)
            """

            def sanitize(piece):
                """Ensure each piece of api path is a string without leading or trailing slashes"""
                return str(piece or "").strip("/")

            if isinstance(api_namespace, APINames):
                api_namespace = api_namespace.value
            api_path = "/".join(
                map(sanitize, (api_base_path, api_namespace, api_method))
            )
            # since base_url is guaranteed to end in a slash and api_path will never
            # start with a slash, this join only ever append to the path in base_url
            url = urljoin(base_url, api_path)
            return url

        self._API_BASE_URL = build_base_url(
            client=self,
            base_url=self._API_BASE_URL,
            host=self.host,
            port=self.port,
            force_user_scheme=self._FORCE_SCHEME_FROM_HOST,
            requests_args=requests_args,
        )
        return build_url_path(
            base_url=self._API_BASE_URL,
            api_base_path=self._API_BASE_PATH,
            api_namespace=api_namespace,
            api_method=api_method,
        )

    @property
    def _session(self):
        """
        Create or return existing HTTP session.

        :return: Requests Session object
        """

        class QbittorrentSession(Session):
            """
            Wrapper to augment Requests Session.
            Requests doesn't allow Session to default certain configuration
            globally. This gets around that by setting defaults for each request.
            """

            def request(self, *args, **kwargs):
                kwargs.setdefault("timeout", 15.1)
                kwargs.setdefault("allow_redirects", True)
                return super(QbittorrentSession, self).request(*args, **kwargs)

        if self._http_session:
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
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=1,
                read=1,
                connect=1,
                status_forcelist={500, 502, 504},
                raise_on_status=False,
            )
        )
        self._http_session.mount("http://", adapter)
        self._http_session.mount("https://", adapter)

        return self._http_session

    def __del__(self):
        """
        Close HTTP Session before destruction.
        This isn't strictly necessary since this will automatically
        happen when the Session is garbage collected...but it makes
        Python's ResourceWarning logging for unclosed sockets cleaner.
        """
        self._trigger_session_initialization()

    def _trigger_session_initialization(self):
        """
        Effectively resets the HTTP session by removing the reference to it.
        During the next request, a new session will be created.
        """
        if hasattr(self, "_http_session") and isinstance(self._http_session, Session):
            self._http_session.close()
        self._http_session = None

    @staticmethod
    def _handle_error_responses(args, response):
        """Raise proper exception if qBittorrent returns Error HTTP Status."""
        if response.status_code < 400:
            # short circuit for non-error statuses
            return
        if response.status_code == 400:
            # Returned for malformed requests such as missing or invalid parameters.
            #
            # If an error_message isn't returned, qBittorrent didn't receive all required parameters.
            # APIErrorType::BadParams
            # the name (i.e. Bad Response) of the HTTP error started being returned in v4.3.0
            if response.text in ("", "Bad Request"):
                raise MissingRequiredParameters400Error()
            raise InvalidRequest400Error(response.text)

        if response.status_code == 401:
            # Primarily reserved for XSS and host header issues. Is also
            raise Unauthorized401Error(response.text)

        if response.status_code == 403:
            # Not logged in or calling an API method that isn't public
            # APIErrorType::AccessDenied
            raise Forbidden403Error(response.text)

        if response.status_code == 404:
            # API method doesn't exist or more likely, torrent not found
            # APIErrorType::NotFound
            error_message = response.text
            if error_message in ("", "Not Found"):
                error_torrent_hash = ""
                if args["data"]:
                    error_torrent_hash = args["data"].get("hash", error_torrent_hash)
                    error_torrent_hash = args["data"].get("hashes", error_torrent_hash)
                if args and error_torrent_hash == "":
                    error_torrent_hash = args["params"].get("hash", error_torrent_hash)
                    error_torrent_hash = args["params"].get(
                        "hashes", error_torrent_hash
                    )
                if error_torrent_hash:
                    error_message = "Torrent hash(es): %s" % error_torrent_hash
            raise NotFound404Error(error_message)

        if response.status_code == 409:
            # APIErrorType::Conflict
            raise Conflict409Error(response.text)

        if response.status_code == 415:
            # APIErrorType::BadData
            raise UnsupportedMediaType415Error(response.text)

        if response.status_code >= 500:
            raise InternalServerError500Error(response.text)

        if response.status_code >= 400:
            # Unaccounted for errors from API
            raise HTTPError(response.text)

    def _verbose_logging(self, http_method, url, http_args, response):
        """Log verbose information about request. Can be useful during development."""
        if self._VERBOSE_RESPONSE_LOGGING:
            resp_logger = logger.debug
            max_text_length_to_log = 254
            if response.status_code != 200:
                # log as much as possible in an error condition
                max_text_length_to_log = 10000

            resp_logger("Request URL: (%s) %s", http_method.upper(), response.url)
            resp_logger("Request HTTP Args: %s", http_args)
            resp_logger("Request Headers: %s", response.request.headers)
            if (
                str(response.request.body) not in ("None", "")
                and "auth/login" not in url
            ):
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
                "Response status: %s (%s)", response.status_code, response.reason
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
