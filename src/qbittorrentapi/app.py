from json import dumps
from logging import getLogger

import six

from qbittorrentapi.auth import AuthAPIMixIn
from qbittorrentapi.decorators import alias
from qbittorrentapi.decorators import aliased
from qbittorrentapi.decorators import endpoint_introduced
from qbittorrentapi.decorators import login_required
from qbittorrentapi.definitions import APINames
from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import Dictionary
from qbittorrentapi.definitions import List
from qbittorrentapi.definitions import ListEntry

logger = getLogger(__name__)


class ApplicationPreferencesDictionary(Dictionary):
    """Response for :meth:`~AppAPIMixIn.app_preferences`"""


class BuildInfoDictionary(Dictionary):
    """Response for :meth:`~AppAPIMixIn.app_build_info`"""


class NetworkInterfaceList(List):
    """Response for :meth:`~AppAPIMixIn.app_network_interface_list`"""

    def __init__(self, list_entries, client=None):
        super(NetworkInterfaceList, self).__init__(
            list_entries, entry_class=NetworkInterface, client=client
        )


class NetworkInterface(ListEntry):
    """Item in :class:`NetworkInterfaceList`"""


class NetworkInterfaceAddressList(List):
    """Response for :meth:`~AppAPIMixIn.app_network_interface_address_list`"""

    def __init__(self, list_entries, client=None):
        super(NetworkInterfaceAddressList, self).__init__(list_entries)


@aliased
class Application(ClientCache):
    """
    Allows interaction with ``Application`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
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
        >>> prefs['web_ui_clickjacking_protection_enabled'] = True
        >>> client.app.preferences = prefs
        >>>
        >>> client.application.shutdown()
    """

    @property
    def version(self):
        """Implements :meth:`~AppAPIMixIn.app_version`"""
        return self._client.app_version()

    @property
    def web_api_version(self):
        """Implements :meth:`~AppAPIMixIn.app_web_api_version`"""
        return self._client.app_web_api_version()

    webapiVersion = web_api_version

    @property
    def build_info(self):
        """Implements :meth:`~AppAPIMixIn.app_build_info`"""
        return self._client.app_build_info()

    buildInfo = build_info

    def shutdown(self):
        """Implements :meth:`~AppAPIMixIn.app_shutdown`"""
        return self._client.app_shutdown()

    @property
    def preferences(self):
        """Implements :meth:`~AppAPIMixIn.app_preferences` and
        :meth:`~AppAPIMixIn.app_set_preferences`"""
        return self._client.app_preferences()

    @preferences.setter
    def preferences(self, value):
        """Implements :meth:`~AppAPIMixIn.app_set_preferences`"""
        self.set_preferences(prefs=value)

    @alias("setPreferences")
    def set_preferences(self, prefs=None, **kwargs):
        """Implements :meth:`~AppAPIMixIn.app_set_preferences`"""
        return self._client.app_set_preferences(prefs=prefs, **kwargs)

    @property
    def default_save_path(self):
        """Implements :meth:`~AppAPIMixIn.app_default_save_path`"""
        return self._client.app_default_save_path()

    defaultSavePath = default_save_path

    @property
    def network_interface_list(self):
        """Implements :meth:`~AppAPIMixIn.app_network_interface_list`"""
        return self._client.app_network_interface_list()

    networkInterfaceList = network_interface_list

    @alias("networkInterfaceAddressList")
    def network_interface_address_list(self, interface_name="", **kwargs):
        """Implements :meth:`~AppAPIMixIn.app_network_interface_list`"""
        return self._client.app_network_interface_address_list(
            interface_name=interface_name, **kwargs
        )


@aliased
class AppAPIMixIn(AuthAPIMixIn):
    """
    Implementation of all ``Application`` API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> client.app_version()
        >>> client.app_preferences()
    """

    @property
    def app(self):
        """
        Allows for transparent interaction with Application endpoints.

        See Application class for usage.
        :return: Application object
        """
        if self._application is None:
            self._application = Application(client=self)
        return self._application

    application = app

    @login_required
    def app_version(self, **kwargs):
        """
        Retrieve application version.

        :return: string
        """
        return self._get(
            _name=APINames.Application,
            _method="version",
            response_class=six.text_type,
            **kwargs
        )

    @alias("app_webapiVersion")
    @login_required
    def app_web_api_version(self, **kwargs):
        """
        Retrieve web API version.

        :return: string
        """
        return self._MOCK_WEB_API_VERSION or self._get(
            _name=APINames.Application,
            _method="webapiVersion",
            response_class=six.text_type,
            **kwargs
        )

    @alias("app_buildInfo")
    @endpoint_introduced("2.3", "app/buildInfo")
    @login_required
    def app_build_info(self, **kwargs):
        """
        Retrieve build info.

        :return: :class:`BuildInfoDictionary` - `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-build-info>`_
        """  # noqa: E501
        return self._get(
            _name=APINames.Application,
            _method="buildInfo",
            response_class=BuildInfoDictionary,
            **kwargs
        )

    @login_required
    def app_shutdown(self, **kwargs):
        """Shutdown qBittorrent."""
        self._post(_name=APINames.Application, _method="shutdown", **kwargs)

    @login_required
    def app_preferences(self, **kwargs):
        """
        Retrieve qBittorrent application preferences.

        :return: :class:`ApplicationPreferencesDictionary` - `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-application-preferences>`_
        """  # noqa: E501
        return self._get(
            _name=APINames.Application,
            _method="preferences",
            response_class=ApplicationPreferencesDictionary,
            **kwargs
        )

    @alias("app_setPreferences")
    @login_required
    def app_set_preferences(self, prefs=None, **kwargs):
        """
        Set one or more preferences in qBittorrent application.

        :param prefs: dictionary of preferences to set
        :return: None
        """
        data = {"json": dumps(prefs, separators=(",", ":"))}
        self._post(
            _name=APINames.Application, _method="setPreferences", data=data, **kwargs
        )

    @alias("app_defaultSavePath")
    @login_required
    def app_default_save_path(self, **kwargs):
        """
        Retrieves the default path for where torrents are saved.

        :return: string
        """
        return self._get(
            _name=APINames.Application,
            _method="defaultSavePath",
            response_class=six.text_type,
            **kwargs
        )

    @alias("app_networkInterfaceList")
    @endpoint_introduced("2.3", "app/networkInterfaceList")
    @login_required
    def app_network_interface_list(self, **kwargs):
        """
        Retrieves the list of network interfaces.

        :return: :class:`NetworkInterfaceList`
        """
        return self._get(
            _name=APINames.Application,
            _method="networkInterfaceList",
            response_class=NetworkInterfaceList,
            **kwargs
        )

    @alias("app_networkInterfaceAddressList")
    @endpoint_introduced("2.3", "app/networkInterfaceAddressList")
    @login_required
    def app_network_interface_address_list(self, interface_name="", **kwargs):
        """
        Retrieves the addresses for a network interface; omit name for all addresses.

        :param interface_name: Name of interface to retrieve addresses for
        :return: :class:`NetworkInterfaceAddressList`
        """
        data = {"iface": interface_name}
        return self._post(
            _name=APINames.Application,
            _method="networkInterfaceAddressList",
            data=data,
            response_class=NetworkInterfaceAddressList,
            **kwargs
        )
