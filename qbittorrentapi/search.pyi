from typing import Any
from typing import Dict
from typing import Iterable
from typing import List as ListT
from typing import Mapping
from typing import Optional
from typing import Text
from typing import TypeVar
from typing import Union

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import Dictionary
from qbittorrentapi.definitions import List
from qbittorrentapi.definitions import ListEntry

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
KWARGS = Any
JsonValueT = Union[None, int, Text, bool, ListT[JsonValueT], Dict[Text, JsonValueT]]

class SearchJobDictionary(Dictionary[K, V]):
    def __init__(
        self,
        data: Optional[Mapping[Any, Any]] = None,
        client: Optional[SearchAPIMixIn] = None,
    ) -> None: ...
    def stop(self, **kwargs: KWARGS) -> None: ...
    def status(
        self, **kwargs: KWARGS
    ) -> SearchStatusesList[SearchStatus[Text, JsonValueT]]: ...
    def results(
        self,
        limit: Optional[Text | int] = None,
        offset: Optional[Text | int] = None,
        **kwargs: KWARGS
    ) -> SearchResultsDictionary[Text, JsonValueT]: ...
    def delete(self, **kwargs: KWARGS) -> None: ...

class SearchResultsDictionary(Dictionary[K, V]): ...

class SearchStatusesList(List[T]):
    def __init__(
        self,
        list_entries: Optional[Iterable[ListEntry[Text, JsonValueT]]] = None,
        client: Optional[SearchAPIMixIn] = None,
    ) -> None: ...

class SearchStatus(ListEntry[K, V]): ...

class SearchCategoriesList(List[T]):
    def __init__(
        self,
        list_entries: Optional[Iterable[ListEntry[Text, JsonValueT]]] = None,
        client: Optional[SearchAPIMixIn] = None,
    ) -> None: ...

class SearchCategory(ListEntry[K, V]): ...

class SearchPluginsList(List[T]):
    def __init__(
        self,
        list_entries: Optional[Iterable[ListEntry[Text, JsonValueT]]] = None,
        client: Optional[SearchAPIMixIn] = None,
    ) -> None: ...

class SearchPlugin(ListEntry[K, V]): ...

class Search(ClientCache):
    def start(
        self,
        pattern: Optional[Text] = None,
        plugins: Optional[Iterable[Text]] = None,
        category: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> SearchJobDictionary[Text, JsonValueT]: ...
    def stop(
        self, search_id: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> None: ...
    def status(
        self, search_id: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> SearchStatusesList[SearchStatus[Text, JsonValueT]]: ...
    def results(
        self,
        search_id: Optional[Text | int] = None,
        limit: Optional[Text | int] = None,
        offset: Optional[Text | int] = None,
        **kwargs: KWARGS
    ) -> SearchResultsDictionary[Text, JsonValueT]: ...
    def delete(
        self, search_id: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> None: ...
    def categories(
        self, plugin_name: Optional[Text] = None, **kwargs: KWARGS
    ) -> SearchCategoriesList[SearchCategory[Text, JsonValueT]]: ...
    @property
    def plugins(self) -> SearchPluginsList[SearchPlugin[Text, JsonValueT]]: ...
    def install_plugin(
        self, sources: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    installPlugin = install_plugin
    def uninstall_plugin(
        self, sources: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    uninstallPlugin = uninstall_plugin
    def enable_plugin(
        self,
        plugins: Optional[Iterable[Text]] = None,
        enable: Optional[bool] = None,
        **kwargs: KWARGS
    ) -> None: ...
    def update_plugins(self, **kwargs: KWARGS) -> None: ...
    updatePlugins = update_plugins

class SearchAPIMixIn(AppAPIMixIn):
    @property
    def search(self) -> Search: ...
    def search_start(
        self,
        pattern: Optional[Text] = None,
        plugins: Optional[Iterable[Text]] = None,
        category: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> SearchJobDictionary[Text, JsonValueT]: ...
    def search_stop(
        self, search_id: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> None: ...
    def search_status(
        self, search_id: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> SearchStatusesList[SearchStatus[Text, JsonValueT]]: ...
    def search_results(
        self,
        search_id: Optional[Text | int] = None,
        limit: Optional[Text | int] = None,
        offset: Optional[Text | int] = None,
        **kwargs: KWARGS
    ) -> SearchResultsDictionary[Text, JsonValueT]: ...
    def search_delete(
        self, search_id: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> None: ...
    def search_categories(
        self, plugin_name: Optional[Text] = None, **kwargs: KWARGS
    ) -> SearchCategoriesList[SearchCategory[Text, JsonValueT]]: ...
    def search_plugins(
        self, **kwargs: KWARGS
    ) -> SearchPluginsList[SearchPlugin[Text, JsonValueT]]: ...
    def search_install_plugin(
        self, sources: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    search_installPlugin = search_install_plugin
    def search_uninstall_plugin(
        self, names: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    search_uninstallPlugin = search_uninstall_plugin
    def search_enable_plugin(
        self,
        plugins: Optional[Iterable[Text]] = None,
        enable: Optional[bool] = None,
        **kwargs: KWARGS
    ) -> None: ...
    search_enablePlugin = search_enable_plugin
    def search_update_plugins(self, **kwargs: KWARGS) -> None: ...
    search_updatePlugins = search_update_plugins
