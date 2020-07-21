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
* These can be provided when instantiating Client or calling ``qbt_client.auth_log_in(username='...', password='...')``.
* Alternatively, set environment variables ``PYTHON_QBITTORRENTAPI_HOST``, ``PYTHON_QBITTORRENTAPI_USERNAME`` and ``PYTHON_QBITTORRENTAPI_PASSWORD``.

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
