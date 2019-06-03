import logging

from qbittorrentapi.request import RequestMixIn
from qbittorrentapi.decorators import response_json
from qbittorrentapi.decorators import login_required
from qbittorrentapi.decorators import Alias
from qbittorrentapi.decorators import aliased
from qbittorrentapi.helpers import APINames
from qbittorrentapi.responses import SyncMainDataDictionary
from qbittorrentapi.responses import SyncTorrentPeersDictionary

logger = logging.getLogger(__name__)


@aliased
class SyncMixIn(RequestMixIn):
    # TODO: revert to _post or figure out the Bad Request with no data...seems most likely content-length issue
    @response_json(SyncMainDataDictionary)
    @login_required
    def sync_maindata(self, rid=None, **kwargs):
        """
        Retrieves sync data.

        :param rid: response ID
        :return: dictionary response
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-main-data
        """
        parameters = {'rid': rid}
        return self._get(_name=APINames.Sync, _method='maindata', params=parameters, **kwargs)

    @Alias('sync_torrentPeers')
    @response_json(SyncTorrentPeersDictionary)
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
