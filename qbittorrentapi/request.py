import logging
from time import sleep
import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from qbittorrentapi.exceptions import *

try:  # python 3
    from urllib.parse import urlparse
except ImportError:  # python 2
    from urlparse import urlparse

logger = logging.getLogger(__name__)


class RequestMixIn:
    def _get(self, _name="", _method="", **kwargs):
        return self._request_wrapper(http_method='get', api_name=_name, api_method=_method, **kwargs)

    def _post(self, _name="", _method="", **kwargs):
        return self._request_wrapper(http_method='post', api_name=_name, api_method=_method, **kwargs)

    def _request_wrapper(self, _retries=2, _retry_backoff_factor=.3, **kwargs):
        """Wrapper to manage requests retries."""

        # This should retry at least twice to account for the Web API switching from HTTP to HTTPS.
        # During the second attempt, the URL is rebuilt using HTTP or HTTPS as appropriate.
        max_retries = _retries if _retries > 1 else 2
        for retry in range(0, (max_retries + 1)):
            try:
                return self._request(**kwargs)
            except HTTPError as e:
                # retry the request for HTTP 500 statuses, raise immediately for everything else (e.g. 4XX statuses)
                if not isinstance(e, HTTP5XXError) or retry >= max_retries:
                    raise
            except Exception as e:
                if retry >= max_retries:
                    error_prologue = "Failed to connect to qBittorrent. "
                    error_messages = {
                        requests.exceptions.SSLError:
                            "This is likely due to using an untrusted certificate (likely self-signed) " 
                            "for HTTPS qBittorrent WebUI. To suppress this error (and skip certificate "
                            "verification consequently exposing the HTTPS connection to man-in-the-middle "
                            "attacks), set VERIFY_WEBUI_CERTIFICATE=False when instantiating Client or set "
                            "environment variable PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE "
                            "to a non-null value. SSL Error: %s" % repr(e),
                        requests.exceptions.HTTPError: "Invalid HTTP Response: %s" % repr(e),
                        requests.exceptions.TooManyRedirects: "Too many redirects: %s" % repr(e),
                        requests.exceptions.ConnectionError: "Connection Error: %s" % repr(e),
                        requests.exceptions.Timeout: "Timeout Error: %s" % repr(e),
                        requests.exceptions.RequestException: "Requests Error: %s" % repr(e)
                    }
                    error_message = error_prologue + error_messages.get(type(e), "Unknown Error: %s" % repr(e))
                    logger.debug(error_message)
                    response = e.response if hasattr(e, 'response') else None
                    raise APIConnectionError(error_message, response=response)

            # back off on attempting each subsequent retry. first retry is always immediate.
            # if the backoff factor is 0.1, then sleep() will sleep for [0.0s, 0.2s, 0.4s, 0.8s, ...] between retries.
            try:
                if retry > 0:
                    backoff_time = _retry_backoff_factor * (2 ** ((retry + 1) - 1))
                    if backoff_time < 120:
                        sleep(backoff_time)
            except Exception:
                pass
            finally:
                logger.debug('Retry attempt %d' % (retry+1))
                self._initialize_context()

    def _request(self, http_method, api_name, api_method,
                 data=None, params=None, files=None, headers=None, requests_params=None,
                 **kwargs):

        api_path_list = [self._API_URL_BASE_PATH, self._API_URL_API_VERSION, api_name, api_method]

        url = self._build_url(base_url=self._API_URL_BASE,
                              host=self.host,
                              port=self.port,
                              api_path_list=api_path_list)

        # preserve URL without the path so we don't have to rebuild it next time
        self._API_URL_BASE = url._replace(path='')

        # mechanism to send additional arguments to Requests for individual API calls
        requests_params = requests_params or dict()

        # support for custom params to API
        data = data or dict()
        params = params or dict()
        files = files or dict()
        if http_method == 'get':
            params.update(kwargs)
        if http_method == 'post':
            data.update(kwargs)

        # set up headers
        headers = headers or dict()
        headers['Referer'] = self._API_URL_BASE.geturl()
        headers['Origin'] = self._API_URL_BASE.geturl()

        # include the SID auth cookie unless we're trying to log in and get a SID
        cookies = {'SID': self._SID if 'auth/login' not in url.path else ''}

        # turn off console-printed warnings about SSL certificate issues (e.g. untrusted since it is self-signed)
        if not self._VERIFY_WEBUI_CERTIFICATE:
            disable_warnings(InsecureRequestWarning)

        response = requests.request(method=http_method,
                                    url=url.geturl(),
                                    headers=headers,
                                    cookies=cookies,
                                    verify=self._VERIFY_WEBUI_CERTIFICATE,
                                    data=data,
                                    params=params,
                                    files=files,
                                    **requests_params)

        resp_logger = logger.debug
        max_text_length_to_log = 254
        if response.status_code != 200:
            max_text_length_to_log = 10000  # log as much as possible in a error condition

        resp_logger("Request URL: (%s) %s" % (http_method.upper(), response.url))
        if str(response.request.body) not in ["None", ""] and "auth/login" not in url.path:
            body_len = max_text_length_to_log if len(response.request.body) > max_text_length_to_log else len(response.request.body)
            resp_logger("Request body: %s%s" % (response.request.body[:body_len], "...<truncated>" if body_len >= 80 else ''))

        resp_logger("Response status: %s (%s)" % (response.status_code, response.reason))
        if response.text:
            text_len = max_text_length_to_log if len(response.text) > max_text_length_to_log else len(response.text)
            resp_logger("Response text: %s%s" % (response.text[:text_len], "...<truncated>" if text_len >= 80 else ''))

        if self._PRINT_STACK_FOR_EACH_REQUEST:
            from traceback import print_stack
            print_stack()

        error_message = response.text

        if response.status_code == 400:
            """
            Returned for malformed requests such as missing or invalid parameters.

            If an error_message isn't returned, qBittorrent didn't receive all required parameters.
            APIErrorType::BadParams
            """
            if response.text == "":
                raise MissingRequiredParameters400Error()
            raise InvalidRequest400Error(error_message)

        elif response.status_code == 401:
            """
            Primarily reserved for XSS and host header issues. Is also
            """
            raise Unauthorized401Error(error_message)

        elif response.status_code == 403:
            """
            Not logged in or calling an API method that isn't public
            APIErrorType::AccessDenied
            """
            raise Forbidden403Error(error_message)

        elif response.status_code == 404:
            """
            API method doesn't exist or more likely, torrent not found
            APIErrorType::NotFound
            """
            if error_message == "":
                error_torrent_hash = ""
                if data:
                    error_torrent_hash = data.get('hash', error_torrent_hash)
                    error_torrent_hash = data.get('hashes', error_torrent_hash)
                if params and error_torrent_hash == "":
                    error_torrent_hash = params.get('hash', error_torrent_hash)
                    error_torrent_hash = params.get('hashes', error_torrent_hash)
                if error_torrent_hash:
                    error_message = "Torrent hash(es): %s" % error_torrent_hash
            raise NotFound404Error(error_message)

        elif response.status_code == 409:
            """
            APIErrorType::Conflict
            """
            raise Conflict409Error(error_message)

        elif response.status_code == 415:
            """
            APIErrorType::BadData
            """
            raise UnsupportedMediaType415Error(error_message)

        elif response.status_code >= 500:
            raise InternalServerError500Error(error_message)

        elif response.status_code >= 400:
            """
            Unaccounted for errors from API
            """
            raise HTTPError(error_message)

        return response

    @staticmethod
    def _build_url(base_url=None, host='', port=None, api_path_list=None):
        """
        Create a fully qualified URL (minus query parameters that Requests will add later).

        Supports detecting whether HTTPS is enabled for WebUI.

        :param base_url: if the URL was already built, this is the base URL
        :param host: user provided hostname for WebUI
        :param api_path_list: list of strings for API endpoint path (e.g. ['api', 'v2', 'app', 'version'])
        :return: full URL for WebUI API endpoint
        """
        # build full URL if it's the first time we're here
        if base_url is None:
            if not host.lower().startswith(('http:', 'https:', '//')):
                host = '//' + host
            base_url = urlparse(url=host)
            # force scheme to HTTP even if host was provided with HTTPS scheme
            base_url = base_url._replace(scheme='http')
            # add port number if host doesn't contain one
            if port is not None and not isinstance(base_url.port, int):
                base_url = base_url._replace(netloc='%s:%s' % (base_url.netloc, port))

            # detect whether Web API is configured for HTTP or HTTPS
            logger.debug("Detecting scheme for URL...")
            try:
                r = requests.head(base_url.geturl(), allow_redirects=True)
                # if WebUI eventually supports sending a redirect from HTTP to HTTPS then
                # Requests will automatically provide a URL using HTTPS.
                # For instance, the URL returned below will use the HTTPS scheme.
                #  >>> requests.head("http://grc.com", allow_redirects=True).url
                scheme = urlparse(r.url).scheme
            except requests.exceptions.RequestException:
                # qBittorrent will reject the connection if WebUI is configured for HTTPS.
                # If something else caused this exception, we'll properly handle that
                # later during the actual API request.
                scheme = 'https'

            # use detected scheme
            logger.debug("Using %s scheme" % scheme.upper())
            base_url = base_url._replace(scheme=scheme)

            logger.debug("Base URL: %s" % base_url.geturl())

        # add the full API path to complete the URL
        return base_url._replace(path='/'.join([s.strip('/') for s in api_path_list]))
