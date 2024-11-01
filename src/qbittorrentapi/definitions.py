from __future__ import annotations

from collections import UserList
from collections.abc import Iterable, Mapping, Sequence
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    Union,
)

from qbittorrentapi._attrdict import AttrDict

if TYPE_CHECKING:
    from qbittorrentapi import Request

K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T")

#: Type to define JSON.
JsonValueT = Union[
    None,
    int,
    str,
    bool,
    Sequence["JsonValueT"],
    Mapping[str, "JsonValueT"],
]
#: Type ``Any`` for ``kwargs`` parameters for API methods.
APIKwargsT = Any
#: Type for this API Client.
ClientT = TypeVar("ClientT", bound="Request")
#: Type for entry in List from API.
ListEntryT = TypeVar("ListEntryT", bound="ListEntry")
#: Type for List input to API method.
ListInputT = Iterable[Mapping[str, JsonValueT]]
#: Type for Files input to API method.
FilesToSendT = Mapping[str, Union[bytes, tuple[str, bytes]]]


class APINames(str, Enum):
    """
    API namespaces for API endpoints.

    e.g ``torrents`` in ``http://localhost:8080/api/v2/torrents/addTrackers``
    """

    Authorization = "auth"
    Application = "app"
    Log = "log"
    Sync = "sync"
    Transfer = "transfer"
    Torrents = "torrents"
    TorrentCreator = "torrentcreator"
    RSS = "rss"
    Search = "search"
    EMPTY = ""


class TorrentState(str, Enum):
    """
    Torrent States as defined by qBittorrent.

    Note: In qBittorrent v5.0.0:
     - ``PAUSED_UPLOAD`` was renamed to ``STOPPED_UPLOAD``
     - ``PAUSED_DOWNLOAD`` was renamed to ``STOPPED_DOWNLOAD``

    Definitions:
        - wiki: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-torrent-list>`_
        - code: `<https://github.com/qbittorrent/qBittorrent/blob/8e6515be2c8cc2b335002ab8913e9dcdd7873204/src/base/bittorrent/torrent.h#L79>`_

    :Usage:
        >>> from qbittorrentapi import Client, TorrentState
        >>> client = Client()
        >>> # print torrent hashes for torrents that are downloading
        >>> for torrent in client.torrents_info():
        >>>     # check if torrent is downloading
        >>>     if torrent.state_enum.is_downloading:
        >>>         print(f'{torrent.hash} is downloading...')
        >>>     # the appropriate enum member can be directly derived
        >>>     state_enum = TorrentState(torrent.state)
        >>>     print(f'{torrent.hash}: {state_enum.value}')
    """

    ERROR = "error"
    MISSING_FILES = "missingFiles"
    UPLOADING = "uploading"
    #: ``pausedUP`` was renamed to ``stoppedUP`` in Web API v2.11.0
    PAUSED_UPLOAD = "pausedUP"
    STOPPED_UPLOAD = "stoppedUP"
    QUEUED_UPLOAD = "queuedUP"
    STALLED_UPLOAD = "stalledUP"
    CHECKING_UPLOAD = "checkingUP"
    FORCED_UPLOAD = "forcedUP"
    ALLOCATING = "allocating"
    DOWNLOADING = "downloading"
    METADATA_DOWNLOAD = "metaDL"
    FORCED_METADATA_DOWNLOAD = "forcedMetaDL"
    #: ``pausedDL`` was renamed to ``stoppedDL`` in Web API v2.11.0
    PAUSED_DOWNLOAD = "pausedDL"
    STOPPED_DOWNLOAD = "stoppedDL"
    QUEUED_DOWNLOAD = "queuedDL"
    FORCED_DOWNLOAD = "forcedDL"
    STALLED_DOWNLOAD = "stalledDL"
    CHECKING_DOWNLOAD = "checkingDL"
    CHECKING_RESUME_DATA = "checkingResumeData"
    MOVING = "moving"
    UNKNOWN = "unknown"

    @property
    def is_downloading(self) -> bool:
        """Returns ``True`` if the State is categorized as Downloading."""
        return self in {
            TorrentState.DOWNLOADING,
            TorrentState.METADATA_DOWNLOAD,
            TorrentState.FORCED_METADATA_DOWNLOAD,
            TorrentState.STALLED_DOWNLOAD,
            TorrentState.CHECKING_DOWNLOAD,
            TorrentState.PAUSED_DOWNLOAD,
            TorrentState.STOPPED_DOWNLOAD,
            TorrentState.QUEUED_DOWNLOAD,
            TorrentState.FORCED_DOWNLOAD,
        }

    @property
    def is_uploading(self) -> bool:
        """Returns ``True`` if the State is categorized as Uploading."""
        return self in {
            TorrentState.UPLOADING,
            TorrentState.STALLED_UPLOAD,
            TorrentState.CHECKING_UPLOAD,
            TorrentState.QUEUED_UPLOAD,
            TorrentState.FORCED_UPLOAD,
        }

    @property
    def is_complete(self) -> bool:
        """Returns ``True`` if the State is categorized as Complete."""
        return self in {
            TorrentState.UPLOADING,
            TorrentState.STALLED_UPLOAD,
            TorrentState.CHECKING_UPLOAD,
            TorrentState.PAUSED_UPLOAD,
            TorrentState.STOPPED_UPLOAD,
            TorrentState.QUEUED_UPLOAD,
            TorrentState.FORCED_UPLOAD,
        }

    @property
    def is_checking(self) -> bool:
        """Returns ``True`` if the State is categorized as Checking."""
        return self in {
            TorrentState.CHECKING_UPLOAD,
            TorrentState.CHECKING_DOWNLOAD,
            TorrentState.CHECKING_RESUME_DATA,
        }

    @property
    def is_errored(self) -> bool:
        """Returns ``True`` if the State is categorized as Errored."""
        return self in {TorrentState.MISSING_FILES, TorrentState.ERROR}

    @property
    def is_stopped(self) -> bool:
        """Returns ``True`` if the State is categorized as Stopped."""
        return self in {
            TorrentState.PAUSED_UPLOAD,
            TorrentState.STOPPED_UPLOAD,
            TorrentState.PAUSED_DOWNLOAD,
            TorrentState.STOPPED_DOWNLOAD,
        }

    @property
    def is_paused(self) -> bool:
        """Alias of :any:`TorrentState.is_stopped`"""
        return self.is_stopped


TorrentStates = TorrentState


class TrackerStatus(int, Enum):
    """
    Tracker Statuses as defined by qBittorrent.

    Definitions:
        - wiki: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-torrent-trackers>`_
        - code: `<https://github.com/qbittorrent/qBittorrent/blob/5dcc14153f046209f1067299494a82e5294d883a/src/base/bittorrent/trackerentry.h#L42>`_

    :Usage:
        >>> from qbittorrentapi import Client, TrackerStatus
        >>> client = Client()
        >>> # print torrent hashes for torrents that are downloading
        >>> for torrent in client.torrents_info():
        >>>     for tracker in torrent.trackers:
        >>>         # display status for each tracker
        >>>         print(f"{torrent.hash[-6:]}: {TrackerStatus(tracker.status).display:>13} :{tracker.url}")
    """  # noqa: E501

    DISABLED = 0
    NOT_CONTACTED = 1
    WORKING = 2
    UPDATING = 3
    NOT_WORKING = 4

    @property
    def display(self) -> str:
        """Returns a descriptive display value for status."""
        return {
            TrackerStatus.DISABLED: "Disabled",
            TrackerStatus.NOT_CONTACTED: "Not contacted",
            TrackerStatus.WORKING: "Working",
            TrackerStatus.UPDATING: "Updating",
            TrackerStatus.NOT_WORKING: "Not working",
        }[self]


class ClientCache(Generic[ClientT]):
    """
    Caches the client.

    Subclass this for any object that needs access to the Client.
    """

    def __init__(self, *args: Any, client: ClientT, **kwargs: Any):
        self._client = client
        super().__init__(*args, **kwargs)


class Dictionary(AttrDict[V]):
    """Base definition of dictionary-like objects returned from qBittorrent."""

    def __init__(self, data: Mapping[str, JsonValueT] | None = None, **kwargs: Any):
        super().__init__(self._normalize(data or {}))
        # allows updating properties that aren't necessarily a part of the AttrDict
        self._setattr("_allow_invalid_attributes", True)

    @classmethod
    def _normalize(cls, data: Mapping[str, V] | T) -> AttrDict[V] | T:
        """Iterate through a dict converting any nested dicts to AttrDicts."""
        if isinstance(data, Mapping):
            return AttrDict({key: cls._normalize(value) for key, value in data.items()})
        return data


class List(UserList[ListEntryT]):
    """Base definition for list-like objects returned from qBittorrent."""

    def __init__(
        self,
        list_entries: ListInputT | None = None,
        entry_class: type[ListEntryT] | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            [
                (
                    entry_class(data=entry, **kwargs)  # type: ignore[misc]
                    if entry_class is not None and isinstance(entry, Mapping)
                    else entry
                )
                for entry in list_entries or []
            ]
        )


class ListEntry(Dictionary[JsonValueT]):
    """Base definition for objects within a list returned from qBittorrent."""
