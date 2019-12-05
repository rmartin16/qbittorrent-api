import requests
import logging
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from qbittorrentapi.exceptions import *

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urlparse import urlparse

logger = logging.getLogger(__name__)


class RequestMixIn:
    def _get(self, _name="", _method="", **kwargs):
        return self._request_wrapper(http_method='get',
                                     relative_path_list=[_name, _method],
                                     **kwargs)

    def _post(self, _name="", _method="", **kwargs):
        return self._request_wrapper(http_method='post',
                                     relative_path_list=[_name, _method],
                                     **kwargs)

    @staticmethod
    def _build_url(url_without_path=urlparse(''), host="", api_path_list=None):
        """
        Create a fully qualifed URL (minus query parameters that Requests will add later).

        Supports detecting whether HTTPS is enabled for WebUI.

        :param url_without_path: if the URL was already built, this is the base URL
        :param host: ueer provided hostname for WebUI
        :param api_path_list: list of strings for API endpoint path (e.g. ['api', 'v2', 'app', 'version'])
        :return: full URL for WebUI API endpoint
        """
        full_api_path = '/'.join([s.strip('/') for s in api_path_list])

        # build full URL if it's the first time we're here
        if url_without_path.netloc == "":
            url_without_path = urlparse(host)

            # URLs such as 'localhost:8080' are interpreted as all path
            #  so, assume the path is the host if no host found
            if url_without_path.netloc == "":
                # noinspection PyProtectedMember
                url_without_path = url_without_path._replace(netloc=url_without_path.path, path='')

            # detect supported scheme for URL
            logger.debug("Detecting scheme for URL...")
            try:
                # noinspection PyProtectedMember
                tmp_url = url_without_path._replace(scheme='http')
                r = requests.head(tmp_url.geturl(), allow_redirects=True)
                # if WebUI supports sending a redirect from HTTP to HTTPS eventually, using the scheme
                # the ultimate URL Requests found will upgrade the connection to HTTPS automatically.
                #  For instance:
                #   >>> requests.head("http://grc.com", allow_redirects=True).url
                scheme = urlparse(r.url).scheme
            except requests.exceptions.RequestException:
                # catch (practically) all Requests exceptions...any of them almost certainly means
                #  any connection attempt will fail due to a more systemic issue handled elsewhere
                scheme = 'https'

            # use detected scheme
            logger.debug("Using %s scheme" % scheme.upper())
            # noinspection PyProtectedMember
            url_without_path = url_without_path._replace(scheme=scheme)

            logger.debug("Base URL: %s" % url_without_path.geturl())

        # add the full API path to complete the URL
        # noinspection PyProtectedMember
        url = url_without_path._replace(path=full_api_path)

        return url

    def _request_wrapper(self, http_method, relative_path_list, **kwargs):
        """Wrapper to manage requests retries."""

        # This should retry at least twice to account from the WebUI API switching from HTTP to HTTPS.
        # During the second attempt, the URL is rebuilt using HTTP or HTTPS as appropriate.
        max_retries = 2
        for loop_count in range(1, (max_retries + 1)):
            try:
                return self._request(http_method, relative_path_list, **kwargs)
            except HTTPError as e:
                # retry request for HTTP 500 statuses, raise immediately for everything else (e.g. 4XX statuses)
                if not isinstance(e, HTTP5XXError) or loop_count >= max_retries:
                    raise
            except Exception as e:
                if loop_count >= max_retries:
                    error_prologue = "Failed to connect to qBittorrent. "
                    error_messages = {
                        requests.exceptions.SSLError: "This is due to using an untrusted certificate (likely self-signed) " \
                                                      "for HTTPS qBittorrent WebUI. To suppress this error (and skip certificate " \
                                                      "verification consequently exposing the HTTPS connection to man-in-the-middle " \
                                                      "attacks), set VERIFY_WEBUI_CERTIFICATE=False when instantiating Client or set " \
                                                      "environment variable PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE " \
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

            logger.debug("Connection error. Retrying.")
            self._initialize_context()

    def _request(self, http_method, relative_path_list, **kwargs):

        api_path_list = [self._URL_API_PATH, self._URL_API_VERSION]
        api_path_list.extend(relative_path_list)

        url = self._build_url(url_without_path=self._URL_WITHOUT_PATH,
                              host=self.host,
                              api_path_list=api_path_list)

        # preserve URL without the path so we don't have to rebuild it next time
        # noinspection PyProtectedMember
        self._URL_WITHOUT_PATH = url._replace(path="")

        # mechanism to send params to Requests
        requests_params = kwargs.pop('requests_params', dict())

        # support for custom params to API
        data = kwargs.pop('data', dict())
        params = kwargs.pop('params', dict())
        files = kwargs.pop('files', dict())
        if http_method == 'get':
            params.update(kwargs)
        if http_method == 'post':
            data.update(kwargs)

        # set up headers
        headers = kwargs.pop('headers', dict())
        headers['Referer'] = self._URL_WITHOUT_PATH.geturl()
        headers['Origin'] = self._URL_WITHOUT_PATH.geturl()
        # headers['X-Requested-With'] = "XMLHttpRequest"

        # include the SID auth cookie unless we're trying to log in and get a SID
        cookies = {'SID': self._SID if "auth/login" not in url.path else ''}

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
