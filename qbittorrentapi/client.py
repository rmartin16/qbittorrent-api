import logging
from os import environ

from qbittorrentapi.auth import AuthMixIn
from qbittorrentapi.app import AppMixIn
from qbittorrentapi.log import LogMixIn
from qbittorrentapi.sync import SyncMixIn
from qbittorrentapi.transfer import TransferMixIn
from qbittorrentapi.torrents import TorrentsMixIn
from qbittorrentapi.rss import RSSMixIn
from qbittorrentapi.search import SearchMixIn
from qbittorrentapi.interactions import Application
from qbittorrentapi.interactions import Transfer
from qbittorrentapi.interactions import Torrents
from qbittorrentapi.interactions import TorrentCategories
from qbittorrentapi.interactions import TorrentTags
from qbittorrentapi.interactions import Log
from qbittorrentapi.interactions import Sync
from qbittorrentapi.interactions import RSS
from qbittorrentapi.interactions import Search


logger = logging.getLogger(__name__)

'''
NOTES
Implementation
    Required API parameters
        - To avoid runtime errors, required API parameters are not explicitly
          enforced in the code. Instead, I found if qBittorent returns HTTP400
          without am error message, at least one required parameter is missing.
          This raises a MissingRequiredParameters400 error.
        - Alternatively, if a parameter is malformatted, HTTP400 is returned
          with an error message.
          This raises a InvalidRequest400 error.
    
    Unauthorized HTTP 401
        - This is only raised if XSS is detected or host header validation fails.

API Peculiarities
    app/setPreferences
        - This was endlessly frustrating since it requires data in the 
          form of {'json': dumps({'dht': True})}...
        - Sending an empty string for 'banned_ips' drops the useless message
          below in to the log file (same for WebUI):
            ' is not a valid IP address and was rejected while applying the list of banned addresses.'
            - https://github.com/qbittorrent/qBittorrent/issues/10745
    
    torrents/downloadLimit and uploadLimit
        - Hashes handling is non-standard. 404 is not returned for bad hashes
          and 'all' doesn't work.
        - https://github.com/qbittorrent/qBittorrent/blob/6de02b0f2a79eeb4d7fb624c39a9f65ffe181d68/src/webui/api/torrentscontroller.cpp#L754
        - https://github.com/qbittorrent/qBittorrent/issues/10744
    
    torrents/info
        - when using a GET request, the params (such as category) seemingly can't
          contain spaces; however, POST does work with spaces.
        - [Resolved] https://github.com/qbittorrent/qBittorrent/issues/10606
'''


class Client(AuthMixIn, AppMixIn, LogMixIn, SyncMixIn, TransferMixIn, TorrentsMixIn, RSSMixIn, SearchMixIn):
    """
    Initialize API for qBittorrent client.

    Host must be specified. Username and password can be specified at login.
    A call to auth_log_in is not explicitly required if username and password are
    provided during Client construction.

    Optional Configuration Arguments:
        VERIFY_WEBUI_CERTIFICATE: Set to False to skip verify certificate for HTTPS connections;
                                  for instance, if the connection is using a self-signed certificate.
                                  Not setting this to False for self-signed certs will cause a
                                  APIConnectionError exception to be raised.
        RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS: Some Endpoints may not be implemented in older versions of
                                                                  qBittorrent. Setting this to True will raise a UnimplementedError
                                                                  instead of just returning None.
        DISABLE_LOGGING_DEBUG_OUTPUT: Turn off debug output from logging for this package as well as Requests & urllib3.

    :param host: hostname for qBittorrent Web API (eg http://localhost[:8080], https://localhost[:8080], localhost[:8080])
    :param port: port number for qBittorrent Web API (note: only used if host does not contain a port)
    :param username: user name for qBittorrent client
    :param password: password for qBittorrent client
    """
    def __init__(self, host='', port=None, username='', password='', **kwargs):
        self.host = host
        self.port = port
        self.username = username
        self._password = password

        # defaults that should not change
        self._API_URL_BASE_PATH = "api"
        self._API_URL_API_VERSION = "v2"

        # state, context, and caching variables
        #   These variables are deleted if the connection to qBittorrent is reset
        #   or a new login is required. All of these (except the SID cookie) should
        #   be reset in _initialize_connection().
        self._SID = None
        self._cached_web_api_version = None
        self._application = None
        self._transfer = None
        self._torrents = None
        self._torrent_categories = None
        self._torrent_tags = None
        self._log = None
        self._sync = None
        self._rss = None
        self._search = None
        self._API_URL_BASE = None

        # Configuration variables
        self._VERIFY_WEBUI_CERTIFICATE = kwargs.pop('VERIFY_WEBUI_CERTIFICATE', True)
        self._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS = kwargs.pop('RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS', False)
        self._PRINT_STACK_FOR_EACH_REQUEST = kwargs.pop("PRINT_STACK_FOR_EACH_REQUEST", False)

        if kwargs.pop("DISABLE_LOGGING_DEBUG_OUTPUT", False):
            logging.getLogger('qbittorrentapi').setLevel(logging.INFO)
            logging.getLogger('requests').setLevel(logging.INFO)
            logging.getLogger('urllib3').setLevel(logging.INFO)

        # Environment variables have lowest priority
        if self.host == '' and environ.get('PYTHON_QBITTORRENTAPI_HOST') is not None:
            logger.debug("Using PYTHON_QBITTORRENTAPI_HOST env variable for qBittorrent hostname")
            self.host = environ['PYTHON_QBITTORRENTAPI_HOST']
        if self.username == '' and environ.get('PYTHON_QBITTORRENTAPI_USERNAME') is not None:
            logger.debug("Using PYTHON_QBITTORRENTAPI_USERNAME env variable for username")
            self.username = environ['PYTHON_QBITTORRENTAPI_USERNAME']

        if self._password == '' and environ.get('PYTHON_QBITTORRENTAPI_PASSWORD') is not None:
            logger.debug("Using PYTHON_QBITTORRENTAPI_PASSWORD env variable for password")
            self._password = environ['PYTHON_QBITTORRENTAPI_PASSWORD']

        if self._VERIFY_WEBUI_CERTIFICATE is True and environ.get('PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE') is not None:
            self._VERIFY_WEBUI_CERTIFICATE = False

        # Mocking variables until better unit testing exists
        self._MOCK_WEB_API_VERSION = kwargs.pop('MOCK_WEB_API_VERSION', None)

        # Ensure we got everything we need
        assert self.host
        if self.username != "":
            assert self._password

    ##########################################################################
    # Interaction Layer Properties
    ##########################################################################
    @property
    def app(self):
        return self.application

    @property
    def application(self):
        """
        Allows for transparent interaction with Application endpoints.

        See Application class for usage.
        :return: Application object
        """
        if self._application is None:
            self._application = Application(self)
        return self._application

    @property
    def log(self):
        """
        Allows for transparent interaction with Log endpoints.

        See Log class for usage.
        :return: Log object
        """
        if self._log is None:
            self._log = Log(self)
        return self._log

    @property
    def sync(self):
        if self._sync is None:
            self._sync = Sync(self)
        return self._sync

    @property
    def transfer(self):
        """
       Allows for transparent interaction with Transfer endpoints.

       See Transfer class for usage.
       :return: Transfer object
       """
        if self._transfer is None:
            self._transfer = Transfer(self)
        return self._transfer

    @property
    def torrents(self):
        """
        Allows for transparent interaction with Torrents endpoints.

        See Torrents and Torrent class for usage.
        :return: Torrents object
        """
        if self._torrents is None:
            self._torrents = Torrents(self)
        return self._torrents

    @property
    def torrent_categories(self):
        """
        Allows for transparent interaction with Torrent Categories endpoints.

        See Torrent_Categories class for usage.
        :return: Torrent Categories object
        """
        if self._torrent_categories is None:
            self._torrent_categories = TorrentCategories(self)
        return self._torrent_categories

    @property
    def torrent_tags(self):
        """
        Allows for transparent interaction with Torrent Tags endpoints.

        See Torrent_Tags class for usage.
        :return: Torrent Tags object
        """
        if self._torrent_tags is None:
            self._torrent_tags = TorrentTags(self)
        return self._torrent_tags

    @property
    def rss(self):
        """
        Allows for transparent interaction with RSS endpoints.

        See RSS class for usage.
        :return: RSS object
        """
        if self._rss is None:
            self._rss = RSS(self)
        return self._rss

    @property
    def search(self):
        """
        Allows for transparent interaction with Search endpoints.

        See Search class for usage.
        :return: Search object
        """
        if self._search is None:
            self._search = Search(self)
        return self._search
