from __future__ import annotations

from typing import cast

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    ClientCache,
    Dictionary,
    JsonValueT,
)


class SyncMainDataDictionary(Dictionary[JsonValueT]):
    """
    Response for :meth:`~SyncAPIMixIn.sync_maindata`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-main-data>`_
    """  # noqa: E501


class SyncTorrentPeersDictionary(Dictionary[JsonValueT]):
    """
    Response for :meth:`~SyncAPIMixIn.sync_torrent_peers`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-torrent-peers-data>`_
    """  # noqa: E501


class SyncAPIMixIn(AppAPIMixIn):
    """
    Implementation of all ``Sync`` API Methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> maindata = client.sync_maindata(rid="...")
        >>> torrent_peers = client.sync_torrent_peers(torrent_hash="...", rid="...")
    """  # noqa: E501

    @property
    def sync(self) -> Sync:
        """
        Allows for transparent interaction with ``Sync`` endpoints.

        See Sync class for usage.
        """
        if self._sync is None:
            self._sync = Sync(client=self)
        return self._sync

    def sync_maindata(
        self,
        rid: str | int = 0,
        **kwargs: APIKwargsT,
    ) -> SyncMainDataDictionary:
        """
        Retrieves sync data.

        :param rid: response ID
        """
        data = {"rid": rid}
        return self._post_cast(
            _name=APINames.Sync,
            _method="maindata",
            data=data,
            response_class=SyncMainDataDictionary,
            **kwargs,
        )

    def sync_torrent_peers(
        self,
        torrent_hash: str | None = None,
        rid: str | int = 0,
        **kwargs: APIKwargsT,
    ) -> SyncTorrentPeersDictionary:
        """
        Retrieves torrent sync data.

        :raises NotFound404Error:

        :param torrent_hash: hash for torrent
        :param rid: response ID
        """
        data = {"hash": torrent_hash, "rid": rid}
        return self._post_cast(
            _name=APINames.Sync,
            _method="torrentPeers",
            data=data,
            response_class=SyncTorrentPeersDictionary,
            **kwargs,
        )

    sync_torrentPeers = sync_torrent_peers


class Sync(ClientCache[SyncAPIMixIn]):
    """
    Allows interaction with the ``Sync`` API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # these are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'sync_' prepended)
        >>> maindata = client.sync.maindata(rid="...")
        >>> # for use when continuously calling maindata for changes in torrents
        >>> # this will automatically request the changes since the last call
        >>> md = client.sync.maindata.delta()
        >>> #
        >>> torrentPeers = client.sync.torrentPeers(torrent_hash="...", rid="...")
        >>> torrent_peers = client.sync.torrent_peers(torrent_hash="...", rid="...")
    """  # noqa: E501

    def __init__(self, client: SyncAPIMixIn) -> None:
        super().__init__(client=client)
        self._maindata = self.MainData(client=client)
        self._torrent_peers = self.TorrentPeers(client=client)

    class MainData(ClientCache[SyncAPIMixIn]):
        def __init__(self, client: SyncAPIMixIn) -> None:
            super().__init__(client=client)
            self._rid: int = 0

        def __call__(
            self,
            rid: str | int = 0,
            **kwargs: APIKwargsT,
        ) -> SyncMainDataDictionary:
            return self._client.sync_maindata(rid=rid, **kwargs)

        def delta(self, **kwargs: APIKwargsT) -> SyncMainDataDictionary:
            """Implements :meth:`~SyncAPIMixIn.sync_maindata` to return updates since
            last call."""
            md = self._client.sync_maindata(rid=self._rid, **kwargs)
            self._rid = cast(int, md.get("rid", 0))
            return md

        def reset_rid(self) -> None:
            """Resets RID so the next request includes everything."""
            self._rid = 0

    class TorrentPeers(ClientCache["SyncAPIMixIn"]):
        def __init__(self, client: SyncAPIMixIn) -> None:
            super().__init__(client=client)
            self._rid: int = 0

        def __call__(
            self,
            torrent_hash: str | None = None,
            rid: str | int = 0,
            **kwargs: APIKwargsT,
        ) -> SyncTorrentPeersDictionary:
            """Implements :meth:`~SyncAPIMixIn.sync_torrent_peers`."""
            return self._client.sync_torrent_peers(
                torrent_hash=torrent_hash,
                rid=rid,
                **kwargs,
            )

        def delta(
            self,
            torrent_hash: str | None = None,
            **kwargs: APIKwargsT,
        ) -> SyncTorrentPeersDictionary:
            """Implements :meth:`~SyncAPIMixIn.sync_torrent_peers` to return updates
            since last call."""
            torrent_peers = self._client.sync_torrent_peers(
                torrent_hash=torrent_hash,
                rid=self._rid,
                **kwargs,
            )
            self._rid = cast(int, torrent_peers.get("rid", 0))
            return torrent_peers

        def reset_rid(self) -> None:
            """Resets RID so the next request includes everything."""
            self._rid = 0

    @property
    def maindata(self) -> Sync.MainData:
        """Implements :meth:`~SyncAPIMixIn.sync_maindata`."""
        return self._maindata

    @property
    def torrent_peers(self) -> Sync.TorrentPeers:
        """Implements :meth:`~SyncAPIMixIn.sync_torrent_peers`."""
        return self._torrent_peers

    torrentPeers = torrent_peers
