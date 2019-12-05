import logging
from os import path
from os import strerror as os_strerror
import errno

from qbittorrentapi.request import RequestMixIn
from qbittorrentapi.helpers import list2string, APINames
from qbittorrentapi.decorators import response_text
from qbittorrentapi.decorators import response_json
from qbittorrentapi.decorators import login_required
from qbittorrentapi.decorators import version_implemented
from qbittorrentapi.decorators import Alias
from qbittorrentapi.decorators import aliased
from qbittorrentapi.responses import TorrentFilesList
from qbittorrentapi.responses import TorrentInfoList
from qbittorrentapi.responses import TorrentLimitsDictionary
from qbittorrentapi.responses import TorrentPieceInfoList
from qbittorrentapi.responses import TorrentPropertiesDictionary
from qbittorrentapi.responses import TorrentCategoriesDictionary
from qbittorrentapi.responses import TorrentsAddPeersDictionary
from qbittorrentapi.responses import TagList
from qbittorrentapi.responses import TrackersList
from qbittorrentapi.responses import WebSeedsList
from qbittorrentapi.exceptions import TorrentFileNotFoundError
from qbittorrentapi.exceptions import TorrentFilePermissionError
from qbittorrentapi.exceptions import TorrentFileError

logger = logging.getLogger(__name__)


@aliased
class TorrentsMixIn(RequestMixIn):
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
            TorrentFileNotFoundError if a torrent file doesn't exist
            TorrentFilePermissionError if read permission is denied to torrent file

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
        :param download_limit: download limit in bytes/second
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
                'autoTMM': (None, use_auto_torrent_management),
                'sequentialDownload': (None, is_sequential_download),
                'firstLastPiecePrio': (None, is_first_last_piece_priority)
                }

        if torrent_files:
            if isinstance(torrent_files, str):
                torrent_files = [torrent_files]
            torrent_file = torrent_files[0]
            try:
                torrent_files = [(path.basename(torrent_file), open(torrent_file, 'rb'))
                                 for torrent_file in [path.abspath(path.realpath(path.expanduser(torrent_file)))
                                                      for torrent_file in torrent_files]]
            except IOError as io_err:
                if io_err.errno == errno.ENOENT:
                    raise TorrentFileNotFoundError(errno.ENOENT, os_strerror(errno.ENOENT), torrent_file)
                elif io_err.errno == errno.EACCES:
                    raise TorrentFilePermissionError(errno.ENOENT, os_strerror(errno.EACCES), torrent_file)
                else:
                    raise TorrentFileError(io_err)

        return self._post(_name=APINames.Torrents, _method='add', data=data, files=torrent_files, **kwargs)

    # INDIVIDUAL TORRENT ENDPOINTS
    @response_json(TorrentPropertiesDictionary)
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

    @Alias('torrents_pieceStates')
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

    @Alias('torrents_pieceHashes')
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

    @Alias('torrents_addTrackers')
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
    @Alias('torrents_editTracker')
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
    @Alias('torrents_removeTrackers')
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

    @Alias('torrents_filePrio')
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
    def torrents_info(self, status_filter=None, category=None, sort=None, reverse=None, limit=None, offset=None,
                      hashes=None, **kwargs):
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

    @Alias('torrents_increasePrio')
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

    @Alias('torrents_decreasePrio')
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

    @Alias('torrents_topPrio')
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

    @Alias('torrents_bottomPrio')
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

    @Alias('torrents_downloadLimit')
    @response_json(TorrentLimitsDictionary)
    @login_required
    def torrents_download_limit(self, hashes=None, **kwargs):
        """
        Retrieve the download limit for one or more torrents. (alias: torrents_downloadLimit)

        :return: dictioanry {hash: limit} (-1 represents no limit)
        """
        data = {'hashes': list2string(hashes, "|")}
        return self._post(_name=APINames.Torrents, _method='downloadLimit', data=data, **kwargs)

    @Alias('torrents_setDownloadLimit')
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
    @Alias('torrents_setShareLimits')
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

    @Alias('torrents_uploadLimit')
    @response_json(TorrentLimitsDictionary)
    @login_required
    def torrents_upload_limit(self, hashes=None, **kwargs):
        """
        Retrieve the upload limit for onee or more torrents. (alias: torrents_uploadLimit)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: dictionary of limits
        """
        data = {'hashes': list2string(hashes, '|')}
        return self._post(_name=APINames.Torrents, _method='uploadLimit', data=data, **kwargs)

    @Alias('torrents_setUploadLimit')
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

    @Alias('torrents_setLocation')
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

    @Alias('torrents_setCategory')
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

    @Alias('torrents_setAutoManagement')
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

    @Alias('torrents_toggleSequentialDownload')
    @login_required
    def torrents_toggle_sequential_download(self, hashes=None, **kwargs):
        """
        Toggle sequential download for one or more torrents. (alias: torrents_toggleSequentialDownload)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes)}
        self._post(_name=APINames.Torrents, _method='toggleSequentialDownload', data=data, **kwargs)

    @Alias('torrents_toggleFirstLastPiecePrio')
    @login_required
    def torrents_toggle_first_last_piece_priority(self, hashes=None, **kwargs):
        """
        Toggle priority of first/last piece downloading. (alias: torrents_toggleFirstLastPiecePrio)

        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|')}
        self._post(_name=APINames.Torrents, _method='toggleFirstLastPiecePrio', data=data, **kwargs)

    @Alias('torrents_setForceStart')
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

    @Alias('torrents_setSuperSeeding')
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

    @Alias('torrents_addPeers')
    @version_implemented('2.3', 'torrents/addPeers')
    @response_json(TorrentsAddPeersDictionary)
    @login_required
    def torrents_add_peers(self, peers=None, hashes=None, **kwargs):
        """
        Add one or more peers to one or more torrents. (alias: torrents_addPeers)

        Exceptions:
            InvalidRequest400Error for invalid peers

        :param peers: one or more peers to add. each peer should take the form 'host:port'
        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: dictionary - {<hash>: {'added': #, 'failed': #}}
        """
        data = {'hashes': list2string(hashes, '|'),
                'peers': list2string(peers, '|')}
        return self._post(_name=APINames.Torrents, _method='addPeers', data=data, **kwargs)

    # TORRENT CATEGORIES ENDPOINTS
    @version_implemented('2.1.0', 'torrents/categories')
    @response_json(TorrentCategoriesDictionary)
    @login_required
    def torrents_categories(self, **kwargs):
        """
        Retrieve all category definitions

        Note: torrents/categories is not available until v2.1.0
        :return: dictionary of categories
        """
        return self._get(_name=APINames.Torrents, _method='categories', **kwargs)

    @Alias('torrents_createCategory')
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
    @Alias('torrents_editCategory')
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

    @Alias('torrents_removeCategories')
    @login_required
    def torrents_remove_categories(self, categories=None, **kwargs):
        """
        Delete one or more categories. (alias: torrents_removeCategories)

        :param categories: categories to delete
        :return: None
        """
        data = {'categories': list2string(categories, '\n')}
        self._post(_name=APINames.Torrents, _method='removeCategories', data=data, **kwargs)

    # TORRENT TAGS ENDPOINTS
    @version_implemented('2.3', 'torrents/tags')
    @response_json(TagList)
    @login_required
    def torrents_tags(self, **kwargs):
        """
        Retrieve all tag definitions.

        :return: list of tags
        """
        return self._post(_name=APINames.Torrents, _method='tags', **kwargs)

    @Alias('torrents_addTags')
    @version_implemented('2.3', 'torrents/addTags')
    @login_required
    def torrents_add_tags(self, tags=None, hashes=None, **kwargs):
        """
        Add one or more tags to one or more torrents. (alias: torrents_addTags)

        Note: Tags that do not exist will be created on-the-fly.

        :param tags: tag name or list of tags
        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'tags': list2string(tags, ',')}
        self._post(_name=APINames.Torrents, _method='addTags', data=data, **kwargs)

    @Alias('torrents_removeTags')
    @version_implemented('2.3', 'torrents/removeTags')
    @login_required
    def torrents_remove_tags(self, tags=None, hashes=None, **kwargs):
        """
        Add one or more tags to one or more torrents. (alias: torrents_removeTags)

        :param tags: tag name or list of tags
        :param hashes: single torrent hash or list of torrent hashes. Or 'all' for all torrents.
        :return: None
        """
        data = {'hashes': list2string(hashes, '|'),
                'tags': list2string(tags, ',')}
        self._post(_name=APINames.Torrents, _method='removeTags', data=data, **kwargs)

    @Alias('torrents_createTags')
    @version_implemented('2.3', 'torrents/createTags')
    @login_required
    def torrents_create_tags(self, tags=None, **kwargs):
        """
        Create one or more tags. (alias: torrents_createTags)

        :param tags: tag name or list of tags
        :return: None
        """
        data = {'tags': list2string(tags, ',')}
        self._post(_name=APINames.Torrents, _method='createTags', data=data, **kwargs)

    @Alias('torrents_deleteTags')
    @version_implemented('2.3', 'torrents/deleteTags')
    @login_required
    def torrents_delete_tags(self, tags=None, **kwargs):
        """
        Delete one or more tags. (alias: torrents_deleteTags)

        :param tags: tag name or list of tags
        :return: None
        """
        data = {'tags': list2string(tags, ',')}
        self._post(_name=APINames.Torrents, _method='deleteTags', data=data, **kwargs)
