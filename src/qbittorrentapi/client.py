from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from qbittorrentapi.log import LogAPIMixIn
from qbittorrentapi.rss import RSSAPIMixIn
from qbittorrentapi.search import SearchAPIMixIn
from qbittorrentapi.sync import SyncAPIMixIn
from qbittorrentapi.torrentcreator import TorrentCreatorAPIMixIn
from qbittorrentapi.torrents import TorrentsAPIMixIn
from qbittorrentapi.transfer import TransferAPIMixIn

# NOTES
# Implementation
#     Required API parameters
#         - To avoid runtime errors, required API parameters are not explicitly
#           enforced in the code. Instead, I found if qBittorrent returns HTTP400
#           without am error message, at least one required parameter is missing.
#           This raises a MissingRequiredParameters400 error.
#         - Alternatively, if a parameter is malformatted, HTTP400 is returned
#           with an error message.
#           This raises a InvalidRequest400 error.
#
#     Unauthorized HTTP 401
#         - This is only raised if XSS is detected or host header validation fails.
#
# API Peculiarities
#     app/setPreferences
#         - This was endlessly frustrating since it requires data in the
#           form of {'json': dumps({'dht': True})}...this way, Requests sends the
#           JSON dump as a key/value pair for "json" via x-www-form-urlencoded.
#         - Sending an empty string for 'banned_ips' drops the useless message
#           below in to the log file (same for WebUI):
#             ' is not a valid IP address and was rejected while applying the list of banned addresses.'  # noqa: E501
#             - [Resolved] https://github.com/qbittorrent/qBittorrent/issues/10745
#
#     torrents/downloadLimit and uploadLimit
#         - Hashes handling is non-standard. 404 is not returned for bad hashes and 'all' doesn't work.  # noqa: E501
#         - https://github.com/qbittorrent/qBittorrent/blob/6de02b0f2a79eeb4d7fb624c39a9f65ffe181d68/src/webui/api/torrentscontroller.cpp#L754  # noqa: E501
#         - https://github.com/qbittorrent/qBittorrent/issues/10744
#
#     torrents/info
#         - when using a GET request, the params (such as category) seemingly can't
#           contain spaces; however, POST does work with spaces.
#         - [Resolved] https://github.com/qbittorrent/qBittorrent/issues/10606


class Client(
    LogAPIMixIn,
    SyncAPIMixIn,
    TransferAPIMixIn,
    TorrentsAPIMixIn,
    TorrentCreatorAPIMixIn,
    RSSAPIMixIn,
    SearchAPIMixIn,
):
    """
    Initialize API for qBittorrent client.

    Host must be specified. Username and password can be specified at login.
    A call to :meth:`~qbittorrentapi.auth.AuthAPIMixIn.auth_log_in` is not explicitly
    required if username and password are provided during Client construction.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> torrents = client.torrents_info()

    :param host: hostname for qBittorrent Web API, ``[http[s]://]hostname[:port][/path]``
    :param port: port number for qBittorrent Web API (ignored if host contains a port)
    :param username: username for qBittorrent Web API
    :param password: password for qBittorrent Web API
    :param SIMPLE_RESPONSES: By default, complex objects are returned from some
        endpoints. These objects will allow for accessing responses' items as
        attributes and include methods for contextually relevant actions. This
        comes at the cost of performance. Generally, this cost isn't large;
        however, some endpoints, such as ``torrents_files()`` method, may need
        to convert a large payload. Set this to True to return the simple JSON
        back. Alternatively, set this to True only for an individual method call.
        For instance, when requesting the files for a torrent:
        ``client.torrents_files(torrent_hash='...', SIMPLE_RESPONSES=True)``
    :param VERIFY_WEBUI_CERTIFICATE: Set to ``False`` to skip verify certificate for
        HTTPS connections; for instance, if the connection is using a self-signed
        certificate. Not setting this to ``False`` for self-signed certs will cause a
        :class:`~qbittorrentapi.exceptions.APIConnectionError` exception to be raised.
    :param EXTRA_HEADERS: Dictionary of HTTP Headers to include in all requests
        made to qBittorrent.
    :param REQUESTS_ARGS: Dictionary of configuration for each HTTP request made by
        :any:`requests.request`.
    :param HTTPADAPTER_ARGS: Dictionary of configuration for
        :class:`~requests.adapters.HTTPAdapter`.
    :param FORCE_SCHEME_FROM_HOST: If a scheme (i.e. ``http`` or ``https``) is
        specified in host, it will be used regardless of whether qBittorrent is
        configured for HTTP or HTTPS communication. Normally, this client will
        attempt to determine which scheme qBittorrent is actually listening on...
        but this can cause problems in rare cases. Defaults ``False``.
    :param RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: Some endpoints
        may not be implemented in older versions of qBittorrent. Setting this to ``True``
        will raise a :class:`NotImplementedError` instead of just returning ``None``.
    :param RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS: Raise
        :class:`~qbittorrentapi.exceptions.UnsupportedQbittorrentVersion` if the
        connected version of qBittorrent is not fully supported by this client.
        Defaults ``False``.
    :param DISABLE_LOGGING_DEBUG_OUTPUT: Turn off debug output from logging for
        this package as well as ``requests`` & ``urllib3``.
    """  # noqa: E501

    def __init__(
        self,
        host: str = "",
        port: str | int | None = None,
        username: str | None = None,
        password: str | None = None,
        *,
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
    ):
        super().__init__(
            host=host,
            port=port,
            username=username,
            password=password,
            EXTRA_HEADERS=EXTRA_HEADERS,
            REQUESTS_ARGS=REQUESTS_ARGS,
            HTTPADAPTER_ARGS=HTTPADAPTER_ARGS,
            VERIFY_WEBUI_CERTIFICATE=VERIFY_WEBUI_CERTIFICATE,
            FORCE_SCHEME_FROM_HOST=FORCE_SCHEME_FROM_HOST,
            RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS,  # noqa: E501
            RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS,
            VERBOSE_RESPONSE_LOGGING=VERBOSE_RESPONSE_LOGGING,
            SIMPLE_RESPONSES=SIMPLE_RESPONSES,
            DISABLE_LOGGING_DEBUG_OUTPUT=DISABLE_LOGGING_DEBUG_OUTPUT,
        )
