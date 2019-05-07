import requests
import logging
import json
from os import path
from functools import wraps
from pkg_resources import parse_version

from qbittorrentapi import VERSION
from qbittorrentapi.objects import *

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
          form of {'json': json.dumps({'dht': True})}...
    
    torrents/downloadLimit and uploadLimit
        - Hashes handling is non-standard. 404 is not returned for bad hashes
          and 'all' doesn't work.
        - https://github.com/qbittorrent/qBittorrent/blob/6de02b0f2a79eeb4d7fb624c39a9f65ffe181d68/src/webui/api/torrentscontroller.cpp#L754
'''


##########################################################################
# Exception Classes
##########################################################################
class APIError(Exception):
    pass


class LoginFailed(APIError):
    pass


class ConnectionError(APIError):
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
            logger.info("Not logged in...attempting login")
            obj.auth_log_in()
        try:
            return f(obj, *args, **kwargs)
        except HTTP403Error:
            logger.warning("Login may have expired...attempting new login")
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
            try:
                return response_class(result.text)
            except AttributeError:
                if isinstance(result, response_class):
                    return result
                return response_class()
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
                        result = json.loads(response.text)
                    return response_class(result)
            except Exception:
                logger.exception("Exception during repsonse parsing. Returning empty repsonse.")
                return response_class()
        return wrapper
    return _inner


def version_implemented(version_introduced, endpoint):
    """
    Prevent hitting an endpoint if the host doesn't support it.

    :param version_introduced: version endpoint was made available
    :param endpoint: API endpoint (e.g. /torrents/categories)
    """
    def _inner(f):
        @wraps(f)
        def wrapper(obj, *args, **kwargs):
            current_version = obj.app_web_api_version()
            if is_version_less_than(version_introduced, current_version):
                return f(obj, *args, **kwargs)
            else:
                logger.error("%s not implemented until api version %s (installed version: %s)" % (endpoint, version_introduced, current_version))
                return "Not implemented until v%s" % version_introduced
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
    Blank = ''
    Authorization = "auth/"
    Application = "app/"
    Log = "log/"
    Sync = "sync/"
    Transfer = "transfer/"
    Torrents = "torrents/"
    RSS = "rss/"
    Search = "search/"


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


def is_version_less_than(ver1, ver2):
    """
    Determine if ver1 is equal to or later than ver2.

    :param ver1: version to check
    :param ver2: current version of application
    :return: True or False
    """
    return parse_version(ver1) <= parse_version(ver2)

##########################################################################
# API Client
##########################################################################
@aliased
class Client(object):
    """
    Initialize API for qBittorrent client.

    Host must be specified. Username and password can be specified at login.
    A call to auth_log_in is not explicitly required if username and password are
    provided during Client construction,.

    :param host: hostname of qBittorrent client (eg http://localhost:8080)
    :param username: user name for qBittorrent client
    :param password: password for qBittorrent client
    """

    _URL_API_PATH = "api/v2/"
    _URL_PATH = ""

    _MOCK_WEB_API_VERSION = ''  # '2.1'

    # TODO: consider whether password should hang around in the event it is
    #       necessary to attempt an automatic re-login (e.g. if the SID expires)
    def __init__(self, host='', username='', password=''):
        self.host = host
        self.username = username
        self.password = password

        assert self.host

        if self.username != "":
            assert self.password

        if not self.host.endswith('/'):
            self.host += '/'
        self._URL_PATH = self.host + self._URL_API_PATH

        self.SID = None
        self._cached_web_api_version = None

    ##########################################################################
    # Authorization
    ##########################################################################
    @property
    def is_logged_in(self):
        return bool(self.SID)

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
        if username != '':
            self.username = username
            self.password = password

        try:
            response = self._post(name=APINames.Authorization,
                                  method='login',
                                  data={'username': self.username,
                                        'password': self.password})
            self.SID = response.cookies['SID']
            logger.info("Login successful for user '%s'." % self.username)
            logger.debug("SID: %s" % self.SID)
            # cache to avoid perf hit from version checking certain endpoints
            self._cached_web_api_version = self.app_web_api_version()
        except KeyError:
            logger.error("Login failed for user '%s'" % self.username)
            raise suppress_context(LoginFailed("Login authorization failed for user '%s'" % self.username))

    @login_required
    def auth_log_out(self):
        """ Log out of qBittorrent client"""
        self._get(name=APINames.Authorization, method='logout')

    ##########################################################################
    # Application
    ##########################################################################
    @response_text(str)
    @login_required
    def app_version(self):
        """
        Retrieve application version

        :return: string
        """
        return self._get(name=APINames.Application, method='version')

    @alias('app_webapiVersion')
    @response_text(str)
    @login_required
    def app_web_api_version(self):
        """
        Retrieve web API version. (alias: app_webapiVersion)

        :return: string
        """
        if self._cached_web_api_version:
            return self._cached_web_api_version
        if self._MOCK_WEB_API_VERSION:
            return self._MOCK_WEB_API_VERSION
        return self._get(name=APINames.Application, method='webapiVersion')

    @version_implemented('2.3.0', 'app/buildInfo')
    @response_json(BuildInfoDict)
    @alias('app_buildInfo')
    @login_required
    def app_build_info(self):
        """
        Retrieve build info. (alias: app_buildInfo)

        :return: Dictionary of build info. Each piece of info is an attribute.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-build-info
        """
        return self._get(name=APINames.Application, method='buildInfo')

    @login_required
    def app_shutdown(self):
        """Shutdown qBittorrent"""
        return self._get(name=APINames.Application, method='shutdown')

    @response_json(ApplicationPreferencesDict)
    @login_required
    def app_preferences(self):
        """
        Retrieve qBittorrent application preferences.

        :return: Dictionary of preferences. Each preference is an attribute.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-application-preferences
        """
        return self._get(name=APINames.Application, method='preferences')

    @alias('app_setPreferences')
    @login_required
    def app_set_preferences(self, prefs=None):
        """
        Set one or more preferences in qBittorrent application. (alias: app_setPreferences)

        :param prefs: dictionary of preferences to set
        :return:
        """
        data = {'json': json.dumps(prefs)}
        return self._post(name=APINames.Application, method='setPreferences', data=data)

    @alias('app_defaultSavePath')
    @response_text(str)
    @login_required
    def app_default_save_path(self):
        """
        Retrieves the default path for where torrents are saved. (alias: app_defaultSavePath)

        :return: string
        """
        return self._get(name=APINames.Application, method='defaultSavePath')

    @alias('app_defaultSavePath')
    @response_text(str)
    @login_required
    def app_default_save_path(self):
        """
        Retrieve default save path for torrents. (alias: app_defaultSavePath)

        :return: string for default save path
        """
        return self._get(name=APINames.Application, method='defaultSavePath')

    ##########################################################################
    # Log
    ##########################################################################
    @response_json(LogMainList)
    @login_required
    def log_main(self, normal=None, info=None, warning=None, critical=None, last_known_id=None):
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
        return self._get(name=APINames.Log, method='main', params=parameters)

    @response_json(LogPeersList)
    @login_required
    def log_peers(self, last_known_id=None):
        """
        Retrieve qBittorrent peer log.

        :param last_known_id: only entries with an ID greater than this value will be returned
        :return: list of log entries in a List
        """
        parameters = {'last_known_id': last_known_id}
        return self._get(name=APINames.Log, method='peers', params=parameters)

    ##########################################################################
    # Sync
    ##########################################################################
    @response_json(SyncMainDataDict)
    @login_required
    def sync_maindata(self, rid=None):
        """
        Retrieves sync data.

        :param rid: response ID
        :return: dictionary response
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-main-data
        """
        parameters = {'rid': rid}
        return self._get(name=APINames.Sync, method='maindata', params=parameters)

    @alias('sync_torrentPeers')
    @response_json(SyncTorrentPeersDict)
    @login_required
    def sync_torrent_peers(self, torrent_hash=None, rid=None):
        """
        Retrieves torrent sync data. (alias: sync_torrentPeers)

        Exceptions:
            NotFound404Error

        :param torrent_hash: hash for torrent
        :param rid: response ID
        :return: Dictionary of torrent sync data.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-peers-data
        """
        data = {'hash': torrent_hash,
                'rid': rid}
        return self._post(name=APINames.Sync, method='torrentPeers', data=data)

    ##########################################################################
    # Transfer
    ##########################################################################
    @response_json(TransferInfoDict)
    @login_required
    def transfer_info(self):
        """
        Retrieves the global transfer info usually found in qBittorrent status bar.

        :return: dictioanry of status items
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-global-transfer-info
        """
        return self._get(name=APINames.Transfer, method='info')

    @alias('transfer_speedLimitsMode')
    @response_text(bool)
    @login_required
    def transfer_speed_limits_mode(self):
        """
        Retrieves whether alternative speed limits are enabled. (alias: transfer_speedLimitMode)

        :return: True if alternative speed limits are currently enabled
        """
        return self._get(name=APINames.Transfer, method='speedLimitsMode')

    @alias('transfer_toggleSpeedLimitsMode')
    @login_required
    def transfer_toggle_speed_limits_mode(self):
        """
        Toggles whether alternative speed limited are enabled. (alias: transfer_toggleSpeedLimitsMode)

        :return: None
        """
        self._post(name=APINames.Transfer, method='toggleSpeedLimitsMode')

    @alias('transfer_downloadLimit')
    @response_text(int)
    @login_required
    def transfer_download_limit(self):
        """
        Retrieves download limit. 0 is unlimited. (alias: transfer_downloadLimit)

        :return: integer
        """
        return self._get(name=APINames.Transfer, method='downloadLimit')

    @alias('transfer_uploadLimit')
    @response_text(int)
    @login_required
    def transfer_upload_limit(self):
        """
        Retrieves upload limit. 0 is unlimited. (alias: transfer_uploadLimit)

        :return: integer
        """
        return self._get(name=APINames.Transfer, method='uploadLimit')

    @alias('transfer_setDownloadLimit')
    @login_required
    def transfer_set_download_limit(self, limit=None):
        """
        Set the global download limit in bytes/second. (alias: transfer_setDownloadLimit)

        :param limit: download limit in bytes/second (0 or -1 for no limit)
        :return: None
        """
        data = {'limit': limit}
        self._post(name=APINames.Transfer, method='setDownloadLimit', data=data)

    @alias('transfer_setUploadLimit')
    @login_required
    def transfer_set_upload_limit(self, limit=None):
        """
        Set the global download limit in bytes/second. (alias: transfer_setUploadLimit)

        :param limit: upload limit in bytes/second (0 or -1 for no limit)
        :return: None
        """
        data = {'limit': limit}
        self._post(name=APINames.Transfer, method='setUploadLimit', data=data)

    ##########################################################################
    # Torrent Management
    ##########################################################################
    @response_json(TorrentInfoList)
    @login_required
    def torrents_info(self, status_filter=None, category=None, sort=None, reverse=False, limit=None, offset=None, torrent_hashes=None):
        """
        Retrieves list of info for torrents.

        Note: torrent_hashes is available starting web API version 2.0.1

        :param status_filter: Filter list by all, downloading, completed, paused, active, inactive, resumed
        :param category: Filter list by category
        :param sort: Sort list by any property returned
        :param reverse: Reverse sorting
        :param limit: Limit length of list
        :param offset: Start of list (if <0, offset from end of list)
        :param torrent_hashes: Filter list by hash (seperate multiple hashes with a '|')
        :return: List of torrents
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-list
        """
        if self.app_web_api_version() < '2.0.1':
            torrent_hashes = None

        data = {'filter': status_filter,
                'category': category,
                'sort': sort,
                'reverse': reverse,
                'limit': limit,
                'offset': offset,
                'hashes': list2string(torrent_hashes, '|')}
        return self._post(name=APINames.Torrents, method='info', data=data)

    @response_json(TorrentPropertiesDict)
    @login_required
    def torrents_properties(self, torrent_hash=None):
        """
        Retrieve individual torrent's properties.

        Exceptions:
            NotFound404Error

        :param torrent_hash: hash for torrent
        :return: Dictionary of torrent properties
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-generic-properties
        """
        parameters = {'hash': torrent_hash}
        return self._post(name=APINames.Torrents, method='properties', data=parameters)

    @response_json(TrackersList)
    @login_required
    def torrents_trackers(self, torrent_hash=None):
        """
        Retrieve individual torrent's trackers.

        Exceptions:
            NotFound404Error

        :param torrent_hash: hash for torrent
        :return: List of torrent's trackers
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-trackers
        """
        data = {'hash': torrent_hash}
        return self._post(name=APINames.Torrents, method='trackers', data=data)

    @response_json(WebSeedsList)
    @login_required
    def torrents_webseeds(self, torrent_hash=None):
        """
        Retrieve individual torrent's web seeds.

        Exceptions:
            NotFound404Error

        :param torrent_hash: hash for torrent
        :return: List of torrent's web seeds
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-web-seeds
        """
        data = {'hash': torrent_hash}
        return self._post(name=APINames.Torrents, method='webseeds', data=data)

    @response_json(TorrentFilesList)
    @login_required
    def torrents_files(self, torrent_hash=None):
        """
        Retrieve individual torrent's files.

        Exceptions:
            NotFound404Error

        :param torrent_hash: hash for torrent
        :return: List of torrent's files
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-torrent-contents
        """
        data = {'hash': torrent_hash}
        return self._post(name=APINames.Torrents, method='files', data=data)

    @alias('torrents_pieceStates')
    @response_json(TorrentPieceInfoList)
    @login_required
    def torrents_piece_states(self, torrent_hash=None):
        """
        Retrieve individual torrent's pieces' states. (alias: torrents_pieceStates)

        Exceptions:
            NotFound404Error

        :param torrent_hash: hash for torrent
        :return: list of torrent's pieces' states
        """
        data = {'hash': torrent_hash}
        return self._post(name=APINames.Torrents, method='pieceStates', data=data)

    @alias('torrents_pieceHashes')
    @response_json(TorrentPieceInfoList)
    @login_required
    def torrents_piece_hashes(self, torrent_hash=None):
        """
        Retrieve individual torrent's pieces' hashes. (alias: torrents_pieceHashes)

        Exceptions:
            NotFound404Error

        :param torrent_hash: hash for torrent
        :return: List of torrent's pieces' hashes
        """
        data = {'hash': torrent_hash}
        return self._post(name=APINames.Torrents, method='pieceHashes', data=data)

    @login_required
    def torrents_resume(self, torrent_hashes=None):
        """
        Resume one or more torrents in qBitorrent.

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        self._post(name=APINames.Torrents, method='resume', data=data)

    @login_required
    def torrents_pause(self, torrent_hashes=None):
        """
        Pause one or more torrents in qBitorrent.

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, "|")}
        self._post(name=APINames.Torrents, method='pause', data=data)

    @login_required
    def torrents_delete(self, torrent_hashes=None, delete_files=None):
        """
        Remove a torrent from qBittorrent and optionally delete its files.

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param delete_files: Truw to delete the torrent's files
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|'),
                'deleteFiles': delete_files}
        self._post(name=APINames.Torrents, method='delete', data=data)

    @login_required
    def torrents_recheck(self, torrent_hashes=None):
        """
        Recheck a torrent in qBittorrent.

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        self._post(name=APINames.Torrents, method='recheck', data=data)

    @version_implemented('2.0.2', 'torrents/reannounce')
    @login_required
    def torrents_reannounce(self, torrent_hashes=None):
        """
        Reannounce a torrent.

        Note: torrents/reannounce not available web API version 2.0.2

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        self._post(name=APINames.Torrents, method='reannounce', data=data)

    @response_text(str)
    @login_required
    def torrents_add(self, urls=None, torrent_files=None, save_path=None, cookie=None, category=None,
                     is_skip_checking=None, is_paused=None, is_root_folder=None, rename=None,
                     upload_limit=None, download_limit=None, use_auto_torrent_management=None,
                     is_sequential_download=None, is_first_last_piece_priority=None):
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
            torrent_files = [(path.basename(file), open(file, 'rb')) for file in
                             [path.abspath(path.realpath(path.expanduser(file))) for file in torrent_files]]

        return self._post(name=APINames.Torrents, method='add', data=data, files=torrent_files)

    @alias('torrents_addTrackers')
    @login_required
    def torrents_add_trackers(self, torrent_hash=None, urls=None):
        """
        Add trackers to a torrent. (alias: torrents_addTrackers)

        Exceptions:
            NotFound404Error

        :param torrent_hash: hash for torrent
        :param urls: tracker urls to add to torrent
        :return: None
        """
        data = {'hash': torrent_hash,
                'urls': list2string(urls, '\n')}
        self._post(name=APINames.Torrents, method='addTrackers', data=data)

    @version_implemented('2.2.0', 'torrents/editTracker')
    @alias('torrents_editTracker')
    @login_required
    def torrents_edit_tracker(self, torrent_hash=None, original_url=None, new_url=None):
        """
        Replace a torrent's tracker with a different one. (alias: torrents_editTrackers)

        Exceptions:
            InvalidRequest400
            NotFound404Error
            Conflict409Error

        :param torrent_hash: hash for torrent
        :param original_url: URL for existing tracker
        :param new_url: new URL to replace
        :return: None
        """
        data = {'hash': torrent_hash,
                'origUrl': original_url,
                'newUrl': new_url}
        self._post(name=APINames.Torrents, method='editTracker', data=data)

    @version_implemented('2.2.0', 'torrents/removeTrackers')
    @alias('removeTrackers')
    @login_required
    def torrents_remove_trackers(self, torrent_hash=None, urls=None):
        """
        Remove trackers from a torrent. (alias: torrents_removeTrackers)

        Exceptions:
            NotFound404Error
            Conflict409Error

        :param torrent_hash: hash for torrent
        :param urls: tracker urls to removed from torrent
        :return: None
        """
        data = {'hash': torrent_hash,
                'urls': list2string(urls, '|')}
        self._post(name=APINames.Torrents, method='removeTrackers', data=data)

    @alias('torrents_increasePrio')
    @login_required
    def torrents_increase_priority(self, torrent_hashes=None):
        """
        Increase the priority of a torrent. Torrent Queuing must be enabled. (alias: torrents_increasePrio)

        Exceptions:
            Conflict409

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        self._post(name=APINames.Torrents, method='increasePrio', data=data)

    @alias('torrents_decreasePrio')
    @login_required
    def torrents_decrease_priority(self, torrent_hashes=None):
        """
        Decrease the priority of a torrent. Torrent Queuing must be enabled. (alias: torrents_decreasePrio)

        Exceptions:
            Conflict409

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        self._post(name=APINames.Torrents, method='decreasePrio', data=data)

    @alias('torrents_topPrio')
    @login_required
    def torrents_top_priority(self, torrent_hashes=None):
        """
        Set torrent as highest priority. Torrent Queuing must be enabled. (alias: torrents_topPrio)

        Exceptions:
            Conflict409

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        self._post(name=APINames.Torrents, method='topPrio', data=data)

    @alias('torrents_bottomPrio')
    @login_required
    def torrents_bottom_priority(self, torrent_hashes=None):
        """
        Set torrent as highest priority. Torrent Queuing must be enabled. (alias: torrents_bottomPrio)

        Exceptions:
            Conflict409

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        self._post(name=APINames.Torrents, method='bottomPrio', data=data)

    @alias('torrents_filePrio')
    @login_required
    def torrents_file_priority(self, torrent_hash="", file_ids=None, priority=None):
        """
        Set priority for one or more files. (alias: torrents_filePrio)

        Exceptions:
            InvalidRequest400 if priority is invalid or at least one file ID is not an integer
            NotFound404
            Conflict409 if torrent metadata has not finished downloading or at least one file was not found
        :param torrent_hash: hash for torrent
        :param file_ids: single file ID or a list. See
        :param priority: priority for file(s)
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#set-file-priority
        :return:
        """
        data = {'hash': torrent_hash,
                'id': list2string(file_ids, "|"),
                'priority': priority}
        self._post(name=APINames.Torrents, method='filePrio', data=data)

    @alias('torrents_downloadLimit')
    @response_json(TorrentLimitsDict)
    @login_required
    def torrents_download_limit(self, torrent_hashes=None):
        """
        Retrieve the download limit for one or more torrents. (alias: torrents_downloadLimit)

        :return: dictioanry {hash: limit} (-1 represents no limit)
        """
        data = {'hashes': list2string(torrent_hashes, "|")}
        return self._post(name=APINames.Torrents, method='downloadLimit', data=data)

    @alias('torrents_setDownloadLimit')
    @login_required
    def torrents_set_download_limit(self, torrent_hashes=None, limit=None):
        """
        Set the download limit for one or more torrents. (alias: torrents_setDownloadLimit)

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param limit: bytes/second (-1 sets the limit to infinity)
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|'),
                'limit': limit}
        self._post(name=APINames.Torrents, method='setDownloadLimit', data=data)

    @version_implemented('2.0.1', 'torrents/setShareLimits')
    @alias('torrents_setShareLimits')
    @login_required
    def torrents_set_share_limits(self, torrent_hashes=None, ratio_limit=None, seeding_time_limit=None):
        """
        Set share limits for one or more torrents.

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param ratio_limit: max ratio to seed a torrent. (-2 means use the global value and -1 is no limit)
        :param seeding_time_limit: minutes (-2 means use the global value and -1 is no limit_
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, "|"),
                'ratioLimit': ratio_limit,
                'seedingTimeLimit': seeding_time_limit}
        self._post(name=APINames.Torrents, method='setShareLimits', data=data)

    @alias('torrents_uploadLimit')
    @response_json(TorrentLimitsDict)
    @login_required
    def torrents_upload_limit(self, torrent_hashes=None):
        """
        Retrieve the upload limit for onee or more torrents. (alias: torrents_uploadLimit)

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: dictionary of limits
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        return self._post(name=APINames.Torrents, method='uploadLimit', data=data)

    @alias('torrents_setUploadLimit')
    @login_required
    def torrents_set_upload_limit(self, torrent_hashes=None, limit=None):
        """
        Set the upload limit for one or more torrents. (alias: torrents_setUploadLimit)

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param limit: bytes/second (-1 sets the limit to infinity)
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|'),
                'limit': limit}
        self._post(name=APINames.Torrents, method='setUploadLimit', data=data)

    @alias('torrents_setLocation')
    @login_required
    def torrents_set_location(self, torrent_hashes=None, location=None):
        """
        Set location for torrents's files. (alias: torrents_setLocation)

        Exceptions:
            Unauthorized403 if the user doesn't have permissions to write to the location
            Conflict409 if the directory cannot be created at the location

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param location: disk location to move torrent's files
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|'),
                'location': location}
        self._post(name=APINames.Torrents, method='setLocation', data=data)

    @login_required
    def torrents_rename(self, torrent_hash=None, new_torrent_name=None):
        """
        Rename a torrent.

        Exceptions:
            NotFound404

        :param torrent_hash: hash for torrent
        :param new_torrent_name: new name for torrent
        :return: None
        """
        data = {'hash': torrent_hash,
                'name': new_torrent_name}
        self._post(name=APINames.Torrents, method='rename', data=data)

    @version_implemented('2.1.0', 'torrents/categories')
    @response_json(dict)
    @login_required
    def torrents_categories(self):
        """
        Retrieve all category definitions

        Note: torrents/categories is not available until v2.1.0
        :return: dictionary of categories
        """
        return self._get(name=APINames.Torrents, method='categories')

    @alias('torrents_setCategory')
    @login_required
    def torrents_set_category(self, torrent_hashes=None, category=None):
        """
        Set a category for one or more torrents. (alias: torrents_setCategory)

        Exceptions:
            Conflict409 for bad category

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param category: category to assign to torrent
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|'),
                'category': category}
        self._post(name=APINames.Torrents, method='setCategory', data=data)

    @alias('torrents_createCategory')
    @login_required
    def torrents_create_category(self, new_category=None, save_path=None):
        """
        Create a new torrent category. (alias: torrents_createCategory)

        Note: save_path is not available until web API version 2.1.0

        Exceptions:
            Conflict409 if category name is not valid or unable to create

        :param new_category: name for new category
        :param save_path: location to save torrents for this category
        :return: None
        """
        # savePath was introduced in v2.1.0
        if is_version_less_than(self.app_web_api_version(), '2.1.0'):
            save_path = None
        data = {'category': new_category,
                'savePath': save_path}
        self._post(name=APINames.Torrents, method='createCategory', data=data)

    @version_implemented('2.1.0', 'torrents/editCategory')
    @alias('torrents_editCategory')
    @login_required
    def torrents_edit_category(self, category=None, save_path=None):
        """
        Edit an existing category. (alias: torrents_editCategory)

        Note: torrents/editCategory not available until web API version 2.1.0

        Exceptions:
            Conflict409

        :param category: category to edit
        :param save_path: new location to save files for this category
        :return: None
        """
        data = {'category': category,
                'savePath': save_path}
        self._post(name=APINames.Torrents, method='editCategory', data=data)

    @alias('torrents_removeCategories')
    @login_required
    def torrents_remove_categories(self, categories=None):
        """
        Delete one or more categories. (alias: torrents_removeCategories)

        :param categories: categories to delete
        :return: None
        """
        data = {'categories': list2string(categories, '\n')}
        self._post(name=APINames.Torrents, method='removeCategories', data=data)

    @alias('torrents_setAutoManagement')
    @login_required
    def torrents_set_auto_management(self, torrent_hashes=None, enable=None):
        """
        Enable or disable automatic torrent management for one or more torrents. (alias: torrents_setAutoManagement)

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param enable: True or False
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|'),
                'enable': enable}
        self._post(name=APINames.Torrents, method='setAutoManagement', data=data)

    @alias('torrents_toggleSequentialDownload')
    @login_required
    def torrents_toggle_sequential_download(self, torrent_hashes=None):
        """
        Toggle sequential download for one or more torrents. (alias: torrents_toggleSequentialDownload)

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes)}
        self._post(name=APINames.Torrents, method='toggleSequentialDownload', data=data)

    @alias('torrents_toggleFirstLastPiecePrio')
    @login_required
    def torrents_toggle_first_last_piece_priority(self, torrent_hashes):
        """
        Toggle priority of first/last piece downloading. (alias: torrents_toggleFirstLastPiecePrio)
        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|')}
        self._post(name=APINames.Torrents, method='toggleFirstLastPiecePrio', data=data)

    @alias('torrents_setForceStart')
    @login_required
    def torrents_set_force_start(self, torrent_hashes=None, enable=None):
        """
        Force start one or more torrents. (alias: torrents_setForceStart)

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param enable: True or False (False makes this equivalent to torrents_resume())
        :return: None
        """
        data = {'hashes': list2string(torrent_hashes, '|'),
                'value': enable}
        self._post(name=APINames.Torrents, method='setForceStart', data=data)

    @alias('torrents_setSuperSeeding')
    @login_required
    def torrents_set_super_seeding(self, torrent_hashes=None, enable=None):
        """
        Set one or more torrents as super seeding. (alias: torrents_setSuperSeeding)

        :param torrent_hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :param enable: True or False
        :return:
        """
        data = {'hashes': list2string(torrent_hashes, '|'),
                'value': enable}
        self._post(name=APINames.Torrents, method='setSuperSeeding', data=data)

    ##########################################################################
    # RSS
    ##########################################################################
    @alias('rss_addFolder')
    @login_required
    def rss_add_folder(self, folder_path=None):
        """
        Add a RSS folder. Any intermediate folders in path must already exist. (alias: rss_addFolder)

        Exceptions:
            Conflict409Error

        :param folder_path: path to new folder (e.g. Linux\ISOs)
        :return: None
        """
        data = {'path': folder_path}
        self._post(name=APINames.RSS, method='addFolder', data=data)

    @alias('rss_addFeed')
    @login_required
    def rss_add_feed(self, url=None, item_path=None):
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
        self._post(name=APINames.RSS, method='addFeed', data=data)

    @alias('rss_removeItem')
    @login_required
    def rss_remove_item(self, item_path=None):
        """
        Remove a RSS item (folder, feed, etc). (alias: rss_removeItem)

        NOTE: Removing a folder also removes everything in it.

        Exceptions:
            Conflict409Error

        :param item_path: path to item to be removed (e.g. Folder\Subfolder\ItemName)
        :return: None
        """
        data = {'path': item_path}
        self._post(name=APINames.RSS, method='removeItem', data=data)

    @alias('rss_moveItem')
    @login_required
    def rss_move_item(self, orig_item_path=None, new_item_path=None):
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
        self._post(name=APINames.RSS, method='moveItem', data=data)

    @response_json(RssitemsDict)
    @login_required
    def rss_items(self, include_feed_data=None):
        """
        Retrieve RSS items and optionally feed data.

        :param include_feed_data: True or false to include feed data
        :return: dictionary of RSS items
        """
        params = {'withData': include_feed_data}
        return self._get(name=APINames.RSS, method='items', params=params)

    @alias('rss_setRule')
    @login_required
    def rss_set_rule(self, rule_name=None, rule_def=None):
        """
        Create a new RSS auto-downloading rule. (alias: rss_setRule)

        :param rule_name: name for new rule
        :param rule_def: dictionary with rule fields
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#set-auto-downloading-rule
        :return: None
        """
        data = {'ruleName': rule_name,
                'ruleDef': json.dumps(rule_def)}
        self._post(name=APINames.RSS, method='setRule', data=data)

    @alias('rss_renameRule')
    @login_required
    def rss_rename_rule(self, orig_rule_name=None, new_rule_name=None):
        """
        Rename a RSS auto-download rule. (alias: rss_renameRule)

        :param orig_rule_name: current name of rule
        :param new_rule_name: new name for rule
        :return: None
        """
        data = {'ruleName': orig_rule_name,
                'newRuleName': new_rule_name}
        self._post(name=APINames.RSS, method='renameRule', data=data)

    @alias('rss_removeRule')
    @login_required
    def rss_remove_rule(self, rule_name=None):
        """
        Delete a RSS auto-downloading rule. (alias: rss_removeRule)

        :param rule_name: Name of rule to delete
        :return: None
        """
        data = {'ruleName': rule_name}
        self._post(name=APINames.RSS, method='removeRule', data=data)

    @response_json(RSSRulesDict)
    @login_required
    def rss_rules(self):
        """
        Retrieve RSS auto-download rule definitions.

        :return: None
        """
        return self._get(name=APINames.RSS, method='rules')

    ##########################################################################
    # Search
    ##########################################################################
    @version_implemented('2.1.1', 'search/start')
    @response_json(SearchJobDict)
    @login_required
    def search_start(self, pattern=None, plugins=None, category=None):
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
        return self._post(name=APINames.Search, method='start', data=data)

    @version_implemented('2.1.1', 'search/stop')
    @login_required
    def search_stop(self, search_id=None):
        """
        Stop a running search.

        Exceptions:
            NotFound404Error

        :param search_id: ID of search job to stop
        :return: None
        """
        data = {'id': search_id}
        self._post(name=APINames.Search, method='stop', data=data)

    @version_implemented('2.1.1', 'search/status')
    @response_json(SearchStatusesList)
    @login_required
    def search_status(self, search_id=None):
        """
        Retrieve status of one or all searches.

        Exceptions:
            NotFound404Error

        :param search_id: ID of search to get status; leave emtpy for status of all jobs
        :return: dictionary of searches
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-search-status
        """
        params = {'id': search_id}
        return self._get(name=APINames.Search, method='status', params=params)

    @version_implemented('2.1.1', 'search/results')
    @response_json(SearchResultsDict)
    @login_required
    def search_results(self, search_id=None, limit=None, offset=None):
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
        params = {'id': search_id,
                  'limit': limit,
                  'offset': offset}
        return self._post(name=APINames.Search, method='results', data=params)

    @version_implemented('2.1.1', 'search/delete')
    @login_required
    def search_delete(self, search_id=None):
        """
        Delete a search job.

        ExceptionsL
            NotFound404Error

        :param search_id: ID of search to delete
        :return: None
        """
        data = {'id': search_id}
        self._post(name=APINames.Search, method='delete', data=data)

    @version_implemented('2.1.1', 'search/categories')
    @response_json(SearchCategoriesList)
    @login_required
    def search_categories(self, plugin_name=None):
        """
        Retrieve categories for search.

        :param plugin_name: Limit categories returned by plugin(s) (supports 'all' and 'enabled')
        :return: list of categories
        """
        data = {'pluginName': plugin_name}
        return self._post(name=APINames.Search, method='categories', data=data)

    @version_implemented('2.1.1', 'search/plugins')
    @response_json(SearchPluginsList)
    @login_required
    def search_plugins(self):
        """
        Retrieve details of search plugins.

        :return: List of plugins.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-search-plugins
        """
        return self._post(name=APINames.Search, method='plugins')

    @version_implemented('2.1.1', 'search/installPlugin')
    @alias('search_installPlugin')
    @login_required
    def search_install_plugin(self, sources=None):
        """
        Install search plugins from either URL or file. (alias: search_installPlugin)

        :param sources: list of URLs or filepaths
        :return: None
        """
        data = {'sources': list2string(sources, '|')}
        self._post(name=APINames.Search, method='installPlugin', data=data)

    @version_implemented('2.1.1', 'search/uninstallPlugin')
    @alias('search_uninstallPlugin')
    @login_required
    def search_uninstall_plugin(self, sources=None):
        """
        Uninstall search plugins. (alias: search_uninstallPlugin)

        :param sources:
        :return: None
        """
        data = {'sources': list2string(sources, '|')}
        self._post(name=APINames.Search, method='uninstallPlugin', data=data)

    @version_implemented('2.1.1', 'search/enablePlugin')
    @alias('search_enablePlugin')
    @login_required
    def search_enable_plugin(self, plugins=None, enable=None):
        """
        Enable or disable search plugin(s). (alias: search_enablePlugin)

        :param plugins: list of plugin names
        :param enable: True or False
        :return: None
        """
        data = {'names': plugins,
                'enable': enable}
        self._post(name=APINames.Search, method='enablePlugin', data=data)

    @version_implemented('2.1.1', 'search/updatePlugin')
    @alias('search_updatePlugins')
    @login_required
    def search_update_plugins(self):
        """
        Auto update search plugins. (alias: search_updatePlugins)

        :return: None
        """
        self._post(name=APINames.Search, method='updatePlugins')

    ##########################################################################
    # requests wrapper
    ##########################################################################
    def _get(self, name=APINames.Blank, method='', **kwargs):
        relative_url = name + method
        return self._request(method='get',
                             relative_url=relative_url,
                             **kwargs)

    def _post(self, name=APINames.Blank, method='', **kwargs):
        relative_url = name + method
        return self._request(method='post',
                             relative_url=relative_url,
                             **kwargs)

    def _request(self, method, relative_url, **kwargs):

        url = self._URL_PATH + relative_url

        headers = kwargs.pop('headers', {})
        headers['Referer'] = self.host
        headers['Origin'] = self.host
        # headers['X-Requested-With'] = "XMLHttpRequest"

        cookies = {}
        if self.SID is not None and "auth/login" not in url:
            cookies = {'SID': self.SID}

        try:
            response = requests.request(method, url, headers=headers, cookies=cookies, **kwargs)

            resp_logger = logger.info
            max_length = 254
            if response.status_code != 200:
                resp_logger = logger.warning
                max_length = 10000

            resp_logger("Request URL: %s" % response.url)
            if str(response.request.body) not in ["None", ""] and "auth/login" not in url:
                body_len = max_length if len(response.request.body) > max_length else len(response.request.body)
                resp_logger("Request body: %s%s" % (response.request.body[:body_len], "...<truncated>" if body_len >= 80 else ''))

            resp_logger("Response status: %s (%s)" % (response.status_code, response.reason))
            if response.text:
                text_len = max_length if len(response.text) > max_length else len(response.text)
                resp_logger("Response text: %s%s" % (response.text[:text_len], "...<truncated>" if text_len >= 80 else ''))

            # TODO: consider adding support to suppress exceptions and just return an empty response
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
                Primarily reserved for XSS and host header issues.
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
                raise APIError(error_message)

        except requests.exceptions.ConnectionError as e:
            logger.error("Connection error wtih qBittorrent")
            raise ConnectionError(repr(e))

        return response
