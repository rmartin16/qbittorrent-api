import logging

from qbittorrentapi.request import RequestMixIn
from qbittorrentapi.decorators import response_text
from qbittorrentapi.decorators import response_json
from qbittorrentapi.decorators import login_required
from qbittorrentapi.decorators import Alias
from qbittorrentapi.decorators import aliased
from qbittorrentapi.decorators import version_implemented
from qbittorrentapi.helpers import APINames
from qbittorrentapi.helpers import list2string
from qbittorrentapi.responses import TransferInfoDictionary

logger = logging.getLogger(__name__)


@aliased
class TransferMixIn(RequestMixIn):
    @response_json(TransferInfoDictionary)
    @login_required
    def transfer_info(self, **kwargs):
        """
        Retrieves the global transfer info usually found in qBittorrent status bar.

        :return: dictionary of status items
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-global-transfer-info
        """
        return self._get(_name=APINames.Transfer, _method='info', **kwargs)

    @Alias('transfer_speedLimitsMode')
    @response_text(str)
    @login_required
    def transfer_speed_limits_mode(self, **kwargs):
        """
        Retrieves whether alternative speed limits are enabled. (alias: transfer_speedLimitMode)

        :return: '1' if alternative speed limits are currently enabled, '0' otherwise
        """
        return self._get(_name=APINames.Transfer, _method='speedLimitsMode', **kwargs)

    @Alias('transfer_toggleSpeedLimitsMode')
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

    @Alias('transfer_downloadLimit')
    @response_text(int)
    @login_required
    def transfer_download_limit(self, **kwargs):
        """
        Retrieves download limit. 0 is unlimited. (alias: transfer_downloadLimit)

        :return: integer
        """
        return self._get(_name=APINames.Transfer, _method='downloadLimit', **kwargs)

    @Alias('transfer_uploadLimit')
    @response_text(int)
    @login_required
    def transfer_upload_limit(self, **kwargs):
        """
        Retrieves upload limit. 0 is unlimited. (alias: transfer_uploadLimit)

        :return: integer
        """
        return self._get(_name=APINames.Transfer, _method='uploadLimit', **kwargs)

    @Alias('transfer_setDownloadLimit')
    @login_required
    def transfer_set_download_limit(self, limit=None, **kwargs):
        """
        Set the global download limit in bytes/second. (alias: transfer_setDownloadLimit)

        :param limit: download limit in bytes/second (0 or -1 for no limit)
        :return: None
        """
        data = {'limit': limit}
        self._post(_name=APINames.Transfer, _method='setDownloadLimit', data=data, **kwargs)

    @Alias('transfer_setUploadLimit')
    @login_required
    def transfer_set_upload_limit(self, limit=None, **kwargs):
        """
        Set the global download limit in bytes/second. (alias: transfer_setUploadLimit)

        :param limit: upload limit in bytes/second (0 or -1 for no limit)
        :return: None
        """
        data = {'limit': limit}
        self._post(_name=APINames.Transfer, _method='setUploadLimit', data=data, **kwargs)

    @Alias('transfer_banPeers')
    @version_implemented('2.3', 'transfer/banPeers')
    @login_required
    def transfer_ban_peers(self, peers=None, **kwargs):
        """
        Ban one or more peers. (alias: transfer_banPeers)

        :param peers: one or more peers to ban. each peer should take the form 'host:port'
        :return: None
        """
        data = {'peers': list2string(peers, '|')}
        self._post(_name=APINames.Transfer, _method='banPeers', data=data, **kwargs)
