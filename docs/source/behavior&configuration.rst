Behavior & Configuration
================================

Untrusted WebUI Certificate
***************************
* qBittorrent allows you to configure HTTPS with an untrusted certificate; this commonly includes self-signed certificates.
* When using such a certificate, instantiate Client with ``VERIFY_WEBUI_CERTIFICATE=False`` or set environment variable ``PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE`` to a non-null value.
* Failure to do this for will cause connections to qBittorrent to fail.
* As a word of caution, doing this actually does turn off certificate verification. Therefore, for instance, potential man-in-the-middle attacks will not be detected and reported (since the error is suppressed). However, the connection will remain encrypted.

Host, Username and Password
***************************
* These can be provided when instantiating ``Client`` or calling ``qbt_client.auth_log_in(username='...', password='...')``.
* Alternatively, set environment variables ``PYTHON_QBITTORRENTAPI_HOST``, ``PYTHON_QBITTORRENTAPI_USERNAME`` and ``PYTHON_QBITTORRENTAPI_PASSWORD``.

Requests Configuration
**********************
* The `Requests <https://docs.python-requests.org/en/latest/>`_ package is used to issue HTTP requests to qBittorrent to facilitate this API.
* Much of ``Requests`` configuration for making HTTP calls can be controlled with parameters passed along with the request payload.
* For instance, HTTP Basic Authorization credentials can be provided via ``auth``, timeouts via ``timeout``, or Cookies via ``cookies``.
* These parameters are exposed here in two ways; the examples below tell ``Requests`` to use a connect timeout of 3.1 seconds and a read timeout of 30 seconds.
* When you instantiate ``Client``, you can specify the parameters to use in all HTTP requests to qBittorrent:
    * ``qbt_client = Client(..., requests_args={'timeout': (3.1, 30)}``
* Alternatively, parameters can be specified for individual requests:
    * ``qbt_client.torrents_info(..., requests_args={'timeout': (3.1, 30))``

Additional HTTP Headers
***********************
* For consistency, HTTP Headers can be specified using the method above; for backwards compatability, the methods below are supported as well.
* Either way, these additional headers will be incorporated (using clobbering) into the rest of the headers to be sent.
* To send a custom HTTP header in all requests made from an instantiated client, declare them during instantiation:
    * ``qbt_client = Client(..., EXTRA_HEADERS={'X-My-Fav-Header': 'header value')``
* Alternatively, you can send custom headers in individual requests:
    * ``qbt_client.torrents.add(..., headers={'X-My-Fav-Header': 'header value')``

Unimplemented API Endpoints
***************************
* Since the qBittorrent Web API has evolved over time, some endpoints may not be available from the qBittorrent host.
* By default, if a call is made to endpoint that doesn't exist for the version of the qBittorrent host (e.g., the Search endpoints were introduced in Web API v2.1.1), there's a debug logger output and None is returned.
* To raise ``NotImplementedError`` instead, instantiate Client with ``RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True``.

Disable Logging Debug Output
****************************
* Instantiate Client with `DISABLE_LOGGING_DEBUG_OUTPUT=True` or manually disable logging for the relevant packages:
    * ``logging.getLogger('qbittorrentapi').setLevel(logging.INFO)``
    * ``logging.getLogger('requests').setLevel(logging.INFO)``
    * ``logging.getLogger('urllib3').setLevel(logging.INFO)``
