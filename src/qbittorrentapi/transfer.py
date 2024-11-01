from __future__ import annotations

from collections.abc import Iterable

from qbittorrentapi._version_support import v
from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    ClientCache,
    Dictionary,
    JsonValueT,
)


class TransferInfoDictionary(Dictionary[JsonValueT]):
    """
    Response to :meth:`~TransferAPIMixIn.transfer_info`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-global-transfer-info>`_
    """  # noqa: E501


class TransferAPIMixIn(AppAPIMixIn):
    """
    Implementation of all ``Transfer`` API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> transfer_info = client.transfer_info()
        >>> client.transfer_set_download_limit(limit=1024000)
    """  # noqa: E501

    @property
    def transfer(self) -> Transfer:
        """
        Allows for transparent interaction with Transfer endpoints.

        See Transfer class for usage.
        """
        if self._transfer is None:
            self._transfer = Transfer(client=self)
        return self._transfer

    def transfer_info(self, **kwargs: APIKwargsT) -> TransferInfoDictionary:
        """Retrieves the global transfer info found in qBittorrent status bar."""
        return self._get_cast(
            _name=APINames.Transfer,
            _method="info",
            response_class=TransferInfoDictionary,
            **kwargs,
        )

    def transfer_speed_limits_mode(self, **kwargs: APIKwargsT) -> str:
        """Returns ``1`` if alternative speed limits are currently enabled, ``0``
        otherwise."""
        return self._get_cast(
            _name=APINames.Transfer,
            _method="speedLimitsMode",
            response_class=str,
            **kwargs,
        )

    transfer_speedLimitsMode = transfer_speed_limits_mode

    def transfer_set_speed_limits_mode(
        self,
        intended_state: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Sets whether alternative speed limits are enabled.

        :param intended_state: True to enable alt speed and False to disable. Leaving
            None will toggle the current state.
        """
        if (
            intended_state is None
            or v(self.app_web_api_version()) < v("2.8.14")
            and ((self.transfer.speed_limits_mode == "1") is not bool(intended_state))
        ):
            self._post(
                _name=APINames.Transfer,
                _method="toggleSpeedLimitsMode",
                **kwargs,
            )
        else:
            data = {"mode": 1 if intended_state else 0}
            self._post(
                _name=APINames.Transfer,
                _method="setSpeedLimitsMode",
                data=data,
                **kwargs,
            )

    transfer_setSpeedLimitsMode = transfer_set_speed_limits_mode
    transfer_toggleSpeedLimitsMode = transfer_set_speed_limits_mode
    transfer_toggle_speed_limits_mode = transfer_set_speed_limits_mode

    def transfer_download_limit(self, **kwargs: APIKwargsT) -> int:
        """Retrieves download limit; 0 is unlimited."""
        return self._get_cast(
            _name=APINames.Transfer,
            _method="downloadLimit",
            response_class=int,
            **kwargs,
        )

    transfer_downloadLimit = transfer_download_limit

    def transfer_upload_limit(self, **kwargs: APIKwargsT) -> int:
        """Retrieves upload limit; 0 is unlimited."""
        return self._get_cast(
            _name=APINames.Transfer,
            _method="uploadLimit",
            response_class=int,
            **kwargs,
        )

    transfer_uploadLimit = transfer_upload_limit

    def transfer_set_download_limit(
        self,
        limit: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set the global download limit in bytes/second.

        :param limit: download limit in bytes/second (0 or -1 for no limit)
        """
        data = {"limit": limit}
        self._post(
            _name=APINames.Transfer,
            _method="setDownloadLimit",
            data=data,
            **kwargs,
        )

    transfer_setDownloadLimit = transfer_set_download_limit

    def transfer_set_upload_limit(
        self,
        limit: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set the global download limit in bytes/second.

        :param limit: upload limit in bytes/second (0 or -1 for no limit)
        """
        data = {"limit": limit}
        self._post(
            _name=APINames.Transfer,
            _method="setUploadLimit",
            data=data,
            **kwargs,
        )

    transfer_setUploadLimit = transfer_set_upload_limit

    def transfer_ban_peers(
        self,
        peers: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Ban one or more peers.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3.0).

        :param peers: one or more peers to ban. each peer should take the form
            'host:port'
        """
        data = {"peers": self._list2string(peers, "|")}
        self._post(
            _name=APINames.Transfer,
            _method="banPeers",
            data=data,
            version_introduced="2.3",
            **kwargs,
        )

    transfer_banPeers = transfer_ban_peers


class Transfer(ClientCache[TransferAPIMixIn]):
    """
    Allows interaction with the ``Transfer`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # these are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'transfer_' prepended)
        >>> transfer_info = client.transfer.info
        >>> # access and set download/upload limits as attributes
        >>> dl_limit = client.transfer.download_limit
        >>> # this updates qBittorrent in real-time
        >>> client.transfer.download_limit = 1024000
        >>> # update speed limits mode to alternate or not
        >>> client.transfer.speedLimitsMode = True
    """  # noqa: E501

    @property
    def info(self) -> TransferInfoDictionary:
        """Implements :meth:`~TransferAPIMixIn.transfer_info`."""
        return self._client.transfer_info()

    @property
    def speed_limits_mode(self) -> str:
        """Implements :meth:`~TransferAPIMixIn.transfer_speed_limits_mode`."""
        return self._client.transfer_speed_limits_mode()

    @speed_limits_mode.setter
    def speed_limits_mode(self, val: bool) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_speed_limits_mode`."""
        self.set_speed_limits_mode(intended_state=val)

    @property
    def speedLimitsMode(self) -> str:
        """Implements :meth:`~TransferAPIMixIn.transfer_speed_limits_mode`."""
        return self._client.transfer_speed_limits_mode()

    @speedLimitsMode.setter
    def speedLimitsMode(self, val: bool) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_speed_limits_mode`."""
        self.set_speed_limits_mode(intended_state=val)

    def set_speed_limits_mode(
        self,
        intended_state: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_speed_limits_mode`."""
        return self._client.transfer_set_speed_limits_mode(
            intended_state=intended_state,
            **kwargs,
        )

    setSpeedLimitsMode = set_speed_limits_mode
    toggleSpeedLimitsMode = set_speed_limits_mode
    toggle_speed_limits_mode = set_speed_limits_mode

    @property
    def download_limit(self) -> int:
        """Implements :meth:`~TransferAPIMixIn.transfer_download_limit`."""
        return self._client.transfer_download_limit()

    @download_limit.setter
    def download_limit(self, val: int | str) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_download_limit`."""
        self.set_download_limit(limit=val)

    @property
    def downloadLimit(self) -> int:
        """Implements :meth:`~TransferAPIMixIn.transfer_download_limit`."""
        return self._client.transfer_download_limit()

    @downloadLimit.setter
    def downloadLimit(self, val: int | str) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_download_limit`."""
        self.set_download_limit(limit=val)

    @property
    def upload_limit(self) -> int:
        """Implements :meth:`~TransferAPIMixIn.transfer_upload_limit`."""
        return self._client.transfer_upload_limit()

    @upload_limit.setter
    def upload_limit(self, val: int | str) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_upload_limit`."""
        self.set_upload_limit(limit=val)

    @property
    def uploadLimit(self) -> int:
        """Implements :meth:`~TransferAPIMixIn.transfer_upload_limit`."""
        return self._client.transfer_upload_limit()

    @uploadLimit.setter
    def uploadLimit(self, val: int | str) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_upload_limit`."""
        self.set_upload_limit(limit=val)

    def set_download_limit(
        self,
        limit: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_download_limit`."""
        return self._client.transfer_set_download_limit(limit=limit, **kwargs)

    setDownloadLimit = set_download_limit

    def set_upload_limit(
        self,
        limit: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_set_upload_limit`."""
        return self._client.transfer_set_upload_limit(limit=limit, **kwargs)

    setUploadLimit = set_upload_limit

    def ban_peers(
        self,
        peers: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TransferAPIMixIn.transfer_ban_peers`."""
        self._client.transfer_ban_peers(peers=peers, **kwargs)

    banPeers = ban_peers
