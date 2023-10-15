from __future__ import annotations

from functools import wraps
from json import dumps
from logging import Logger
from logging import getLogger
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Union

from qbittorrentapi.auth import AuthAPIMixIn
from qbittorrentapi.definitions import APIKwargsT
from qbittorrentapi.definitions import APINames
from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import Dictionary
from qbittorrentapi.definitions import JsonValueT
from qbittorrentapi.definitions import List
from qbittorrentapi.definitions import ListEntry
from qbittorrentapi.definitions import ListInputT

logger: Logger = getLogger(__name__)


class ApplicationPreferencesDictionary(Dictionary[JsonValueT]):
    """
    Response for :meth:`~AppAPIMixIn.app_preferences`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-application-preferences>`_
    """  # noqa: E501


class BuildInfoDictionary(Dictionary[Union[str, int]]):
    """
    Response for :meth:`~AppAPIMixIn.app_build_info`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-build-info>`_
    """  # noqa: E501


class NetworkInterface(ListEntry):
    """Item in :class:`NetworkInterfaceList`"""


class NetworkInterfaceList(List[NetworkInterface]):
    """Response for :meth:`~AppAPIMixIn.app_network_interface_list`"""

    def __init__(self, list_entries: ListInputT, client: AppAPIMixIn | None = None):
        super().__init__(list_entries, entry_class=NetworkInterface)


# only API response that's a list of strings...so just ignore the typing for now
class NetworkInterfaceAddressList(List[str]):  # type: ignore
    """Response for :meth:`~AppAPIMixIn.app_network_interface_address_list`"""

    def __init__(self, list_entries: Iterable[str], client: AppAPIMixIn | None = None):
        super().__init__(list_entries)  # type: ignore


class AppAPIMixIn(AuthAPIMixIn):
    """
    Implementation of all ``Application`` API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> client.app_version()
        >>> client.app_preferences()
    """

    @property
    def app(self) -> Application:
        """
        Allows for transparent interaction with Application endpoints.

        See Application class for usage.
        """
        if self._application is None:
            self._application = Application(client=self)
        return self._application

    application = app

    def app_version(self, **kwargs: APIKwargsT) -> str:
        """qBittorrent application version."""
        return self._get_cast(
            _name=APINames.Application,
            _method="version",
            response_class=str,
            **kwargs,
        )

    def app_web_api_version(self, **kwargs: APIKwargsT) -> str:
        """qBittorrent Web API version."""
        return self._get_cast(
            _name=APINames.Application,
            _method="webapiVersion",
            response_class=str,
            **kwargs,
        )

    app_webapiVersion = app_web_api_version

    def app_build_info(self, **kwargs: APIKwargsT) -> BuildInfoDictionary:
        """
        qBittorrent build info.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3).
        """
        return self._get_cast(
            _name=APINames.Application,
            _method="buildInfo",
            response_class=BuildInfoDictionary,
            version_introduced="2.3",
            **kwargs,
        )

    app_buildInfo = app_build_info

    def app_shutdown(self, **kwargs: APIKwargsT) -> None:
        """Shutdown qBittorrent."""
        self._post(_name=APINames.Application, _method="shutdown", **kwargs)

    def app_preferences(self, **kwargs: APIKwargsT) -> ApplicationPreferencesDictionary:
        """Retrieve qBittorrent application preferences."""
        return self._get_cast(
            _name=APINames.Application,
            _method="preferences",
            response_class=ApplicationPreferencesDictionary,
            **kwargs,
        )

    def app_set_preferences(
        self,
        prefs: Mapping[str, Any] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set one or more preferences in qBittorrent application.

        :param prefs: dictionary of preferences to set
        """
        data = {"json": dumps(prefs, separators=(",", ":"))}
        self._post(
            _name=APINames.Application,
            _method="setPreferences",
            data=data,
            **kwargs,
        )

    app_setPreferences = app_set_preferences

    def app_default_save_path(self, **kwargs: APIKwargsT) -> str:
        """The default path where torrents are saved."""
        return self._get_cast(
            _name=APINames.Application,
            _method="defaultSavePath",
            response_class=str,
            **kwargs,
        )

    app_defaultSavePath = app_default_save_path

    def app_network_interface_list(self, **kwargs: APIKwargsT) -> NetworkInterfaceList:
        """
        The list of network interfaces on the host.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3).
        """
        return self._get_cast(
            _name=APINames.Application,
            _method="networkInterfaceList",
            response_class=NetworkInterfaceList,
            version_introduced="2.3",
            **kwargs,
        )

    app_networkInterfaceList = app_network_interface_list

    def app_network_interface_address_list(
        self,
        interface_name: str = "",
        **kwargs: APIKwargsT,
    ) -> NetworkInterfaceAddressList:
        """
        The addresses for a network interface; omit name for all addresses.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3).

        :param interface_name: Name of interface to retrieve addresses for
        """
        data = {"iface": interface_name}
        return self._post_cast(
            _name=APINames.Application,
            _method="networkInterfaceAddressList",
            data=data,
            response_class=NetworkInterfaceAddressList,
            version_introduced="2.3",
            **kwargs,
        )

    app_networkInterfaceAddressList = app_network_interface_address_list


class Application(ClientCache[AppAPIMixIn]):
    """
    Allows interaction with ``Application`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # these are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'app_' prepended)
        >>> webapiVersion = client.application.webapiVersion
        >>> web_api_version = client.application.web_api_version
        >>> app_web_api_version = client.application.web_api_version
        >>> # access and set preferences as attributes
        >>> is_dht_enabled = client.application.preferences.dht
        >>> # supports sending a just subset of preferences to update
        >>> client.application.preferences = dict(dht=(not is_dht_enabled))
        >>> prefs = client.application.preferences
        >>> prefs["web_ui_clickjacking_protection_enabled"] = True
        >>> client.app.preferences = prefs
        >>>
        >>> client.application.shutdown()
    """

    @property
    @wraps(AppAPIMixIn.app_version)
    def version(self) -> str:
        return self._client.app_version()

    @property
    @wraps(AppAPIMixIn.app_web_api_version)
    def web_api_version(self) -> str:
        return self._client.app_web_api_version()

    webapiVersion = web_api_version

    @property
    @wraps(AppAPIMixIn.app_build_info)
    def build_info(self) -> BuildInfoDictionary:
        return self._client.app_build_info()

    buildInfo = build_info

    @wraps(AppAPIMixIn.app_shutdown)
    def shutdown(self, **kwargs: APIKwargsT) -> None:
        self._client.app_shutdown(**kwargs)

    @property
    @wraps(AppAPIMixIn.app_preferences)
    def preferences(self) -> ApplicationPreferencesDictionary:
        return self._client.app_preferences()

    @preferences.setter
    @wraps(AppAPIMixIn.app_set_preferences)
    def preferences(self, value: Mapping[str, Any]) -> None:
        self.set_preferences(prefs=value)

    @wraps(AppAPIMixIn.app_set_preferences)
    def set_preferences(
        self,
        prefs: Mapping[str, Any] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        self._client.app_set_preferences(prefs=prefs, **kwargs)

    setPreferences = set_preferences

    @property
    @wraps(AppAPIMixIn.app_default_save_path)
    def default_save_path(self) -> str:
        return self._client.app_default_save_path()

    defaultSavePath = default_save_path

    @property
    @wraps(AppAPIMixIn.app_network_interface_list)
    def network_interface_list(self) -> NetworkInterfaceList:
        return self._client.app_network_interface_list()

    networkInterfaceList = network_interface_list

    @wraps(AppAPIMixIn.app_network_interface_address_list)
    def network_interface_address_list(
        self,
        interface_name: str = "",
        **kwargs: APIKwargsT,
    ) -> NetworkInterfaceAddressList:
        return self._client.app_network_interface_address_list(
            interface_name=interface_name,
            **kwargs,
        )

    networkInterfaceAddressList = network_interface_address_list
