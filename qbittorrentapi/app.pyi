from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Text
from typing import TypeVar
from typing import Union

from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import Dictionary
from qbittorrentapi.request import Request

K = TypeVar("K")
V = TypeVar("V")
KWARGS = Any
JsonValueT = Union[None, int, Text, bool, List[JsonValueT], Dict[str, JsonValueT]]

class ApplicationPreferencesDictionary(Dictionary[K, V]): ...
class BuildInfoDictionary(Dictionary[K, V]): ...

class Application(ClientCache):
    @property
    def version(self) -> Text: ...
    @property
    def web_api_version(self) -> Text: ...
    webapiVersion = web_api_version
    @property
    def build_info(self) -> BuildInfoDictionary[Text, JsonValueT]: ...
    buildInfo = build_info
    def shutdown(self) -> None: ...
    @property
    def preferences(self) -> ApplicationPreferencesDictionary[Text, JsonValueT]: ...
    @preferences.setter
    def preferences(self, value: Mapping[Text, JsonValueT]) -> None: ...
    def set_preferences(
        self, prefs: Optional[Mapping[Text, JsonValueT]] = None, **kwargs: KWARGS
    ) -> None: ...
    setPreferences = set_preferences
    @property
    def default_save_path(self) -> Text: ...
    defaultSavePath = default_save_path

class AppAPIMixIn(Request):
    @property
    def app(self) -> Application: ...
    application = app
    def app_version(self, **kwargs: KWARGS) -> str: ...
    def app_web_api_version(self, **kwargs: KWARGS) -> str: ...
    app_webapiVersion = app_web_api_version
    def app_build_info(
        self, **kwargs: KWARGS
    ) -> BuildInfoDictionary[Text, JsonValueT]: ...
    app_buildInfo = app_build_info
    def app_shutdown(self, **kwargs: KWARGS) -> None: ...
    def app_preferences(
        self, **kwargs: KWARGS
    ) -> ApplicationPreferencesDictionary[Text, JsonValueT]: ...
    def app_set_preferences(
        self, prefs: Optional[Mapping[Text, JsonValueT]] = None, **kwargs: KWARGS
    ) -> None: ...
    app_setPreferences = app_set_preferences
    def app_default_save_path(self, **kwargs: KWARGS) -> str: ...
    app_defaultSavePath = app_default_save_path
