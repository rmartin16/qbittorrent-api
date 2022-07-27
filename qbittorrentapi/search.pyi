from typing import Iterable
from typing import MutableMapping
from typing import Text

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import Dictionary
from qbittorrentapi.definitions import List
from qbittorrentapi.definitions import ListEntry

class SearchJobDictionary(Dictionary):
    def __init__(
        self, data: MutableMapping = None, client: SearchAPIMixIn = None
    ) -> None: ...
    def stop(self, **kwargs) -> None: ...
    def status(self, **kwargs) -> SearchStatusesList[SearchStatus]: ...
    def results(
        self, limit: Text | int = None, offset: Text | int = None, **kwargs
    ) -> SearchResultsDictionary: ...
    def delete(self, **kwargs) -> None: ...

class SearchResultsDictionary(Dictionary): ...

class SearchStatusesList(List):
    def __init__(
        self, list_entries: Iterable = None, client: SearchAPIMixIn = None
    ) -> None: ...

class SearchStatus(ListEntry): ...

class SearchCategoriesList(List):
    def __init__(
        self, list_entries: Iterable = None, client: SearchAPIMixIn = None
    ) -> None: ...

class SearchCategory(ListEntry): ...

class SearchPluginsList(List):
    def __init__(
        self, list_entries: Iterable = None, client: SearchAPIMixIn = None
    ) -> None: ...

class SearchPlugin(ListEntry): ...

class Search(ClientCache):
    def start(
        self,
        pattern: Text = None,
        plugins: Iterable[Text] = None,
        category: Text = None,
        **kwargs
    ) -> SearchJobDictionary: ...
    def stop(self, search_id: Text | int = None, **kwargs) -> None: ...
    def status(
        self, search_id: Text | int = None, **kwargs
    ) -> SearchStatusesList[SearchStatus]: ...
    def results(
        self,
        search_id: Text | int = None,
        limit: Text | int = None,
        offset: Text | int = None,
        **kwargs
    ) -> SearchResultsDictionary: ...
    def delete(self, search_id: Text | int = None, **kwargs) -> None: ...
    def categories(
        self, plugin_name: Text = None, **kwargs
    ) -> SearchCategoriesList[SearchCategory]: ...
    @property
    def plugins(self) -> SearchPluginsList[SearchPlugin]: ...
    def install_plugin(self, sources: Iterable[Text] = None, **kwargs) -> None: ...
    installPlugin = install_plugin
    def uninstall_plugin(self, sources: Iterable[Text] = None, **kwargs) -> None: ...
    uninstallPlugin = uninstall_plugin
    def enable_plugin(
        self, plugins: Iterable[Text] = None, enable: bool = None, **kwargs
    ) -> None: ...
    def update_plugins(self, **kwargs) -> None: ...
    updatePlugins = update_plugins

class SearchAPIMixIn(AppAPIMixIn):
    @property
    def search(self) -> Search: ...
    def search_start(
        self,
        pattern: Text = None,
        plugins: Iterable[Text] = None,
        category: Text = None,
        **kwargs
    ) -> SearchJobDictionary: ...
    def search_stop(self, search_id: Text | int = None, **kwargs) -> None: ...
    def search_status(
        self, search_id: Text | int = None, **kwargs
    ) -> SearchStatusesList[SearchStatus]: ...
    def search_results(
        self,
        search_id: Text | int = None,
        limit: Text | int = None,
        offset: Text | int = None,
        **kwargs
    ) -> SearchResultsDictionary: ...
    def search_delete(self, search_id: Text | int = None, **kwargs) -> None: ...
    def search_categories(
        self, plugin_name: Text = None, **kwargs
    ) -> SearchCategoriesList[SearchCategory]: ...
    def search_plugins(self, **kwargs) -> SearchPluginsList[SearchPlugin]: ...
    def search_install_plugin(
        self, sources: Iterable[Text] = None, **kwargs
    ) -> None: ...
    search_installPlugin = search_install_plugin
    def search_uninstall_plugin(
        self, names: Iterable[Text] = None, **kwargs
    ) -> None: ...
    search_uninstallPlugin = search_uninstall_plugin
    def search_enable_plugin(
        self, plugins: Iterable[Text] = None, enable: bool = None, **kwargs
    ) -> None: ...
    search_enablePlugin = search_enable_plugin
    def search_update_plugins(self, **kwargs) -> None: ...
    search_updatePlugins = search_update_plugins
