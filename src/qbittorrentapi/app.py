from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from json import dumps
from logging import Logger, getLogger
from typing import Any, AnyStr, Union

from qbittorrentapi.auth import AuthAPIMixIn
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


class Cookie(ListEntry):
    """Item in :class:`CookieList`"""


class CookieList(List[Cookie]):
    """Response for :meth:`~AppAPIMixIn.app_cookies`"""

    def __init__(self, list_entries: ListInputT, client: AppAPIMixIn | None = None):
        super().__init__(list_entries, entry_class=Cookie)


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


class DirectoryContentList(List[str]):  # type: ignore
    """Response for :meth:`~AppAPIMixIn.app_get_directory_content`"""

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
    """  # noqa: E501

    @property
    def app(self) -> Application:
        """
        Allows for transparent interaction with Application endpoints.

        See Application class for usage.
        """
        if self._application is None:
            self._application = Application(client=self)
        return self._application

    @property
    def application(self) -> Application:
        return self.app

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
        prefs: ApplicationPreferencesDictionary | Mapping[str, Any] | None = None,
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

    def app_cookies(self, **kwargs: APIKwargsT) -> CookieList:
        """Retrieve current cookies."""
        return self._get_cast(
            _name=APINames.Application,
            _method="cookies",
            response_class=CookieList,
            version_introduced="2.11.3",
            **kwargs,
        )

    def app_set_cookies(
        self,
        cookies: CookieList | Sequence[Mapping[str, str | int]] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set cookies.

        .. highlight:: python
        .. code-block:: python

            cookies = [
                {
                    'domain': 'example.com',
                    'path': '/example/path',
                    'name': 'cookie name',
                    'value': 'cookie value',
                    'expirationDate': 1729366667,
                },
            ]

        :param cookies: list of cookies to set
        """
        data = {
            # coerce to types that are known to be JSON serializable
            "cookies": dumps(list(map(dict, cookies or ())), separators=(",", ":")),
        }
        self._post(
            _name=APINames.Application,
            _method="setCookies",
            data=data,
            version_introduced="2.11.3",
            **kwargs,
        )

    app_setCookies = app_set_cookies

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

    def app_send_test_email(self) -> None:
        """Sends a test email using the configured email address."""
        self._post(
            _name=APINames.Application,
            _method="sendTestEmail",
            version_introduced="2.10.4",
        )

    app_sendTestEmail = app_send_test_email

    def app_get_directory_content(
        self,
        directory_path: str | os.PathLike[AnyStr] | None = None,
    ) -> DirectoryContentList:
        """
        The contents of a directory file path.

        :raises NotFound404Error: file path not found or not a directory
        :param directory_path: file system path to directory
        """
        data = {
            "dirPath": (
                os.fsdecode(directory_path) if directory_path is not None else None
            )
        }
        return self._post_cast(
            _name=APINames.Application,
            _method="getDirectoryContent",
            data=data,
            response_class=DirectoryContentList,
            version_introduced="2.11",
        )

    app_getDirectoryContent = app_get_directory_content


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
    """  # noqa: E501

    @property
    def version(self) -> str:
        """Implements :meth:`~AppAPIMixIn.app_version`."""
        return self._client.app_version()

    @property
    def web_api_version(self) -> str:
        """Implements :meth:`~AppAPIMixIn.app_web_api_version`."""
        return self._client.app_web_api_version()

    webapiVersion = web_api_version

    @property
    def build_info(self) -> BuildInfoDictionary:
        """Implements :meth:`~AppAPIMixIn.app_build_info`."""
        return self._client.app_build_info()

    buildInfo = build_info

    def shutdown(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~AppAPIMixIn.app_shutdown`."""
        self._client.app_shutdown(**kwargs)

    @property
    def preferences(self) -> ApplicationPreferencesDictionary:
        """Implements :meth:`~AppAPIMixIn.app_preferences`."""
        return self._client.app_preferences()

    @preferences.setter
    def preferences(self, value: Mapping[str, Any]) -> None:
        """Implements :meth:`~AppAPIMixIn.app_set_preferences`."""
        self.set_preferences(prefs=value)

    def set_preferences(
        self,
        prefs: Mapping[str, Any] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~AppAPIMixIn.app_set_preferences`."""
        self._client.app_set_preferences(prefs=prefs, **kwargs)

    setPreferences = set_preferences

    @property
    def default_save_path(self) -> str:
        """Implements :meth:`~AppAPIMixIn.app_default_save_path`."""
        return self._client.app_default_save_path()

    defaultSavePath = default_save_path

    @property
    def cookies(self) -> CookieList:
        """Implements :meth:`~AppAPIMixIn.app_cookies`."""
        return self._client.app_cookies()

    def set_cookies(
        self,
        cookies: CookieList | Sequence[Mapping[str, str | int]] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~AppAPIMixIn.app_set_cookies`."""
        self._client.app_set_cookies(cookies=cookies, **kwargs)

    setCookies = set_cookies

    @property
    def network_interface_list(self) -> NetworkInterfaceList:
        """Implements :meth:`~AppAPIMixIn.app_network_interface_list`."""
        return self._client.app_network_interface_list()

    networkInterfaceList = network_interface_list

    def network_interface_address_list(
        self,
        interface_name: str = "",
        **kwargs: APIKwargsT,
    ) -> NetworkInterfaceAddressList:
        """Implements :meth:`~AppAPIMixIn.app_network_interface_address_list`."""
        return self._client.app_network_interface_address_list(
            interface_name=interface_name,
            **kwargs,
        )

    networkInterfaceAddressList = network_interface_address_list

    def send_test_email(self) -> None:
        """Implements :meth:`~AppAPIMixIn.app_send_test_email`."""
        self._client.app_send_test_email()

    sendTestEmail = send_test_email

    def get_directory_content(
        self,
        directory_path: str | os.PathLike[AnyStr] | None = None,
    ) -> DirectoryContentList:
        """Implements :meth:`~AppAPIMixIn.app_get_directory_content`."""
        return self._client.app_get_directory_content(directory_path=directory_path)

    getDirectoryContent = get_directory_content
