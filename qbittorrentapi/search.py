import logging

from qbittorrentapi.request import RequestMixIn
from qbittorrentapi.helpers import list2string, APINames
from qbittorrentapi.decorators import response_json
from qbittorrentapi.decorators import login_required
from qbittorrentapi.decorators import version_implemented
from qbittorrentapi.decorators import Alias
from qbittorrentapi.decorators import aliased
from qbittorrentapi.responses import SearchCategoriesList
from qbittorrentapi.responses import SearchJobDictionary
from qbittorrentapi.responses import SearchPluginsList
from qbittorrentapi.responses import SearchResultsDictionary
from qbittorrentapi.responses import SearchStatusesList

logger = logging.getLogger(__name__)


@aliased
class SearchMixIn(RequestMixIn):
    @version_implemented('2.1.1', 'search/start')
    @response_json(SearchJobDictionary)
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
    @response_json(SearchResultsDictionary)
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
    @Alias('search_installPlugin')
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
    @Alias('search_uninstallPlugin')
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
    @Alias('search_enablePlugin')
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
    @Alias('search_updatePlugins')
    @login_required
    def search_update_plugins(self, **kwargs):
        """
        Auto update search plugins. (alias: search_updatePlugins)

        :return: None
        """
        self._get(_name=APINames.Search, _method='updatePlugins', **kwargs)
