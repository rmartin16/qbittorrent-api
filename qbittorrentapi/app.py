import logging
from json import dumps

from qbittorrentapi.request import RequestMixIn
from qbittorrentapi.decorators import response_text
from qbittorrentapi.decorators import response_json
from qbittorrentapi.decorators import login_required
from qbittorrentapi.decorators import version_implemented
from qbittorrentapi.decorators import Alias
from qbittorrentapi.decorators import aliased
from qbittorrentapi.helpers import APINames
from qbittorrentapi.responses import ApplicationPreferencesDictionary
from qbittorrentapi.responses import BuildInfoDictionary

logger = logging.getLogger(__name__)


@aliased
class AppMixIn(RequestMixIn):
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

    @Alias('app_webapiVersion')
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

    @version_implemented('2.3', 'app/buildInfo')
    @response_json(BuildInfoDictionary)
    @Alias('app_buildInfo')
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

    @response_json(ApplicationPreferencesDictionary)
    @login_required
    def app_preferences(self, **kwargs):
        """
        Retrieve qBittorrent application preferences.

        :return: Dictionary of preferences. Each preference is an attribute.
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#get-application-preferences
        """
        return self._get(_name=APINames.Application, _method='preferences', **kwargs)

    @Alias('app_setPreferences')
    @login_required
    def app_set_preferences(self, prefs=None, **kwargs):
        """
        Set one or more preferences in qBittorrent application. (alias: app_setPreferences)

        :param prefs: dictionary of preferences to set
        :return: None
        """
        data = {'json': dumps(prefs, separators=(',', ':'))}
        return self._post(_name=APINames.Application, _method='setPreferences', data=data, **kwargs)

    @Alias('app_defaultSavePath')
    @response_text(str)
    @login_required
    def app_default_save_path(self, **kwargs):
        """
        Retrieves the default path for where torrents are saved. (alias: app_defaultSavePath)

        :return: string
        """
        return self._get(_name=APINames.Application, _method='defaultSavePath', **kwargs)
