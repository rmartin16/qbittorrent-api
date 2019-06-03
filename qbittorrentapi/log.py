import logging

from qbittorrentapi.request import RequestMixIn
from qbittorrentapi.decorators import response_json
from qbittorrentapi.decorators import login_required
from qbittorrentapi.helpers import APINames
from qbittorrentapi.responses import LogMainList
from qbittorrentapi.responses import LogPeersList

logger = logging.getLogger(__name__)


class LogMixIn(RequestMixIn):
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
