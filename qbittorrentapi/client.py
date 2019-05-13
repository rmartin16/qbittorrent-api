import requests
import logging
from json import loads, dumps
from os import path
from functools import wraps
from pkg_resources import parse_version

from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from qbittorrentapi.objects import (
    ApplicationPreferencesDict,
    BuildInfoDict,
    LogMainList,
    LogPeersList,
    RSSRulesDict,
    RssitemsDict,
    SearchCategoriesList,
    SearchJobDict,
    SearchPluginsList,
    SearchResultsDict,
    SearchStatusesList,
    SyncMainDataDict,
    SyncTorrentPeersDict,
    TorrentFilesList,
    TorrentInfoList,
    TorrentLimitsDict,
    TorrentPieceInfoList,
    TorrentPropertiesDict,
    TorrentCategoriesDict,
    TrackersList,
    TransferInfoDict,
    WebSeedsList,

    Application,
    Transfer,
    Torrents,
    TorrentCategories,
    Log,
    Sync,
    RSS,
    Search
)

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urlparse import urlparse

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
        - This is only raised if XSS is detected or host header validiation fails.

API Peculiarities
    app/setPreferences
        - This was endlessly frustrating since it requires data in the 
          form of {'json': dumps({'dht': True})}...
        - Sending an empty string for 'banned_ips' drops the useless message
          below in to the log file (same for WebUI):
            ' is not a valid IP address and was rejected while applying the list of banned addresses.'
    
    torrents/downloadLimit and uploadLimit
        - Hashes handling is non-standard. 404 is not returned for bad hashes
          and 'all' doesn't work.
        - https://github.com/qbittorrent/qBittorrent/blob/6de02b0f2a79eeb4d7fb624c39a9f65ffe181d68/src/webui/api/torrentscontroller.cpp#L754
    
    torrents/info
        - when using a GET request, the params (such as category) seemingly can't
          contain spaces; however, POST does work with spaces.
'''


##########################################################################
# Exception Classes
##########################################################################
class APIError(Exception):
    pass


class LoginFailed(APIError):
    pass


class APIConnectionError(APIError):
    pass


class HTTPError(APIError):
    pass


class HTTP400Error(HTTPError):
    pass


class HTTP401Error(HTTPError):
    pass


class HTTP403Error(HTTPError):
    pass


class HTTP404Error(HTTPError):
    pass


class HTTP409Error(HTTPError):
    pass


class HTTP415Error(HTTPError):
    pass


class HTTP500Error(HTTPError):
    pass


class MissingRequiredParameters400Error(HTTP400Error):
    pass


class InvalidRequest400Error(HTTP400Error):
    pass


class Unauthorized401Error(HTTP401Error):
    pass


class Forbidden403Error(HTTP403Error):
    pass


class NotFound404Error(HTTP404Error):
    pass


class Conflict409Error(HTTP409Error):
    pass


class UnsupportedMediaType415Error(HTTP415Error):
    pass


class InternalServerError500Error(HTTP500Error):
    pass


##########################################################################
# Decorators
##########################################################################
# noinspection PyPep8Naming
class alias(object):
    """
    Alias class that can be used as a decorator for making methods callable
    through other names (or "aliases").
    Note: This decorator must be used inside an @aliased -decorated class.
    For example, if you want to make the method shout() be also callable as
    yell() and scream(), you can use alias like this:

        @alias('yell', 'scream')
        def shout(message):
            # ....
    """

    def __init__(self, *aliases):
        """Constructor."""
        self.aliases = set(aliases)

    def __call__(self, f):
        """
        Method call wrapper. As this decorator has arguments, this method will
        only be called once as a part of the decoration process, receiving only
        one argument: the decorated function ('f'). As a result of this kind of
        decorator, this method must return the callable that will wrap the
        decorated function.
        """
        f._aliases = self.aliases
        return f


# noinspection PyProtectedMember
def aliased(aliased_class):
    """
    Decorator function that *must* be used in combination with @alias
    decorator. This class will make the magic happen!
    @aliased classes will have their aliased method (via @alias) actually
    aliased.
    This method simply iterates over the member attributes of 'aliased_class'
    seeking for those which have an '_aliases' attribute and then defines new
    members in the class using those aliases as mere pointer functions to the
    original ones.

    Usage:
        @aliased
        class MyClass(object):
            @alias('coolMethod', 'myKinkyMethod')
            def boring_method():
                # ...

        i = MyClass()
        i.coolMethod() # equivalent to i.myKinkyMethod() and i.boring_method()
    """
    original_methods = aliased_class.__dict__.copy()
    for name, method in original_methods.items():
        if hasattr(method, '_aliases'):
            # Add the aliases for 'method', but don't override any
            # previously-defined attribute of 'aliased_class'
            for method_alias in method._aliases - set(original_methods):
                setattr(aliased_class, method_alias, method)
    return aliased_class


def login_required(f):
    """Ensure client is logged in before calling API methods."""
    @wraps(f)
    def wrapper(obj, *args, **kwargs):
        if not obj.is_logged_in:
            logger.debug("Not logged in...attempting login")
            obj.auth_log_in()
        try:
            return f(obj, *args, **kwargs)
        except HTTP403Error:
            logger.debug("Login may have expired...attempting new login")
            obj.auth_log_in()

        return f(obj, *args, **kwargs)

    return wrapper


def response_text(response_class):
    """
    Return the UTF-8 encoding of the API response.

    :param response_class: class to cast the response to
    :return: Text of the response casted to the specified class
    """
    def _inner(f):
        @wraps(f)
        def wrapper(obj, *args, **kwargs):
            result = f(obj, *args, **kwargs)
            if isinstance(result, response_class):
                return result
            try:
                return response_class(result.text)
            except Exception:
                logger.debug("Exception during response parsing.", exc_info=True)
                # return response_class()
                raise APIError("Exception during response parsing")
        return wrapper
    return _inner


def response_json(response_class):
    """
    Return the JSON in the API response. JSON is parsed as instance of response_class.

    :param response_class: class to parse the JSON in to
    :return: JSON as the response class
    """
    def _inner(f):
        @wraps(f)
        def wrapper(obj, *args, **kwargs):
            response = f(obj, *args, **kwargs)
            try:
                if isinstance(response, response_class):
                    return response
                else:
                    try:
                        result = response.json()
                    except AttributeError:
                        # just in case the requests package is old and doesn't contain json()
                        result = loads(response.text)
                    return response_class(result, obj)
            except Exception:
                logger.debug("Exception during response parsing.", exc_info=True)
                # return response_class()
                raise APIError("Exception during response parsing")
        return wrapper
    return _inner


def version_implemented(version_introduced, endpoint, end_point_params=None):
    """
    Prevent hitting an endpoint or sending a parameter if the host doesn't support it.

    :param version_introduced: version endpoint was made available
    :param endpoint: API endpoint (e.g. /torrents/categories)
    :param end_point_params: list of arguments of API call that are version specific
    """
    def _inner(f):
        # noinspection PyProtectedMember
        @wraps(f)
        def wrapper(obj, *args, **kwargs):
            current_version = obj._app_web_api_version_from_version_checker()
            # if the installed version of the API is less than what's required:
            if is_version_less_than(current_version, version_introduced, lteq=False):
                # clear the unsupported end_point_params
                if end_point_params:
                    parameters_list = end_point_params
                    if not isinstance(end_point_params, list):
                        parameters_list = [end_point_params]
                    # each tuple should be ('python param name', 'api param name')
                    for parameter, api_parameter in [t for t in parameters_list if t[0] in kwargs]:
                        error_message = "WARNING: Parameter '%s (%s)' for endpoint '%s' is Not Implemented. " \
                                        "Web API v%s is installed. This endpoint parameter is available starting " \
                                        "in Web API v%s." \
                                        % (api_parameter, parameter, endpoint, current_version, version_introduced)
                        logger.debug(error_message)
                        kwargs[parameter] = None
                # or skip running unsupported API calls
                if not end_point_params:
                    error_message = "ERROR: Endpoint '%s' is Not Implemented. Web API v%s is installed. This endpoint" \
                                    " is available starting in Web API v%s." \
                                    % (endpoint, current_version, version_introduced)
                    logger.debug(error_message)
                    if obj._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS:
                        raise NotImplementedError(error_message)
                    return None
            return f(obj, *args, **kwargs)
        return wrapper
    return _inner


##########################################################################
# API Helpers
##########################################################################
class APINames:
    """
    API names for API endpoints

    e.g 'torrents' in http://localhost:8080/api/v2/torrents/addTrackers
    """

    def __init__(self):
        pass

    Blank = ''
    Authorization = "auth"
    Application = "app"
    Log = "log"
    Sync = "sync"
    Transfer = "transfer"
    Torrents = "torrents"
    RSS = "rss"
    Search = "search"


def list2string(input_list=None, delimiter="|"):
    """
    Converted entries in a list to a concatenated string
    :param input_list: list to convert
    :param delimiter: delimiter for concatenation
    :return: if input is a list, concatenated string...else whatever the input was
    """
    if isinstance(input_list, list):
        return delimiter.join([str(x) for x in input_list])
    return input_list


def suppress_context(exc):
    """
    This is used to mask an exception with another one.

    For instance, below, the devide by zero error is masked by the CustomException.
        try:
            1/0
        except ZeroDivisionError:
            raise suppress_context(CustomException())

    Note: In python 3, the last line would simply be raise CustomException() from None
    :param exc: new Exception that will be raised
    :return: Exception to be raised
    """
    exc.__cause__ = None
    return exc


def is_version_less_than(ver1, ver2, lteq=True):
    """
    Determine if ver1 is equal to or later than ver2.

    :param ver1: version to check
    :param ver2: current version of application
    :param lteq: True for Less Than or Equals; False for just Less Than
    :return: True or False
    """
    if lteq:
        return parse_version(ver1) <= parse_version(ver2)
    return parse_version(ver1) < parse_version(ver2)

##########################################################################
# API Client
##########################################################################
@aliased
class Client(object):
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

    :param host: hostname of qBittorrent client (eg http://localhost:8080)
    :param username: user name for qBittorrent client
    :param password: password for qBittorrent client
    """

    # TODO: consider whether password should hang around in the event it is
    #       necessary to attempt an automatic re-login (e.g. if the SID expires)
    def __init__(self, host='', username='', password='', **kwargs):
        self.host = host
        self.username = username
        self._password = password

        assert self.host
        if self.username != "":
            assert self._password

        # defaults that should not change
        self._URL_API_PATH = "api"
        self._URL_API_VERSION = "v2"

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
        self._log = None
        self._sync = None
        self._rss = None
        self._search = None
        self._URL_WITHOUT_PATH = urlparse(url='')

        # Configuration variables
        self._VERIFY_WEBUI_CERTIFICATE = kwargs.pop('VERIFY_WEBUI_CERTIFICATE', True)
        self._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS = kwargs.pop('RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS', False)
        self._PRINT_STACK_FOR_EACH_REQUEST = kwargs.pop("PRINT_STACK_FOR_EACH_REQUEST", False)

        # Mocking variables until better unit testing exists
        self._MOCK_WEB_API_VERSION = kwargs.pop('MOCK_WEB_API_VERSION', None)

    ##########################################################################
    # Authorization
    ##########################################################################
    @property
    def is_logged_in(self):
        return bool(self._SID)

    def auth_log_in(self, username='', password=''):
        """
        Log in to qBittorrent host.
        
        Exceptions:
            raise LoginFailed if credentials failed to log in
            raise Forbidden403Error if user user is banned

        :param username: user name for qBittorrent client
        :param password: password for qBittorrent client
        :return: None
        """
        if username != "":
            self.username = username
            assert password
            self._password = password

        try:
            self._initialize_context()

            response = self._post(_name=APINames.Authorization,
                                  _method='login',
                                  data={'username': self.username,
                                        'password': self._password})
            self._SID = response.cookies['SID']
            logger.debug("Login successful for user '%s'" % self.username)
            logger.debug("SID: %s" % self._SID)

        except KeyError:
            logger.debug("Login failed for user '%s'" % self.username)
            # noinspection PyTypeChecker
            raise suppress_context(LoginFailed("Login authorization failed for user '%s'" % self.username))

    def _initialize_context(self):
        # cache to avoid perf hit from version checking certain endpoints
        self._cached_web_api_version = None

        # reset URL in case WebUI changed from HTTP to HTTPS
        self._URL_WITHOUT_PATH = urlparse(url='')

        # reinitialize interaction layers
        self._application = None
        self._transfer = None
        self._torrents = None
        self._torrent_categories = None
        self._log = None
        self._sync = None
        self._rss = None
        self._search = None

    @login_required
    def auth_log_out(self, **kwargs):
        """ Log out of qBittorrent client"""
        self._get(_name=APINames.Authorization, _method='logout', **kwargs)

    ##########################################################################
    # Interaction Layer Properties
    ##########################################################################
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

        See Torrents class for usage.
        :return: Torrents object
        """
        if self._torrents is None:
            self._torrents = Torrents(self)
        return self._torrents

    @property
    def torrent_categories(self):
        if self._torrent_categories is None:
            self._torrent_categories = TorrentCategories(self)
        return self._torrent_categories

    @property
    def rss(self):
        if self._rss is None:
            self._rss = RSS(self)
        return self._rss

    @property
    def search(self):
        if self._search is None:
            self._search = Search(self)
        return self._search

    # TODO: consider routing methods through Application to take advantage of caching
    ##########################################################################
    # Application
    ##########################################################################
    @response_text(str)
    @login_required
    def app_version(self, **kwargs):
        """
        Retrieve application version

        :return: string
        """
        return self._get(_name=APINames.Application, _method='version', **kwargs)

    @login_required
    def _app_web_api_version_from_version_checker(self):
        if self._cached_web_api_version:
            return self._cached_web_api_version
        logger.debug("Retrieving API version for version_implemented verifier")
        self._cached_web_api_version = self.app_web_api_version()
        return self._cached_web_api_version

    @alias('app_webapiVersion')
    @response_text(str)
    @login_required
    def app_web_api_version(self, **kwargs):
        """
        Retrieve web API version. (alias: app_webapiVersion)

        :return: string
        """
        if self._MOCK_WEB_API_VERSION:
            return self._MOCK_WEB_API_VERSION
        return self._get(_name=APINames.Application, _method='webapiVersion', **kwargs)

    @version_implemented('2.3.0', 'app/buildInfo')
    @response_json(BuildInfoDict)
    @alias('app_buildInfo')
    @login_required
    def app_build_info(self, **kwargs):
        """
        Retrieve build info. (alias: app_buildInfo)

        :return: Dictionary of build info. Each piece of info is an attribute.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-build-info
        """
        return self._get(_name=APINames.Application, _method='buildInfo', **kwargs)

    @login_required
    def app_shutdown(self, **kwargs):
        """Shutdown qBittorrent"""
        self._get(_name=APINames.Application, _method='shutdown', **kwargs)

    @response_json(ApplicationPreferencesDict)
    @login_required
    def app_preferences(self, **kwargs):
        """
        Retrieve qBittorrent application preferences.

        :return: Dictionary of preferences. Each preference is an attribute.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-application-preferences
        """
        return self._get(_name=APINames.Application, _method='preferences', **kwargs)

    @alias('app_setPreferences')
    @login_required
    def app_set_preferences(self, prefs=None, **kwargs):
        """
        Set one or more preferences in qBittorrent application. (alias: app_setPreferences)

        :param prefs: dictionary of preferences to set
        :return: None
        """
        data = {'json': dumps(prefs)}
        return self._post(_name=APINames.Application, _method='setPreferences', data=data, **kwargs)

    @alias('app_defaultSavePath')
    @response_text(str)
    @login_required
    def app_default_save_path(self, **kwargs):
        """
        Retrieves the default path for where torrents are saved. (alias: app_defaultSavePath)

        :return: string
        """
        return self._get(_name=APINames.Application, _method='defaultSavePath', **kwargs)

    ##########################################################################
    # Log
    ##########################################################################
    @response_json(LogMainList)
    @login_required
    def log_main(self, normal=None, info=None, warning=None, critical=None, last_known_id=None, **kwargs):
        """
        Retrieve the qBittorrent log entries. Iterate over returned object.

        :param normal: False to exclude 'normal' entries
        :param info: False to exclude 'info' entries
        :param warning: False to exclude 'warning' entries
        :param critical: False to exclude 'critical' entries
        :param last_known_id: only entries with an ID greater than this value will be returned
        :return: List of log entries.
        """
        parameters = {"normal": normal,
                      'info': info,
                      'warning': warning,
                      'critical': critical,
                      'last_known_id': last_known_id}
        return self._get(_name=APINames.Log, _method='main', params=parameters, **kwargs)

    @response_json(LogPeersList)
    @login_required
    def log_peers(self, last_known_id=None, **kwargs):
        """
        Retrieve qBittorrent peer log.

        :param last_known_id: only entries with an ID greater than this value will be returned
        :return: list of log entries in a List
        """
        parameters = {'last_known_id': last_known_id}
        return self._get(_name=APINames.Log, _method='peers', params=parameters, **kwargs)

    ##########################################################################
    # Sync
    ##########################################################################
    # TODO: revert to _post or figure out the Bad Request with no data...seems most likely content-length issue
    @response_json(SyncMainDataDict)
    @login_required
    def sync_maindata(self, rid=None, **kwargs):
        """
        Retrieves sync data.

        :param rid: response ID
        :return: dictionary response
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-main-data
        """
        parameters = {'rid': rid}
        return self._get(_name=APINames.Sync, _method='maindata', data=parameters, **kwargs)

    @alias('sync_torrentPeers')
    @response_json(SyncTorrentPeersDict)
    @login_required
    def sync_torrent_peers(self, hash=None, rid=None, **kwargs):
        """
        Retrieves torrent sync data. (alias: sync_torrentPeers)

        Exceptions:
            NotFound404Error

        :param hash: hash for torrent
        :param rid: response ID
        :return: Dictionary of torrent sync data.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-peers-data
        """
        parameters = {'hash': hash,
                      'rid': rid}
        return self._get(_name=APINames.Sync, _method='torrentPeers', params=parameters, **kwargs)

    ##########################################################################
    # Transfer
    ##########################################################################
    @response_json(TransferInfoDict)
    @login_required
    def transfer_info(self, **kwargs):
        """
        Retrieves the global transfer info usually found in qBittorrent status bar.

        :return: dictioanry of status items
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-global-transfer-info
        """
        return self._get(_name=APINames.Transfer, _method='info', **kwargs)

    @alias('transfer_speedLimitsMode')
    @response_text(str)
    @login_required
    def transfer_speed_limits_mode(self, **kwargs):
        """
        Retrieves whether alternative speed limits are enabled. (alias: transfer_speedLimitMode)

        :return: '1' if alternative speed limits are currently enabled, '0' otherwise
        """
        return self._get(_name=APINames.Transfer, _method='speedLimitsMode', **kwargs)

    @alias('transfer_toggleSpeedLimitsMode')
    @login_required
    def transfer_toggle_speed_limits_mode(self, intended_state=None, **kwargs):
        """
        Toggles whether alternative speed limits are enabled. (alias: transfer_toggleSpeedLimitsMode)

        :param intended_state: True to enable alt speed and False to disable.
                               Leaving None will toggle the current state.
        :return: None
        """
        if (self.transfer_speed_limits_mode() == '1') is not intended_state or intended_state is None:
            self._post(_name=APINames.Transfer, _method='toggleSpeedLimitsMode', **kwargs)

    @alias('transfer_downloadLimit')
    @response_text(int)
    @login_required
    def transfer_download_limit(self, **kwargs):
        """
        Retrieves download limit. 0 is unlimited. (alias: transfer_downloadLimit)

        :return: integer
        """
        return self._get(_name=APINames.Transfer, _method='downloadLimit', **kwargs)

    @alias('transfer_uploadLimit')
    @response_text(int)
    @login_required
    def transfer_upload_limit(self, **kwargs):
        """
        Retrieves upload limit. 0 is unlimited. (alias: transfer_uploadLimit)

        :return: integer
        """
        return self._get(_name=APINames.Transfer, _method='uploadLimit', **kwargs)

    @alias('transfer_setDownloadLimit')
    @login_required
    def transfer_set_download_limit(self, limit=None, **kwargs):
        """
        Set the global download limit in bytes/second. (alias: transfer_setDownloadLimit)

        :param limit: download limit in bytes/second (0 or -1 for no limit)
        :return: None
        """
        data = {'limit': limit}
        self._post(_name=APINames.Transfer, _method='setDownloadLimit', data=data, **kwargs)

    @alias('transfer_setUploadLimit')
    @login_required
    def transfer_set_upload_limit(self, limit=None, **kwargs):
        """
        Set the global download limit in bytes/second. (alias: transfer_setUploadLimit)

        :param limit: upload limit in bytes/second (0 or -1 for no limit)
        :return: None
        """
        data = {'limit': limit}
        self._post(_name=APINames.Transfer, _method='setUploadLimit', data=data, **kwargs)

    ##########################################################################
    # Torrent Management
    ##########################################################################
    @response_text(str)
    @login_required
    def torrents_add(self, urls=None, torrent_files=None, save_path=None, cookie=None, category=None,
                     is_skip_checking=None, is_paused=None, is_root_folder=None, rename=None,
                     upload_limit=None, download_limit=None, use_auto_torrent_management=None,
                     is_sequential_download=None, is_first_last_piece_priority=None, **kwargs):
        """
        Add one or more torrents by URLs and/or torrent files.

        Exceptions:
            UnsupportedMediaType415Error if file is not a valid torrent file
            FileNotFoundError if a torrent file doesn't exist
            PermissionError if read permission is denied to torrent file

        :param urls: List of URLs (http://, https://, magnet: and bc://bt/)
        :param torrent_files: list of torrent files
        :param save_path: location to save the torrent data
        :param cookie: cookie to retrieve torrents by URL
        :param category: category to assign to torrent(s)
        :param is_skip_checking: skip hash checking
        :param is_paused: True to start torrent(s) paused
        :param is_root_folder: True or False to create root folder
        :param rename: new name for torrent(s)
        :param upload_limit: upload limit in bytes/second
        :param download_limit: donwnload limit in bytes/second
        :param use_auto_torrent_management: True or False to use automatic torrent management
        :param is_sequential_download: True or False for sequential download
        :param is_first_last_piece_priority: True or False for first and last piece download priority
        :return: "Ok." for success and ""Fails." for failure
        """

        data = {'urls': (None, list2string(urls, '\n')),
                'savepath': (None, save_path),
                'cookie': (None, cookie),
                'category': (None, category),
                'skip_checking': (None, is_skip_checking),
                'paused': (None, is_paused),
                'root_folder': (None, is_root_folder),
                'rename': (None, rename),
                'upLimit': (None, upload_limit),
                'dlLimit': (None, download_limit),
                'useAutoTMM': (None, use_auto_torrent_management),
                'sequentialDownload': (None, is_sequential_download),
                'firstLastPiecePrio': (None, is_first_last_piece_priority)}

        if torrent_files:
            if isinstance(torrent_files, str):
                torrent_files = [torrent_files]
            torrent_files = [(path.basename(torrent_file), open(torrent_file, 'rb')) for torrent_file in
                             [path.abspath(path.realpath(path.expanduser(torrent_file))) for torrent_file in
                              torrent_files]]

        return self._post(_name=APINames.Torrents, _method='add', data=data, files=torrent_files, **kwargs)

    # INDIVIDUAL TORRENT ENDPOINTS
    @response_json(TorrentPropertiesDict)
    @login_required
    def torrents_properties(self, hash=None, **kwargs):
        """
        Retrieve individual torrent's properties.

        Exceptions:
            NotFound404Error

        :param hash: hash for torrent
        :return: Dictionary of torrent properties
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-generic-properties
        """
        data = {'hash': hash}
        return self._post(_name=APINames.Torrents, _method='properties', data=data, **kwargs)

    @response_json(TrackersList)
    @login_required
    def torrents_trackers(self, hash=None, **kwargs):
        """
        Retrieve individual torrent's trackers.

        Exceptions:
            NotFound404Error

        :param hash: hash for torrent
        :return: List of torrent's trackers
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-trackers
        """
        data = {'hash': hash}
        return self._post(_name=APINames.Torrents, _method='trackers', data=data, **kwargs)

    @response_json(WebSeedsList)
    @login_required
    def torrents_webseeds(self, hash=None, **kwargs):
        """
        Retrieve individual torrent's web seeds.

        Exceptions:
            NotFound404Error

        :param hash: hash for torrent
        :return: List of torrent's web seeds
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-web-seeds
        """
        data = {'hash': hash}
        return self._post(_name=APINames.Torrents, _method='webseeds', data=data, **kwargs)

    @response_json(TorrentFilesList)
    @login_required
    def torrents_files(self, hash=None, **kwargs):
        """
        Retrieve individual torrent's files.

        Exceptions:
            NotFound404Error

        :param hash: hash for torrent
        :return: List of torrent's files
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-contents
        """
        data = {'hash': hash}
        return self._post(_name=APINames.Torrents, _method='files', data=data, **kwargs)

    @alias('torrents_pieceStates')
    @response_json(TorrentPieceInfoList)
    @login_required
    def torrents_piece_states(self, hash=None, **kwargs):
        """
        Retrieve individual torrent's pieces' states. (alias: torrents_pieceStates)

        Exceptions:
            NotFound404Error

        :param hash: hash for torrent
        :return: list of torrent's pieces' states
        """
        data = {'hash': hash}
        return self._post(_name=APINames.Torrents, _method='pieceStates', data=data, **kwargs)

    @alias('torrents_pieceHashes')
    @response_json(TorrentPieceInfoList)
    @login_required
    def torrents_piece_hashes(self, hash=None, **kwargs):
        """
        Retrieve individual torrent's pieces' hashes. (alias: torrents_pieceHashes)

        Exceptions:
            NotFound404Error

        :param hash: hash for torrent
        :return: List of torrent's pieces' hashes
        """
        data = {'hash': hash}
        return self._post(_name=APINames.Torrents, _method='pieceHashes', data=data, **kwargs)

    @alias('torrents_addTrackers')
    @login_required
    def torrents_add_trackers(self, hash=None, urls=None, **kwargs):
        """
        Add trackers to a torrent. (alias: torrents_addTrackers)

        Exceptions:
            NotFound404Error

        :param hash: hash for torrent
        :param urls: tracker urls to add to torrent
        :return: None
        """
        data = {'hash': hash,
                'urls': list2string(urls, '\n')}
        self._post(_name=APINames.Torrents, _method='addTrackers', data=data, **kwargs)

    @version_implemented('2.2.0', 'torrents/editTracker')
    @alias('torrents_editTracker')
    @login_required
    def torrents_edit_tracker(self, hash=None, original_url=None, new_url=None, **kwargs):
        """
        Replace a torrent's tracker with a different one. (alias: torrents_editTrackers)

        Exceptions:
            InvalidRequest400
            NotFound404Error
            Conflict409Error

        :param hash: hash for torrent
        :param original_url: URL for existing tracker
        :param new_url: new URL to replace
        :return: None
        """
        data = {'hash': hash,
                'origUrl': original_url,
                'newUrl': new_url}
        self._post(_name=APINames.Torrents, _method='editTracker', data=data, **kwargs)

    @version_implemented('2.2', 'torrents/removeTrackers')
    @alias('torrents_removeTrackers')
    @login_required
    def torrents_remove_trackers(self, hash=None, urls=None, **kwargs):
        """
        Remove trackers from a torrent. (alias: torrents_removeTrackers)

        Exceptions:
            NotFound404Error
            Conflict409Error

        :param hash: hash for torrent
        :param urls: tracker urls to removed from torrent
        :return: None
        """
        data = {'hash': hash,
                'urls': list2string(urls, '|')}
        self._post(_name=APINames.Torrents, _method='removeTrackers', data=data, **kwargs)

    @alias('torrents_filePrio')
    @login_required
    def torrents_file_priority(self, hash=None, file_ids=None, priority=None, **kwargs):
        """
        Set priority for one or more files. (alias: torrents_filePrio)

        Exceptions:
            InvalidRequest400 if priority is invalid or at least one file ID is not an integer
            NotFound404
            Conflict409 if torrent metadata has not finished downloading or at least one file was not found
        :param hash: hash for torrent
        :param file_ids: single file ID or a list. See
        :param priority: priority for file(s)
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#set-file-priority
        :return:
        """
        data = {'hash': hash,
                'id': list2string(file_ids, "|"),
                'priority': priority}
        self._post(_name=APINames.Torrents, _method='filePrio', data=data, **kwargs)

    @login_required
    def torrents_rename(self, hash=None, new_torrent_name=None, **kwargs):
        """
        Rename a torrent.

        Exceptions:
            NotFound404

        :param hash: hash for torrent
        :param new_torrent_name: new name for torrent
        :return: None
        """
        data = {'hash': hash,
                'name': new_torrent_name}
        self._post(_name=APINames.Torrents, _method='rename', data=data, **kwargs)

    # MULTIPLE TORRENT ENDPOINT
    @response_json(TorrentInfoList)
    @version_implemented('2.0.1', 'torrents/info', ('hashes', 'hashes'))
    @login_required
    def torrents_info(self, status_filter=None, category=None, sort=None, reverse=None, limit=None, offset=None, hashes=None, **kwargs):
        """
        Retrieves list of info for torrents.

        Note: hashes is available starting web API version 2.0.1

        :param status_filter: Filter list by all, downloading, completed, paused, active, inactive, resumed
        :param category: Filter list by category
        :param sort: Sort list by any property returned
        :param reverse: Reverse sorting
        :param limit: Limit length of list
        :param offset: Start of list (if <0, offset from end of list)
        :param hashes: Filter list by hash (seperate multiple hashes with a '|')
        :return: List of torrents
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-list
        """
        parameters = {'filter': status_filter,
                      'category': category,
                      'sort': sort,
                      'reverse': reverse,
                      'limit': limit,
                      'offset': offset,
                      'hashes': list2string(hashes, '|')}
        return self._get(_name=APINames.Torrents, _method='info', params=parameters, **kwargs)

    @login_required
    def torrents_resume(self, hashes=None, **kwargs):
        """
        Resume one or more torrents in qBitorrent.

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='resume', data=data, **kwargs)

    @login_required
    def torrents_pause(self, hashes=None, **kwargs):
        """
        Pause one or more torrents in qBitorrent.

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, "|")}
        self._post(_name=APINames.Torrents, _method='pause', data=data, **kwargs)

    @login_required
    def torrents_delete(self, delete_files=None, hashes=None, **kwargs):
        """
        Remove a torrent from qBittorrent and optionally delete its files.

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param delete_files: Truw to delete the torrent's files
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'deleteFiles': delete_files}
        self._post(_name=APINames.Torrents, _method='delete', data=data, **kwargs)

    @login_required
    def torrents_recheck(self, hashes=None, **kwargs):
        """
        Recheck a torrent in qBittorrent.

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='recheck', data=data, **kwargs)

    @version_implemented('2.0.2', 'torrents/reannounce')
    @login_required
    def torrents_reannounce(self, hashes=None, **kwargs):
        """
        Reannounce a torrent.

        Note: torrents/reannounce not available web API version 2.0.2

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='reannounce', data=data, **kwargs)

    @alias('torrents_increasePrio')
    @login_required
    def torrents_increase_priority(self, hashes=None, **kwargs):
        """
        Increase the priority of a torrent. Torrent Queuing must be enabled. (alias: torrents_increasePrio)

        Exceptions:
            Conflict409

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='increasePrio', data=data, **kwargs)

    @alias('torrents_decreasePrio')
    @login_required
    def torrents_decrease_priority(self, hashes=None, **kwargs):
        """
        Decrease the priority of a torrent. Torrent Queuing must be enabled. (alias: torrents_decreasePrio)

        Exceptions:
            Conflict409

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='decreasePrio', data=data, **kwargs)

    @alias('torrents_topPrio')
    @login_required
    def torrents_top_priority(self, hashes=None, **kwargs):
        """
        Set torrent as highest priority. Torrent Queuing must be enabled. (alias: torrents_topPrio)

        Exceptions:
            Conflict409

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='topPrio', data=data, **kwargs)

    @alias('torrents_bottomPrio')
    @login_required
    def torrents_bottom_priority(self, hashes=None, **kwargs):
        """
        Set torrent as highest priority. Torrent Queuing must be enabled. (alias: torrents_bottomPrio)

        Exceptions:
            Conflict409

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='bottomPrio', data=data, **kwargs)

    @alias('torrents_downloadLimit')
    @response_json(TorrentLimitsDict)
    @login_required
    def torrents_download_limit(self, hashes=None, **kwargs):
        """
        Retrieve the download limit for one or more torrents. (alias: torrents_downloadLimit)

        :return: dictioanry {hash: limit} (-1 represents no limit)
        """
        data = {'hashes': list2string(hashes, "|")}
        return self._post(_name=APINames.Torrents, _method='downloadLimit', data=data, **kwargs)

    @alias('torrents_setDownloadLimit')
    @login_required
    def torrents_set_download_limit(self, limit=None, hashes=None, **kwargs):
        """
        Set the download limit for one or more torrents. (alias: torrents_setDownloadLimit)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param limit: bytes/second (-1 sets the limit to infinity)
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'limit': limit}
        self._post(_name=APINames.Torrents, _method='setDownloadLimit', data=data, **kwargs)

    @version_implemented('2.0.1', 'torrents/setShareLimits')
    @alias('torrents_setShareLimits')
    @login_required
    def torrents_set_share_limits(self, ratio_limit=None, seeding_time_limit=None, hashes=None, **kwargs):
        """
        Set share limits for one or more torrents.

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param ratio_limit: max ratio to seed a torrent. (-2 means use the global value and -1 is no limit)
        :param seeding_time_limit: minutes (-2 means use the global value and -1 is no limit_
        :return: None
        """
        data = {'hashes': list2string(hashes, "|"),
                'ratioLimit': ratio_limit,
                'seedingTimeLimit': seeding_time_limit}
        self._post(_name=APINames.Torrents, _method='setShareLimits', data=data, **kwargs)

    @alias('torrents_uploadLimit')
    @response_json(TorrentLimitsDict)
    @login_required
    def torrents_upload_limit(self, hashes=None, **kwargs):
        """
        Retrieve the upload limit for onee or more torrents. (alias: torrents_uploadLimit)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: dictionary of limits
        """
        data = {'hashes': list2string(hashes, '|')}
        return self._post(_name=APINames.Torrents, _method='uploadLimit', data=data, **kwargs)

    @alias('torrents_setUploadLimit')
    @login_required
    def torrents_set_upload_limit(self, limit=None, hashes=None, **kwargs):
        """
        Set the upload limit for one or more torrents. (alias: torrents_setUploadLimit)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param limit: bytes/second (-1 sets the limit to infinity)
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'limit': limit}
        self._post(_name=APINames.Torrents, _method='setUploadLimit', data=data, **kwargs)

    @alias('torrents_setLocation')
    @login_required
    def torrents_set_location(self, location=None, hashes=None, **kwargs):
        """
        Set location for torrents's files. (alias: torrents_setLocation)

        Exceptions:
            Unauthorized403 if the user doesn't have permissions to write to the location
            Conflict409 if the directory cannot be created at the location

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param location: disk location to move torrent's files
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'location': location}
        self._post(_name=APINames.Torrents, _method='setLocation', data=data, **kwargs)

    @alias('torrents_setCategory')
    @login_required
    def torrents_set_category(self, category=None, hashes=None, **kwargs):
        """
        Set a category for one or more torrents. (alias: torrents_setCategory)

        Exceptions:
            Conflict409 for bad category

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param category: category to assign to torrent
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'category': category}
        self._post(_name=APINames.Torrents, _method='setCategory', data=data, **kwargs)

    @alias('torrents_setAutoManagement')
    @login_required
    def torrents_set_auto_management(self, enable=None, hashes=None, **kwargs):
        """
        Enable or disable automatic torrent management for one or more torrents. (alias: torrents_setAutoManagement)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param enable: True or False
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'enable': enable}
        self._post(_name=APINames.Torrents, _method='setAutoManagement', data=data, **kwargs)

    @alias('torrents_toggleSequentialDownload')
    @login_required
    def torrents_toggle_sequential_download(self, hashes=None, **kwargs):
        """
        Toggle sequential download for one or more torrents. (alias: torrents_toggleSequentialDownload)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes)}
        self._post(_name=APINames.Torrents, _method='toggleSequentialDownload', data=data, **kwargs)

    @alias('torrents_toggleFirstLastPiecePrio')
    @login_required
    def torrents_toggle_first_last_piece_priority(self, hashes=None, **kwargs):
        """
        Toggle priority of first/last piece downloading. (alias: torrents_toggleFirstLastPiecePrio)
        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='toggleFirstLastPiecePrio', data=data, **kwargs)

    @alias('torrents_setForceStart')
    @login_required
    def torrents_set_force_start(self, enable=None, hashes=None, **kwargs):
        """
        Force start one or more torrents. (alias: torrents_setForceStart)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param enable: True or False (False makes this equivalent to torrents_resume())
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'value': enable}
        self._post(_name=APINames.Torrents, _method='setForceStart', data=data, **kwargs)

    @alias('torrents_setSuperSeeding')
    @login_required
    def torrents_set_super_seeding(self, enable=None, hashes=None, **kwargs):
        """
        Set one or more torrents as super seeding. (alias: torrents_setSuperSeeding)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param enable: True or False
        :return:
        """
        data = {'hashes': list2string(hashes, '|'),
                'value': enable}
        self._post(_name=APINames.Torrents, _method='setSuperSeeding', data=data, **kwargs)

    # START TORRENT CATEGORIES ENDPOINTS
    @version_implemented('2.1.0', 'torrents/categories')
    @response_json(TorrentCategoriesDict)
    @login_required
    def torrents_categories(self, **kwargs):
        """
        Retrieve all category definitions

        Note: torrents/categories is not available until v2.1.0
        :return: dictionary of categories
        """
        return self._get(_name=APINames.Torrents, _method='categories', **kwargs)

    @alias('torrents_createCategory')
    @version_implemented('2.1.0', 'torrents/createCategory', ('save_path', 'savePath'))
    @login_required
    def torrents_create_category(self, name=None, save_path=None, **kwargs):
        """
        Create a new torrent category. (alias: torrents_createCategory)

        Note: save_path is not available until web API version 2.1.0

        Exceptions:
            Conflict409 if category name is not valid or unable to create

        :param name: name for new category
        :param save_path: location to save torrents for this category
        :return: None
        """
        data = {'category': name,
                'savePath': save_path}
        self._post(_name=APINames.Torrents, _method='createCategory', data=data, **kwargs)

    @version_implemented('2.1.0', 'torrents/editCategory', {'save_path': 'savePath'})
    @alias('torrents_editCategory')
    @login_required
    def torrents_edit_category(self, name=None, save_path=None, **kwargs):
        """
        Edit an existing category. (alias: torrents_editCategory)

        Note: torrents/editCategory not available until web API version 2.1.0

        Exceptions:
            Conflict409

        :param name: category to edit
        :param save_path: new location to save files for this category
        :return: None
        """
        data = {'category': name,
                'savePath': save_path}
        self._post(_name=APINames.Torrents, _method='editCategory', data=data, **kwargs)

    @alias('torrents_removeCategories')
    @login_required
    def torrents_remove_categories(self, categories=None, **kwargs):
        """
        Delete one or more categories. (alias: torrents_removeCategories)

        :param categories: categories to delete
        :return: None
        """
        data = {'categories': list2string(categories, '\n')}
        self._post(_name=APINames.Torrents, _method='removeCategories', data=data, **kwargs)

    ##########################################################################
    # RSS
    ##########################################################################
    @alias('rss_addFolder')
    @login_required
    def rss_add_folder(self, folder_path=None, **kwargs):
        """
        Add a RSS folder. Any intermediate folders in path must already exist. (alias: rss_addFolder)

        Exceptions:
            Conflict409Error

        :param folder_path: path to new folder (e.g. Linux\ISOs)
        :return: None
        """
        data = {'path': folder_path}
        self._post(_name=APINames.RSS, _method='addFolder', data=data, **kwargs)

    @alias('rss_addFeed')
    @login_required
    def rss_add_feed(self, url=None, item_path=None, **kwargs):
        """
        Add new RSS feed. Folders in path must already exist. (alias: rss_addFeed)

        Exceptions:
            Conflict409Error

        :param url: URL of RSS feed (e.g http://thepiratebay.org/rss/top100/200)
        :param item_path: Name and/or path for new feed (e.g. Folder\Subfolder\FeedName)
        :return: None
        """
        data = {'url': url,
                'path': item_path}
        self._post(_name=APINames.RSS, _method='addFeed', data=data, **kwargs)

    @alias('rss_removeItem')
    @login_required
    def rss_remove_item(self, item_path=None, **kwargs):
        """
        Remove a RSS item (folder, feed, etc). (alias: rss_removeItem)

        NOTE: Removing a folder also removes everything in it.

        Exceptions:
            Conflict409Error

        :param item_path: path to item to be removed (e.g. Folder\Subfolder\ItemName)
        :return: None
        """
        data = {'path': item_path}
        self._post(_name=APINames.RSS, _method='removeItem', data=data, **kwargs)

    @alias('rss_moveItem')
    @login_required
    def rss_move_item(self, orig_item_path=None, new_item_path=None, **kwargs):
        """
        Move/rename a RSS item (folder, feed, etc). (alias: rss_moveItem)

        Exceptions:
            Conflict409Error

        :param orig_item_path: path to item to be removed (e.g. Folder\Subfolder\ItemName)
        :param new_item_path: path to item to be removed (e.g. Folder\Subfolder\ItemName)
        :return: None
        """
        data = {'itemPath': orig_item_path,
                'destPath': new_item_path}
        self._post(_name=APINames.RSS, _method='moveItem', data=data, **kwargs)

    @response_json(RssitemsDict)
    @login_required
    def rss_items(self, include_feed_data=None, **kwargs):
        """
        Retrieve RSS items and optionally feed data.

        :param include_feed_data: True or false to include feed data
        :return: dictionary of RSS items
        """
        params = {'withData': include_feed_data}
        return self._get(_name=APINames.RSS, _method='items', params=params, **kwargs)

    @alias('rss_setRule')
    @login_required
    def rss_set_rule(self, rule_name=None, rule_def=None, **kwargs):
        """
        Create a new RSS auto-downloading rule. (alias: rss_setRule)

        :param rule_name: name for new rule
        :param rule_def: dictionary with rule fields
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#set-auto-downloading-rule
        :return: None
        """
        data = {'ruleName': rule_name,
                'ruleDef': dumps(rule_def)}
        self._post(_name=APINames.RSS, _method='setRule', data=data, **kwargs)

    @alias('rss_renameRule')
    @login_required
    def rss_rename_rule(self, orig_rule_name=None, new_rule_name=None, **kwargs):
        """
        Rename a RSS auto-download rule. (alias: rss_renameRule)

        :param orig_rule_name: current name of rule
        :param new_rule_name: new name for rule
        :return: None
        """
        data = {'ruleName': orig_rule_name,
                'newRuleName': new_rule_name}
        self._post(_name=APINames.RSS, _method='renameRule', data=data, **kwargs)

    @alias('rss_removeRule')
    @login_required
    def rss_remove_rule(self, rule_name=None, **kwargs):
        """
        Delete a RSS auto-downloading rule. (alias: rss_removeRule)

        :param rule_name: Name of rule to delete
        :return: None
        """
        data = {'ruleName': rule_name}
        self._post(_name=APINames.RSS, _method='removeRule', data=data, **kwargs)

    @response_json(RSSRulesDict)
    @login_required
    def rss_rules(self, **kwargs):
        """
        Retrieve RSS auto-download rule definitions.

        :return: None
        """
        return self._get(_name=APINames.RSS, _method='rules', **kwargs)

    ##########################################################################
    # Search
    ##########################################################################
    @version_implemented('2.1.1', 'search/start')
    @response_json(SearchJobDict)
    @login_required
    def search_start(self, pattern=None, plugins=None, category=None, **kwargs):
        """
        Start a search. Python must be installed. Host may limit nuber of concurrent searches.

        Exceptions:
            Conflict409Error

        :param pattern: term to search for
        :param plugins: list of plugins to use for searching (supports 'all' and 'enabled')
        :param category: categories to limit search; dependent on plugins. (supports 'all')
        :return: ID of search job
        """
        data = {'pattern': pattern,
                'plugins': list2string(plugins, '|'),
                'category': category}
        return self._post(_name=APINames.Search, _method='start', data=data, **kwargs)

    @version_implemented('2.1.1', 'search/stop')
    @login_required
    def search_stop(self, search_id=None, **kwargs):
        """
        Stop a running search.

        Exceptions:
            NotFound404Error

        :param search_id: ID of search job to stop
        :return: None
        """
        data = {'id': search_id}
        self._post(_name=APINames.Search, _method='stop', data=data, **kwargs)

    @version_implemented('2.1.1', 'search/status')
    @response_json(SearchStatusesList)
    @login_required
    def search_status(self, search_id=None, **kwargs):
        """
        Retrieve status of one or all searches.

        Exceptions:
            NotFound404Error

        :param search_id: ID of search to get status; leave emtpy for status of all jobs
        :return: dictionary of searches
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-search-status
        """
        params = {'id': search_id}
        return self._get(_name=APINames.Search, _method='status', params=params, **kwargs)

    @version_implemented('2.1.1', 'search/results')
    @response_json(SearchResultsDict)
    @login_required
    def search_results(self, search_id=None, limit=None, offset=None, **kwargs):
        """
        Retrieve the results for the search.

        Exceptions
            NotFound404Error
            Conflict409Error

        :param search_id: ID of search job
        :param limit: number of results to return
        :param offset: where to start returning results
        :return: Dictionary of results
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-search-results
        """
        data = {'id': search_id,
                'limit': limit,
                'offset': offset}
        return self._post(_name=APINames.Search, _method='results', data=data, **kwargs)

    @version_implemented('2.1.1', 'search/delete')
    @login_required
    def search_delete(self, search_id=None, **kwargs):
        """
        Delete a search job.

        ExceptionsL
            NotFound404Error

        :param search_id: ID of search to delete
        :return: None
        """
        data = {'id': search_id}
        self._post(_name=APINames.Search, _method='delete', data=data, **kwargs)

    @version_implemented('2.1.1', 'search/categories')
    @response_json(SearchCategoriesList)
    @login_required
    def search_categories(self, plugin_name=None, **kwargs):
        """
        Retrieve categories for search.

        :param plugin_name: Limit categories returned by plugin(s) (supports 'all' and 'enabled')
        :return: list of categories
        """
        data = {'pluginName': plugin_name}
        return self._post(_name=APINames.Search, _method='categories', data=data, **kwargs)

    @version_implemented('2.1.1', 'search/plugins')
    @response_json(SearchPluginsList)
    @login_required
    def search_plugins(self, **kwargs):
        """
        Retrieve details of search plugins.

        :return: List of plugins.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-search-plugins
        """
        return self._get(_name=APINames.Search, _method='plugins', **kwargs)

    @version_implemented('2.1.1', 'search/installPlugin')
    @alias('search_installPlugin')
    @login_required
    def search_install_plugin(self, sources=None, **kwargs):
        """
        Install search plugins from either URL or file. (alias: search_installPlugin)

        :param sources: list of URLs or filepaths
        :return: None
        """
        data = {'sources': list2string(sources, '|')}
        self._post(_name=APINames.Search, _method='installPlugin', data=data, **kwargs)

    @version_implemented('2.1.1', 'search/uninstallPlugin')
    @alias('search_uninstallPlugin')
    @login_required
    def search_uninstall_plugin(self, sources=None, **kwargs):
        """
        Uninstall search plugins. (alias: search_uninstallPlugin)

        :param sources:
        :return: None
        """
        data = {'sources': list2string(sources, '|')}
        self._post(_name=APINames.Search, _method='uninstallPlugin', data=data, **kwargs)

    @version_implemented('2.1.1', 'search/enablePlugin')
    @alias('search_enablePlugin')
    @login_required
    def search_enable_plugin(self, plugins=None, enable=None, **kwargs):
        """
        Enable or disable search plugin(s). (alias: search_enablePlugin)

        :param plugins: list of plugin names
        :param enable: True or False
        :return: None
        """
        data = {'names': plugins,
                'enable': enable}
        self._post(_name=APINames.Search, _method='enablePlugin', data=data, **kwargs)

    @version_implemented('2.1.1', 'search/updatePlugin')
    @alias('search_updatePlugins')
    @login_required
    def search_update_plugins(self, **kwargs):
        """
        Auto update search plugins. (alias: search_updatePlugins)

        :return: None
        """
        self._get(_name=APINames.Search, _method='updatePlugins', **kwargs)

    ##########################################################################
    # requests wrapper
    ##########################################################################
    def _get(self, _name=APINames.Blank, _method='', **kwargs):
        return self._request_wrapper(http_method='get',
                                     relative_path_list=[_name, _method],
                                     **kwargs)

    def _post(self, _name=APINames.Blank, _method='', **kwargs):
        return self._request_wrapper(http_method='post',
                                     relative_path_list=[_name, _method],
                                     **kwargs)

    # noinspection PyProtectedMember
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
                url_without_path = url_without_path._replace(netloc=url_without_path.path, path='')

            # detect supported scheme for URL
            logger.debug("Detecting scheme for URL...")
            try:
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
            url_without_path = url_without_path._replace(scheme=scheme)

            logger.debug("Base URL: %s" % url_without_path.geturl())

        # add the full API path to complete the URL
        url = url_without_path._replace(path=full_api_path)

        return url

    # noinspection PyTypeChecker
    def _request_wrapper(self, http_method, relative_path_list, **kwargs):
        """Wrapper to manage requests retries."""

        # This should retry at least twice to account from the WebUI API switching from HTTP to HTTPS.
        # During the second attempt, the URL is rebuilt using HTTP or HTTPS as appropriate.
        max_retries = 2
        for loop_count in range(1, (max_retries + 1)):
            try:
                return self._request(http_method, relative_path_list, **kwargs)
            except requests.exceptions.HTTPError as errh:
                if loop_count == max_retries:
                    error_message = "Failed to connect to qBittorrent. Invalid HTTP Reponse: %s" % repr(errh)
                    logger.debug(error_message)  # , exc_info=True)
                    raise APIConnectionError(error_message)
            except requests.exceptions.TooManyRedirects as errr:
                if loop_count == max_retries:
                    error_message = "Failed to connect to qBittorrent. Too many redirectse: %s" % repr(errr)
                    logger.debug(error_message)  # , exc_info=True)
                    raise APIConnectionError(error_message)
            except requests.exceptions.ConnectionError as ece:
                if loop_count == max_retries:
                    error_message = "Failed to connect to qBittorrent. Connection Error: %s" % repr(ece)
                    logger.debug(error_message)  # , exc_info=True)
                    raise APIConnectionError(error_message)
            except requests.exceptions.Timeout as et:
                if loop_count == max_retries:
                    error_message = "Failed to connect to qBittorrent. Timeout Error: %s" % repr(et)
                    logger.debug(error_message)  # , exc_info=True)
                    raise APIConnectionError(error_message)
            except requests.exceptions.RequestException as e:
                if loop_count == max_retries:
                    error_message = "Failed to connect to qBittorrent. Requests Error: %s" % repr(e)
                    logger.debug(error_message)  # , exc_info=True)
                    raise APIConnectionError(error_message)
            except HTTPError:
                raise
            except Exception as uexp:
                if loop_count == max_retries:
                    error_message = "Failed to connect to qBittorrent. Unknown Error: %s" % repr(uexp)
                    logger.debug(error_message)  # , exc_info=True)
                    raise APIConnectionError(error_message)

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
        requests_params = kwargs.pop('requests_params', {})

        # support for custom params to API
        data = kwargs.pop('data', {})
        params = kwargs.pop('params', {})
        if http_method == 'get':
            params.update(kwargs)
        if http_method == 'post':
            data.update(kwargs)

        # set up headers
        headers = kwargs.pop('headers', {})
        headers['Referer'] = self._URL_WITHOUT_PATH.geturl()
        headers['Origin'] = self._URL_WITHOUT_PATH.geturl()
        # headers['X-Requested-With'] = "XMLHttpRequest"

        # include the SID auth cookie unless we're trying to log in and get a SID
        cookies = {'SID': self._SID if "auth/login" not in url.path else ''}

        if not self._VERIFY_WEBUI_CERTIFICATE:
            disable_warnings(InsecureRequestWarning)
        response = requests.request(http_method,
                                    url.geturl(),
                                    headers=headers,
                                    cookies=cookies,
                                    verify=self._VERIFY_WEBUI_CERTIFICATE,
                                    data=data,
                                    params=params,
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
                if 'data' in kwargs:
                    error_torrent_hash = kwargs['data']['hash'] if ('hash' in kwargs['data']) else error_torrent_hash
                    error_torrent_hash = kwargs['data']['hashes'] if ('hashes' in kwargs['data']) else error_torrent_hash
                if error_torrent_hash == "" and 'params' in kwargs:
                    error_torrent_hash = kwargs['params']['hash'] if ('hash' in kwargs['params']) else error_torrent_hash
                    error_torrent_hash = kwargs['params']['hashes'] if ('hashes' in kwargs['params']) else error_torrent_hash
                if error_torrent_hash != "":
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
