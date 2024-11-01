from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import cast

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    ClientCache,
    Dictionary,
    JsonValueT,
    List,
    ListEntry,
    ListInputT,
)


class SearchResultsDictionary(Dictionary[JsonValueT]):
    """
    Response for :meth:`~SearchAPIMixIn.search_results`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-search-results>`_
    """  # noqa: E501


class SearchStatus(ListEntry):
    """Item in :class:`SearchStatusesList`"""


class SearchStatusesList(List[SearchStatus]):
    """
    Response for :meth:`~SearchAPIMixIn.search_status`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-search-status>`_
    """  # noqa: E501

    def __init__(self, list_entries: ListInputT, client: SearchAPIMixIn | None = None):
        super().__init__(list_entries, entry_class=SearchStatus, client=client)


class SearchCategory(ListEntry):
    """Item in :class:`SearchCategoriesList`"""


class SearchCategoriesList(List[SearchCategory]):
    """Response for :meth:`~SearchAPIMixIn.search_categories`"""

    def __init__(self, list_entries: ListInputT, client: SearchAPIMixIn | None = None):
        super().__init__(list_entries, entry_class=SearchCategory, client=client)


class SearchPlugin(ListEntry):
    """Item in :class:`SearchPluginsList`"""


class SearchPluginsList(List[SearchPlugin]):
    """
    Response for :meth:`~SearchAPIMixIn.search_plugins`.

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-search-plugins>`_
    """

    def __init__(self, list_entries: ListInputT, client: SearchAPIMixIn | None = None):
        super().__init__(list_entries, entry_class=SearchPlugin, client=client)


class SearchAPIMixIn(AppAPIMixIn):
    """
    Implementation for all ``Search`` API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> search_job = client.search_start(pattern="Ubuntu", plugins="all", category="all")
        >>> client.search_stop(search_id=search_job.id)
        >>> # or
        >>> search_job.stop()
    """  # noqa: E501

    @property
    def search(self) -> Search:
        """
        Allows for transparent interaction with ``Search`` endpoints.

        See Search class for usage.
        """
        if self._search is None:
            self._search = Search(client=self)
        return self._search

    def search_start(
        self,
        pattern: str | None = None,
        plugins: str | Iterable[str] | None = None,
        category: str | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchJobDictionary:
        """
        Start a search. Python must be installed. Host may limit number of concurrent
        searches.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        :raises Conflict409Error:

        :param pattern: term to search for
        :param plugins: list of plugins to use for searching (supports 'all' and
            'enabled')
        :param category: categories to limit search; dependent on plugins. (supports
            'all')
        """
        data = {
            "pattern": pattern,
            "plugins": self._list2string(plugins, "|"),
            "category": category,
        }
        return self._post_cast(
            _name=APINames.Search,
            _method="start",
            data=data,
            response_class=SearchJobDictionary,
            version_introduced="2.1.1",
            **kwargs,
        )

    def search_stop(
        self,
        search_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Stop a running search.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        :raises NotFound404Error:
        :param search_id: ID of search job to stop
        """
        data = {"id": search_id}
        self._post(
            _name=APINames.Search,
            _method="stop",
            data=data,
            version_introduced="2.1.1",
            **kwargs,
        )

    def search_status(
        self,
        search_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchStatusesList:
        """
        Retrieve status of one or all searches.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        :raises NotFound404Error:

        :param search_id: ID of search to get status; leave empty for status of all jobs
        """
        params = {"id": search_id}
        return self._get_cast(
            _name=APINames.Search,
            _method="status",
            params=params,
            response_class=SearchStatusesList,
            version_introduced="2.1.1",
            **kwargs,
        )

    def search_results(
        self,
        search_id: str | int | None = None,
        limit: str | int | None = None,
        offset: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchResultsDictionary:
        """
        Retrieve the results for the search.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        :raises NotFound404Error:
        :raises Conflict409Error:

        :param search_id: ID of search job
        :param limit: number of results to return
        :param offset: where to start returning results
        """
        data = {"id": search_id, "limit": limit, "offset": offset}
        return self._post_cast(
            _name=APINames.Search,
            _method="results",
            data=data,
            response_class=SearchResultsDictionary,
            version_introduced="2.1.1",
            **kwargs,
        )

    def search_delete(
        self,
        search_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Delete a search job.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        :raises NotFound404Error:
        :param search_id: ID of search to delete
        """
        data = {"id": search_id}
        self._post(
            _name=APINames.Search,
            _method="delete",
            data=data,
            version_introduced="2.1.1",
            **kwargs,
        )

    def search_categories(
        self,
        plugin_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchCategoriesList:
        """
        Retrieve categories for search.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1) and removed
        with qBittorrent v4.3.0 (Web API v2.6).

        :param plugin_name: Limit categories returned by plugin(s)
            (supports ``all`` and ``enabled``)
        """
        data = {"pluginName": plugin_name}
        return self._post_cast(
            _name=APINames.Search,
            _method="categories",
            data=data,
            response_class=SearchCategoriesList,
            version_introduced="2.1.1",
            version_removed="2.6",
            **kwargs,
        )

    def search_plugins(self, **kwargs: APIKwargsT) -> SearchPluginsList:
        """
        Retrieve details of search plugins.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).
        """
        return self._get_cast(
            _name=APINames.Search,
            _method="plugins",
            response_class=SearchPluginsList,
            version_introduced="2.1.1",
            **kwargs,
        )

    def search_install_plugin(
        self,
        sources: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Install search plugins from either URL or file.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        :param sources: list of URLs or filepaths
        """
        data = {"sources": self._list2string(sources, "|")}
        self._post(
            _name=APINames.Search,
            _method="installPlugin",
            data=data,
            version_introduced="2.1.1",
            **kwargs,
        )

    search_installPlugin = search_install_plugin

    def search_uninstall_plugin(
        self,
        names: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Uninstall search plugins.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        :param names: names of plugins to uninstall
        """
        data = {"names": self._list2string(names, "|")}
        self._post(
            _name=APINames.Search,
            _method="uninstallPlugin",
            data=data,
            version_introduced="2.1.1",
            **kwargs,
        )

    search_uninstallPlugin = search_uninstall_plugin

    def search_enable_plugin(
        self,
        plugins: str | Iterable[str] | None = None,
        enable: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Enable or disable search plugin(s).

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        :param plugins: list of plugin names
        :param enable: Defaults to ``True`` if ``None`` or unset;
            use ``False`` to disable
        """
        data = {
            "names": self._list2string(plugins, "|"),
            "enable": True if enable is None else bool(enable),
        }
        self._post(
            _name=APINames.Search,
            _method="enablePlugin",
            data=data,
            version_introduced="2.1.1",
            **kwargs,
        )

    search_enablePlugin = search_enable_plugin

    def search_update_plugins(self, **kwargs: APIKwargsT) -> None:
        """
        Auto update search plugins.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).
        """
        self._post(
            _name=APINames.Search,
            _method="updatePlugins",
            version_introduced="2.1.1",
            **kwargs,
        )

    search_updatePlugins = search_update_plugins

    def search_download_torrent(
        self,
        url: str | None = None,
        plugin: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Download a .torrent file or magnet for a search plugin.

        This method was introduced with qBittorrent v5.0.0 (Web API v2.11).

        :param url: URL for .torrent file or magnet
        :param plugin: Name of the plugin
        """
        data = {
            "torrentUrl": url,
            "pluginName": plugin,
        }
        self._post(
            _name=APINames.Search,
            _method="downloadTorrent",
            data=data,
            version_introduced="2.11",
            **kwargs,
        )

    search_downloadTorrent = search_download_torrent


class SearchJobDictionary(ClientCache[SearchAPIMixIn], Dictionary[JsonValueT]):
    """Response for :meth:`~SearchAPIMixIn.search_start`"""

    def __init__(self, data: Mapping[str, JsonValueT], client: SearchAPIMixIn):
        self._search_job_id: int | None = cast(int, data.get("id", None))
        super().__init__(data=data, client=client)

    def stop(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_stop`."""
        self._client.search_stop(search_id=self._search_job_id, **kwargs)

    def status(self, **kwargs: APIKwargsT) -> SearchStatusesList:
        """Implements :meth:`~SearchAPIMixIn.search_status`."""
        return self._client.search_status(search_id=self._search_job_id, **kwargs)

    def results(
        self,
        limit: str | int | None = None,
        offset: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchResultsDictionary:
        """Implements :meth:`~SearchAPIMixIn.search_results`."""
        return self._client.search_results(
            limit=limit,
            offset=offset,
            search_id=self._search_job_id,
            **kwargs,
        )

    def delete(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_delete`."""
        return self._client.search_delete(search_id=self._search_job_id, **kwargs)


class Search(ClientCache[SearchAPIMixIn]):
    """
    Allows interaction with ``Search`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # this is all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'search_' prepended)
        >>> # initiate searches and retrieve results
        >>> search_job = client.search.start(pattern="Ubuntu", plugins="all", category="all")
        >>> status = search_job.status()
        >>> results = search_job.result()
        >>> search_job.delete()
        >>> # inspect and manage plugins
        >>> plugins = client.search.plugins
        >>> cats = client.search.categories(plugin_name="...")
        >>> client.search.install_plugin(sources="...")
        >>> client.search.update_plugins()
    """  # noqa: E501

    def start(
        self,
        pattern: str | None = None,
        plugins: str | Iterable[str] | None = None,
        category: str | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchJobDictionary:
        """Implements :meth:`~SearchAPIMixIn.search_start`."""
        return self._client.search_start(
            pattern=pattern,
            plugins=plugins,
            category=category,
            **kwargs,
        )

    def stop(
        self,
        search_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_stop`."""
        return self._client.search_stop(search_id=search_id, **kwargs)

    def status(
        self,
        search_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchStatusesList:
        """Implements :meth:`~SearchAPIMixIn.search_status`."""
        return self._client.search_status(search_id=search_id, **kwargs)

    def results(
        self,
        search_id: str | int | None = None,
        limit: str | int | None = None,
        offset: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchResultsDictionary:
        """Implements :meth:`~SearchAPIMixIn.search_results`."""
        return self._client.search_results(
            search_id=search_id,
            limit=limit,
            offset=offset,
            **kwargs,
        )

    def delete(
        self,
        search_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_delete`."""
        return self._client.search_delete(search_id=search_id, **kwargs)

    def categories(
        self,
        plugin_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> SearchCategoriesList:
        """Implements :meth:`~SearchAPIMixIn.search_categories`."""
        return self._client.search_categories(plugin_name=plugin_name, **kwargs)

    @property
    def plugins(self) -> SearchPluginsList:
        """Implements :meth:`~SearchAPIMixIn.search_plugins`."""
        return self._client.search_plugins()

    def install_plugin(
        self,
        sources: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_install_plugin`."""
        return self._client.search_install_plugin(sources=sources, **kwargs)

    installPlugin = install_plugin

    def uninstall_plugin(
        self,
        sources: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_uninstall_plugin`."""
        return self._client.search_uninstall_plugin(sources=sources, **kwargs)

    uninstallPlugin = uninstall_plugin

    def enable_plugin(
        self,
        plugins: str | Iterable[str] | None = None,
        enable: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_enable_plugin`."""
        return self._client.search_enable_plugin(
            plugins=plugins,
            enable=enable,
            **kwargs,
        )

    enablePlugin = enable_plugin

    def update_plugins(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_update_plugins`."""
        return self._client.search_update_plugins(**kwargs)

    updatePlugins = update_plugins

    def download_torrent(
        self,
        url: str | None = None,
        plugin: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~SearchAPIMixIn.search_download_torrent`."""
        return self._client.search_download_torrent(url=url, plugin=plugin)

    downloadTorrent = download_torrent
