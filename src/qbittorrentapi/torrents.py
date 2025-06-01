from __future__ import annotations

import errno
from collections.abc import Iterable, Mapping, MutableMapping
from logging import Logger, getLogger
from os import path
from os import strerror as os_strerror
from typing import (
    IO,
    Any,
    Callable,
    Literal,
    TypeVar,
    Union,
    cast,
)

from qbittorrentapi._version_support import v
from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    ClientCache,
    Dictionary,
    FilesToSendT,
    JsonValueT,
    List,
    ListEntry,
    ListInputT,
    TorrentState,
)
from qbittorrentapi.exceptions import (
    TorrentFileError,
    TorrentFileNotFoundError,
    TorrentFilePermissionError,
)

#: Type for Torrent Status.
TorrentStatusesT = Literal[
    "all",
    "downloading",
    "seeding",
    "completed",
    "paused",
    "stopped",  # replaced paused in v5.0.0
    "active",
    "inactive",
    "resumed",
    "running",  # replaced resumed in v5.0.0
    "stalled",
    "stalled_uploading",
    "stalled_downloading",
    "checking",
    "moving",
    "errored",
]

#: Type for input of files to API method.
TorrentFilesT = TypeVar(
    "TorrentFilesT",
    bytes,
    str,
    IO[bytes],
    Mapping[str, Union[bytes, str, IO[bytes]]],
    Iterable[Union[bytes, str, IO[bytes]]],
)

logger: Logger = getLogger(__name__)


class TorrentPropertiesDictionary(Dictionary[JsonValueT]):
    """
    Response to :meth:`~TorrentsAPIMixIn.torrents_properties`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-torrent-generic-properties>`_
    """  # noqa: E501


class TorrentLimitsDictionary(Dictionary[JsonValueT]):
    """Response to :meth:`~TorrentsAPIMixIn.torrents_download_limit`"""


class TorrentCategoriesDictionary(Dictionary[JsonValueT]):
    """Response to :meth:`~TorrentsAPIMixIn.torrents_categories`"""


class TorrentsAddPeersDictionary(Dictionary[JsonValueT]):
    """Response to :meth:`~TorrentsAPIMixIn.torrents_add_peers`"""


class TorrentFile(ListEntry):
    """Item in :class:`TorrentFilesList`"""


class TorrentFilesList(List[TorrentFile]):
    """
    Response to :meth:`~TorrentsAPIMixIn.torrents_files`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-torrent-contents>`_
    """  # noqa: E501

    def __init__(
        self,
        list_entries: ListInputT,
        client: TorrentsAPIMixIn | None = None,
    ):
        super().__init__(list_entries, entry_class=TorrentFile, client=client)
        # until v4.3.5, the index key wasn't returned...default it to ID for older
        # versions. when index is returned, maintain backwards compatibility and
        # populate id with index value.
        for i, entry in enumerate(self):
            entry.update({"id": entry.setdefault("index", i)})


class WebSeed(ListEntry):
    """Item in :class:`WebSeedsList`"""


class WebSeedsList(List[WebSeed]):
    """
    Response to :meth:`~TorrentsAPIMixIn.torrents_webseeds`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-torrent-web-seeds>`_
    """  # noqa: E501

    def __init__(
        self,
        list_entries: ListInputT,
        client: TorrentsAPIMixIn | None = None,
    ):
        super().__init__(list_entries, entry_class=WebSeed, client=client)


class Tracker(ListEntry):
    """Item in :class:`TrackersList`"""


class TrackersList(List[Tracker]):
    """
    Response to :meth:`~TorrentsAPIMixIn.torrents_trackers`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-torrent-trackers>`_
    """  # noqa: E501

    def __init__(
        self,
        list_entries: ListInputT,
        client: TorrentsAPIMixIn | None = None,
    ):
        super().__init__(list_entries, entry_class=Tracker, client=client)


class TorrentInfoList(List["TorrentDictionary"]):
    """
    Response to :meth:`~TorrentsAPIMixIn.torrents_info`

    Definition: `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-torrent-list>`_
    """  # noqa: E501

    def __init__(
        self,
        list_entries: ListInputT,
        client: TorrentsAPIMixIn | None = None,
    ):
        super().__init__(list_entries, entry_class=TorrentDictionary, client=client)


class TorrentPieceData(ListEntry):
    """Item in :class:`TorrentPieceInfoList`"""


class TorrentPieceInfoList(List[TorrentPieceData]):
    """Response to :meth:`~TorrentsAPIMixIn.torrents_piece_states` and
    :meth:`~TorrentsAPIMixIn.torrents_piece_hashes`"""

    def __init__(
        self,
        list_entries: ListInputT,
        client: TorrentsAPIMixIn | None = None,
    ):
        super().__init__(list_entries, entry_class=TorrentPieceData, client=client)


class Tag(ListEntry):
    """Item in :class:`TagList`"""


class TagList(List[Tag]):
    """Response to :meth:`~TorrentsAPIMixIn.torrents_tags`"""

    def __init__(
        self,
        list_entries: ListInputT,
        client: TorrentsAPIMixIn | None = None,
    ):
        super().__init__(list_entries, entry_class=Tag, client=client)


class TorrentsAPIMixIn(AppAPIMixIn):
    """
    Implementation of all Torrents API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> client.torrents_add(urls="...")
        >>> client.torrents_reannounce()
    """  # noqa: E501

    @property
    def torrents(self) -> Torrents:
        """
        Allows for transparent interaction with Torrents endpoints.

        See Torrents and Torrent class for usage.
        """
        if self._torrents is None:
            self._torrents = Torrents(client=self)
        return self._torrents

    @property
    def torrent_categories(self) -> TorrentCategories:
        """
        Allows for transparent interaction with Torrent Categories endpoints.

        See Torrent_Categories class for usage.
        """
        if self._torrent_categories is None:
            self._torrent_categories = TorrentCategories(client=self)
        return self._torrent_categories

    @property
    def torrent_tags(self) -> TorrentTags:
        """
        Allows for transparent interaction with Torrent Tags endpoints.

        See Torrent_Tags class for usage.
        """
        if self._torrent_tags is None:
            self._torrent_tags = TorrentTags(client=self)
        return self._torrent_tags

    def torrents_add(
        self,
        urls: str | Iterable[str] | None = None,
        torrent_files: TorrentFilesT | None = None,
        save_path: str | None = None,
        cookie: str | None = None,
        category: str | None = None,
        is_skip_checking: bool | None = None,
        is_paused: bool | None = None,
        is_root_folder: bool | None = None,
        rename: str | None = None,
        upload_limit: str | int | None = None,
        download_limit: str | int | None = None,
        use_auto_torrent_management: bool | None = None,
        is_sequential_download: bool | None = None,
        is_first_last_piece_priority: bool | None = None,
        tags: str | Iterable[str] | None = None,
        content_layout: Literal["Original", "Subfolder", "NoSubfolder"] | None = None,
        ratio_limit: str | float | None = None,
        seeding_time_limit: str | int | None = None,
        download_path: str | None = None,
        use_download_path: bool | None = None,
        stop_condition: Literal["MetadataReceived", "FilesChecked"] | None = None,
        add_to_top_of_queue: bool | None = None,
        inactive_seeding_time_limit: str | int | None = None,
        share_limit_action: Literal[
            "Stop", "Remove", "RemoveWithContent", "EnableSuperSeeding"
        ]
        | None = None,
        ssl_certificate: str | None = None,
        ssl_private_key: str | None = None,
        ssl_dh_params: str | None = None,
        is_stopped: bool | None = None,
        forced: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> str:
        """
        Add one or more torrents by URLs and/or torrent files.

        Returns ``Ok.`` for success and ``Fails.`` for failure.

        :raises UnsupportedMediaType415Error: if file is not a valid torrent file
        :raises TorrentFileNotFoundError: if a torrent file doesn't exist
        :raises TorrentFilePermissionError: if read permission is denied to torrent file

        :param urls: single instance or an iterable of URLs (``http://``, ``https://``,
            ``magnet:``, ``bc://bt/``)
        :param torrent_files: several options are available to send torrent files to
            qBittorrent:

            * single instance of bytes: useful if torrent file already read from disk or
              downloaded from internet.
            * single instance of file handle to torrent file: use ``open(<filepath>, 'rb')``
              to open the torrent file.
            * single instance of a filepath to torrent file: e.g.
              ``/home/user/torrent_filename.torrent``
            * an iterable of the single instances above to send more than one torrent file
            * dictionary with key/value pairs of torrent name and single instance of above
              object

            Note: The torrent name in a dictionary is useful to identify which torrent file
            errored. qBittorrent provides back that name in the error text. If a torrent
            name is not provided, then the name of the file will be used. And in the case of
            bytes (or if filename cannot be determined), the value 'torrent__n' will be used.
        :param save_path: location to save the torrent data
        :param cookie: cookie(s) to retrieve torrents by URL
        :param category: category to assign to torrent(s)
        :param is_skip_checking: ``True`` to skip hash checking
        :param is_paused: Adds torrent in stopped state; alias for ``is_stopped``
        :param is_root_folder: ``True`` or ``False`` to create root folder (superseded by
            content_layout with v4.3.2)
        :param rename: new name for torrent(s)
        :param upload_limit: upload limit in bytes/second
        :param download_limit: download limit in bytes/second
        :param use_auto_torrent_management: ``True`` or ``False`` to use automatic torrent
            management
        :param is_sequential_download: ``True`` or ``False`` for sequential download
        :param is_first_last_piece_priority: ``True`` or ``False`` for first and last piece
            download priority
        :param tags: tag(s) to assign to torrent(s) (added in Web API v2.6.2)
        :param content_layout: ``Original``, ``Subfolder``, or ``NoSubfolder`` to control
            filesystem structure for content (added in Web API v2.7)
        :param ratio_limit: share limit as ratio of upload amt over download amt; e.g. 0.5
            or 2.0 (added in Web API v2.8.1)
        :param seeding_time_limit: number of minutes to seed torrent (added in Web API v2.8.1)
        :param download_path: location to download torrent content before moving to
            ``save_path`` (added in Web API v2.8.4)
        :param use_download_path: ``True`` or ``False`` whether ``download_path`` should
            be used...defaults to ``True`` if ``download_path`` is specified (added in
            Web API v2.8.4)
        :param stop_condition: ``MetadataReceived`` or ``FilesChecked`` to stop the
            torrent when started automatically (added in Web API v2.8.15)
        :param add_to_top_of_queue: puts torrent at top to the queue(added in Web API v2.8.19)
        :param inactive_seeding_time_limit: limit for seeding while inactive (added in
            Web API v2.9.2)
        :param share_limit_action: override default action when share limit is reached
            (added in Web API v2.10.4)
        :param ssl_certificate: peer certificate (in PEM format) (added in Web API v2.10.4)
        :param ssl_private_key: peer private key (added in Web API v2.10.4)
        :param ssl_dh_params: Diffie-Hellman parameters (added in Web API v2.10.4)
        :param is_stopped: Adds torrent in stopped state; alias for ``is_paused`` (added
            in Web API v2.11.0)
        :param forced: add torrent in forced state (added in Web API v2.11.0)
        """  # noqa: E501

        # convert pre-v2.7 params to post-v2.7 params...or post-v2.7 to pre-v2.7
        api_version = v(self.app_web_api_version())
        if (
            content_layout is None
            and is_root_folder is not None
            and api_version >= v("2.7")
        ):
            content_layout = "Original" if is_root_folder else "NoSubfolder"
            is_root_folder = None
        elif (
            content_layout is not None
            and is_root_folder is None
            and api_version < v("2.7")
        ):
            is_root_folder = content_layout in {"Subfolder", "Original"}
            content_layout = None

        # default to actually using the specified download path
        if use_download_path is None and download_path is not None:
            use_download_path = True

        is_stopped = (
            is_paused or is_stopped if (is_paused, is_stopped) != (None, None) else None
        )

        data = {
            "urls": (None, self._list2string(urls, "\n")),
            "cookie": (None, cookie),
            "rename": (None, rename),
            "category": (None, category),
            "tags": (None, self._list2string(tags, ",")),
            "savepath": (None, save_path),
            "useDownloadPath": (None, use_download_path),
            "downloadPath": (None, download_path),
            "sequentialDownload": (None, is_sequential_download),
            "firstLastPiecePrio": (None, is_first_last_piece_priority),
            "addToTopOfQueue": (None, add_to_top_of_queue),
            # paused renamed to stopped in v5.0.0
            "paused": (None, is_stopped),
            "stopped": (None, is_stopped),
            "stopCondition": (None, stop_condition),
            "skip_checking": (None, is_skip_checking),
            "root_folder": (None, is_root_folder),
            "contentLayout": (None, content_layout),
            "autoTMM": (None, use_auto_torrent_management),
            "upLimit": (None, upload_limit),
            "dlLimit": (None, download_limit),
            "seedingTimeLimit": (None, seeding_time_limit),
            "inactiveSeedingTimeLimit": (None, inactive_seeding_time_limit),
            "ratioLimit": (None, ratio_limit),
            "shareLimitAction": (None, share_limit_action),
            "ssl_certificate": (None, ssl_certificate),
            "ssl_private_key": (None, ssl_private_key),
            "ssl_dh_params": (None, ssl_dh_params),
            "forced": (None, forced),
        }

        return self._post_cast(
            _name=APINames.Torrents,
            _method="add",
            data=data,
            files=self._normalize_torrent_files(torrent_files),
            response_class=str,
            **kwargs,
        )

    @staticmethod
    def _normalize_torrent_files(
        user_files: TorrentFilesT | None,
    ) -> FilesToSendT | None:
        """
        Normalize the torrent file(s) from the user.

        The file(s) can be the raw bytes, file handle, filepath for a
        torrent file, or an iterable (e.g. list|set|tuple) of any of
        these "files". Further, the file(s) can be in a dictionary with
        the "names" of the torrents as the keys. These "names" can be
        anything...but are mostly useful as identifiers for each file.
        """
        if not user_files:
            return None

        prefix = "torrent__"
        # if it's string-like and not a list|set|tuple, then make it a list.
        # checking for 'read' attribute since a single file handle is iterable
        # but also needs to be in a list
        is_string_like = isinstance(user_files, (bytes, str))
        is_file_like = hasattr(user_files, "read")
        if is_string_like or is_file_like or not isinstance(user_files, Iterable):
            user_files = [user_files]  # type: ignore[assignment,list-item]

        # up convert to a dictionary to add fabricated torrent names
        norm_files = (
            user_files
            if isinstance(user_files, Mapping)
            else {f"{prefix}{i}": f for i, f in enumerate(user_files)}
        )

        files = {}
        for name, torrent_file in norm_files.items():
            try:
                if isinstance(torrent_file, (bytes, bytearray)):
                    # if bytes, assume it's a downloaded file or read from disk
                    torrent_bytes = torrent_file
                elif hasattr(torrent_file, "read"):
                    # assume this is a file handle from open() or similar
                    torrent_bytes = torrent_file.read()
                else:
                    # otherwise, coerce to a string and try to open it as a file
                    filepath = path.abspath(
                        path.realpath(path.expanduser(str(torrent_file)))
                    )
                    name = path.basename(filepath)
                    with open(filepath, "rb") as file:
                        torrent_bytes = file.read()

                # if using default name, let Requests try to figure out the filename
                # to send. Requests will fall back to "name" as the dict key if fh
                # doesn't provide a file name.
                files[name] = (
                    torrent_bytes if name.startswith(prefix) else (name, torrent_bytes)
                )
            except OSError as io_err:
                if io_err.errno == errno.ENOENT:
                    raise TorrentFileNotFoundError(
                        errno.ENOENT, os_strerror(errno.ENOENT), torrent_file
                    )
                if io_err.errno == errno.EACCES:
                    raise TorrentFilePermissionError(
                        errno.ENOENT, os_strerror(errno.EACCES), torrent_file
                    )
                raise TorrentFileError(io_err)
        return files  # type: ignore[return-value]

    def torrents_count(self) -> int:
        """Retrieve count of torrents."""
        return self._post_cast(
            _name=APINames.Torrents,
            _method="count",
            response_class=int,
            version_introduced="2.9.3",
        )

    ##########################################################################
    # INDIVIDUAL TORRENT ENDPOINTS
    ##########################################################################
    def torrents_properties(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentPropertiesDictionary:
        """
        Retrieve individual torrent's properties.

        :raises NotFound404Error:

        :param torrent_hash: hash for torrent
        """
        data = {"hash": torrent_hash}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="properties",
            data=data,
            response_class=TorrentPropertiesDictionary,
            **kwargs,
        )

    def torrents_trackers(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TrackersList:
        """
        Retrieve individual torrent's trackers. Tracker status is defined in
        :class:`~qbittorrentapi.definitions.TrackerStatus`.

        :raises NotFound404Error:

        :param torrent_hash: hash for torrent
        """
        data = {"hash": torrent_hash}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="trackers",
            data=data,
            response_class=TrackersList,
            **kwargs,
        )

    def torrents_webseeds(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> WebSeedsList:
        """
        Retrieve individual torrent's web seeds.

        :raises NotFound404Error: torrent not found
        :param torrent_hash: hash for torrent
        """
        data = {"hash": torrent_hash}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="webseeds",
            data=data,
            response_class=WebSeedsList,
            **kwargs,
        )

    def torrents_add_webseeds(
        self,
        torrent_hash: str | None = None,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Add webseeds to a torrent.

        :raises NotFound404Error: torrent not found
        :raises InvalidRequest400Error: invalid URL
        :param torrent_hash: hash for torrent
        :param urls: list of webseed URLs to add to torrent
        """
        data = {
            "hash": torrent_hash,
            "urls": self._list2string(urls, "|"),
        }
        self._post(
            _name=APINames.Torrents,
            _method="addWebSeeds",
            data=data,
            version_introduced="2.11.3",
            **kwargs,
        )

    torrents_addWebSeeds = torrents_add_webseeds

    def torrents_edit_webseed(
        self,
        torrent_hash: str | None = None,
        orig_url: str | None = None,
        new_url: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Edit a webseed for a torrent.

        :raises NotFound404Error: torrent not found
        :raises Conflict409Error: ``orig_url`` is not a webseed for the torrent
        :raises InvalidRequest400Error: invalid URL
        :param torrent_hash: hash for torrent
        :param orig_url: webseed URL to be replaced
        :param new_url: webseed URL to replace with
        """
        data = {
            "hash": torrent_hash,
            "origUrl": orig_url,
            "newUrl": new_url,
        }
        self._post(
            _name=APINames.Torrents,
            _method="editWebSeed",
            data=data,
            version_introduced="2.11.3",
            **kwargs,
        )

    torrents_editWebSeed = torrents_edit_webseed

    def torrents_remove_webseeds(
        self,
        torrent_hash: str | None = None,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Remove webseeds from a torrent.

        :raises NotFound404Error:
        :raises InvalidRequest400Error: invalid URL
        :param torrent_hash: hash for torrent
        :param urls: list of webseed URLs to add to torrent
        """
        data = {
            "hash": torrent_hash,
            "urls": self._list2string(urls, "|"),
        }
        self._post(
            _name=APINames.Torrents,
            _method="removeWebSeeds",
            data=data,
            version_introduced="2.11.3",
            **kwargs,
        )

    torrents_removeWebSeeds = torrents_remove_webseeds

    def torrents_files(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentFilesList:
        """
        Retrieve individual torrent's files.

        :raises NotFound404Error:

        :param torrent_hash: hash for torrent
        """
        data = {"hash": torrent_hash}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="files",
            data=data,
            response_class=TorrentFilesList,
            **kwargs,
        )

    def torrents_piece_states(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentPieceInfoList:
        """
        Retrieve individual torrent's pieces' states.

        :raises NotFound404Error:

        :param torrent_hash: hash for torrent
        """
        data = {"hash": torrent_hash}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="pieceStates",
            data=data,
            response_class=TorrentPieceInfoList,
            **kwargs,
        )

    torrents_pieceStates = torrents_piece_states

    def torrents_piece_hashes(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentPieceInfoList:
        """
        Retrieve individual torrent's pieces' hashes.

        :raises NotFound404Error:

        :param torrent_hash: hash for torrent
        """
        data = {"hash": torrent_hash}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="pieceHashes",
            data=data,
            response_class=TorrentPieceInfoList,
            **kwargs,
        )

    torrents_pieceHashes = torrents_piece_hashes

    def torrents_add_trackers(
        self,
        torrent_hash: str | None = None,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Add trackers to a torrent.

        :raises NotFound404Error:
        :param torrent_hash: hash for torrent
        :param urls: tracker URLs to add to torrent
        """
        data = {
            "hash": torrent_hash,
            "urls": self._list2string(urls, "\n"),
        }
        self._post(_name=APINames.Torrents, _method="addTrackers", data=data, **kwargs)

    torrents_addTrackers = torrents_add_trackers

    def torrents_edit_tracker(
        self,
        torrent_hash: str | None = None,
        original_url: str | None = None,
        new_url: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Replace a torrent's tracker with a different one.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.2.0).

        :raises InvalidRequest400Error:
        :raises NotFound404Error:
        :raises Conflict409Error:
        :param torrent_hash: hash for torrent
        :param original_url: URL for existing tracker
        :param new_url: new URL to replace
        """
        data = {
            "hash": torrent_hash,
            "origUrl": original_url,
            "newUrl": new_url,
        }
        self._post(
            _name=APINames.Torrents,
            _method="editTracker",
            data=data,
            version_introduced="2.2.0",
            **kwargs,
        )

    torrents_editTracker = torrents_edit_tracker

    def torrents_remove_trackers(
        self,
        torrent_hash: str | None = None,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Remove trackers from a torrent.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.2.0).

        :raises NotFound404Error:
        :raises Conflict409Error:
        :param torrent_hash: hash for torrent
        :param urls: tracker URLs to removed from torrent
        """
        data = {
            "hash": torrent_hash,
            "urls": self._list2string(urls, "|"),
        }
        self._post(
            _name=APINames.Torrents,
            _method="removeTrackers",
            data=data,
            version_introduced="2.2.0",
            **kwargs,
        )

    torrents_removeTrackers = torrents_remove_trackers

    def torrents_file_priority(
        self,
        torrent_hash: str | None = None,
        file_ids: str | int | Iterable[str | int] | None = None,
        priority: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set priority for one or more files.

        :raises InvalidRequest400Error: if priority is invalid or at least one file ID is
            not an integer
        :raises NotFound404Error:
        :raises Conflict409Error: if torrent metadata has not finished downloading or at
            least one file was not found
        :param torrent_hash: hash for torrent
        :param file_ids: single file ID or a list.
        :param priority: priority for file(s) -
            `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-set-file-priority>`_
        """  # noqa: E501
        data = {
            "hash": torrent_hash,
            "id": self._list2string(file_ids, "|"),
            "priority": priority,
        }
        self._post(_name=APINames.Torrents, _method="filePrio", data=data, **kwargs)

    torrents_filePrio = torrents_file_priority

    def torrents_rename(
        self,
        torrent_hash: str | None = None,
        new_torrent_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Rename a torrent.

        :raises NotFound404Error:
        :param torrent_hash: hash for torrent
        :param new_torrent_name: new name for torrent
        """
        data = {"hash": torrent_hash, "name": new_torrent_name}
        self._post(_name=APINames.Torrents, _method="rename", data=data, **kwargs)

    def torrents_rename_file(
        self,
        torrent_hash: str | None = None,
        file_id: str | int | None = None,
        new_file_name: str | None = None,
        old_path: str | None = None,
        new_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Rename a torrent file.

        This method was introduced with qBittorrent v4.2.1 (Web API v2.4.0).

        :raises MissingRequiredParameters400Error:
        :raises NotFound404Error:
        :raises Conflict409Error:
        :param torrent_hash: hash for torrent
        :param file_id: id for file (removed in Web API v2.7)
        :param new_file_name: new name for file (removed in Web API v2.7)
        :param old_path: path of file to rename (added in Web API v2.7)
        :param new_path: new path of file to rename (added in Web API v2.7)
        """
        # convert pre-v2.7 params to post-v2.7...or post-v2.7 to pre-v2.7
        # HACK: v4.3.2 and v4.3.3 both use Web API v2.7 but old/new_path
        #       were introduced in v4.3.3
        if (
            old_path is None
            and new_path is None
            and file_id is not None
            and v(self.app_version()) >= v("v4.3.3")
        ):
            try:
                old_path = self.torrents_files(torrent_hash=torrent_hash)[file_id].name  # type: ignore[index]
            except (IndexError, AttributeError, TypeError):
                logger.debug(
                    "ERROR: File ID '%s' isn't valid...'oldPath' cannot be determined.",
                    file_id,
                )
                old_path = ""
            new_path = new_file_name or ""
        elif (
            old_path is not None
            and new_path is not None
            and file_id is None
            and v(self.app_version()) < v("v4.3.3")
        ):
            # previous only allowed renaming the file...not also moving it
            new_file_name = new_path.split("/")[-1]
            for file in self.torrents_files(torrent_hash=torrent_hash):
                if file.name == old_path:
                    file_id = file.id
                    break
            else:
                logger.debug(
                    "ERROR: old_path '%s' isn't valid..."
                    "'file_id' cannot be determined.",
                    old_path,
                )
                file_id = ""

        data = {
            "hash": torrent_hash,
            "id": file_id,
            "name": new_file_name,
            "oldPath": old_path,
            "newPath": new_path,
        }
        self._post(
            _name=APINames.Torrents,
            _method="renameFile",
            data=data,
            version_introduced="2.4.0",
            **kwargs,
        )

    torrents_renameFile = torrents_rename_file

    def torrents_rename_folder(
        self,
        torrent_hash: str | None = None,
        old_path: str | None = None,
        new_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Rename a torrent folder.

        This method was introduced with qBittorrent v4.3.2 (Web API v2.7).

        :raises MissingRequiredParameters400Error:
        :raises NotFound404Error:
        :raises Conflict409Error:
        :param torrent_hash: hash for torrent
        :param old_path: path of file to rename (added in Web API v2.7)
        :param new_path: new path of file to rename (added in Web API v2.7)
        """
        # HACK: v4.3.2 and v4.3.3 both use Web API v2.7 but rename_folder
        #       was introduced in v4.3.3
        if v(self.app_version()) >= v("v4.3.3"):
            data = {
                "hash": torrent_hash,
                "oldPath": old_path,
                "newPath": new_path,
            }
            self._post(
                _name=APINames.Torrents,
                _method="renameFolder",
                data=data,
                version_introduced="2.7",
                **kwargs,
            )
        else:
            # only get here on v4.3.2...so hack in raising exception
            if self._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS:
                raise NotImplementedError(
                    "ERROR: Endpoint 'torrents/renameFolder' is Not Implemented in "
                    "this version of qBittorrent. "
                    "This endpoint is available starting in Web API v2.7."
                )

    torrents_renameFolder = torrents_rename_folder

    def torrents_export(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> bytes:
        """
        Export a .torrent file for the torrent.

        This method was introduced with qBittorrent v4.5.0 (Web API v2.8.14).

        :raises NotFound404Error: torrent not found
        :raises Conflict409Error: unable to export .torrent file
        :param torrent_hash: hash for torrent
        """
        data = {"hash": torrent_hash}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="export",
            data=data,
            response_class=bytes,
            version_introduced="2.8.14",
            **kwargs,
        )

    ##########################################################################
    # MULTIPLE TORRENT ENDPOINTS
    ##########################################################################
    def torrents_info(
        self,
        status_filter: TorrentStatusesT | None = None,
        category: str | None = None,
        sort: str | None = None,
        reverse: bool | None = None,
        limit: str | int | None = None,
        offset: str | int | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        tag: str | None = None,
        private: bool | None = None,
        include_trackers: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentInfoList:
        """
        Retrieves list of info for torrents.

        :param status_filter: Filter list by torrent status:

            * Original options: ``all``, ``downloading``, ``seeding``, ``completed``,
              ``paused``, ``active``, ``inactive``, ``resumed``, ``errored``
            * Added in Web API v2.4.1: ``stalled``, ``stalled_uploading``, and
              ``stalled_downloading``
            * Added in Web API v2.8.4: ``checking``
            * Added in Web API v2.8.18: ``moving``
            * Added in Web API v2.11.0: ``stopped`` (replaced ``paused``), ``running``
              (replaced ``resumed``)
        :param category: Filter list by category
        :param sort: Sort list by any property returned
        :param reverse: Reverse sorting
        :param limit: Limit length of list
        :param offset: Start of list (if < 0, offset from end of list)
        :param torrent_hashes: Filter list by hash (separate multiple hashes with a '|')
            (added in Web API v2.0.1)
        :param tag: Filter list by tag (empty string means "untagged"; no "tag" parameter
            means "any tag"; added in Web API v2.8.3)
        :param private: Filter list by private flag - use None to ignore; (added in
            Web API v2.11.1)
        :param include_trackers: Include trackers in response; default False; (added in
            Web API v2.11.4)
        """  # noqa: E501
        # convert filter for pre- and post-v2.11.0
        if status_filter in {"stopped", "paused", "running", "resumed"}:
            is_post_2_11 = v(self.app_web_api_version()) >= v("2.11.0")
            status_filter = {
                ("stopped", False): "paused",
                ("paused", True): "stopped",
                ("running", False): "resumed",
                ("resumed", True): "running",
            }.get((status_filter, is_post_2_11), status_filter)  # type:ignore[assignment]

        data = {
            "filter": status_filter,
            "category": category,
            "sort": sort,
            "reverse": None if reverse is None else bool(reverse),
            "limit": limit,
            "offset": offset,
            "hashes": self._list2string(torrent_hashes, "|"),
            "tag": tag,
            "private": None if private is None else bool(private),
            "includeTrackers": (
                None if include_trackers is None else bool(include_trackers)
            ),
        }
        return self._post_cast(
            _name=APINames.Torrents,
            _method="info",
            data=data,
            response_class=TorrentInfoList,
            **kwargs,
        )

    def torrents_start(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Start one or more torrents in qBittorrent.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        # resume renamed to start in v5.0.0
        method = "start" if v(self.app_web_api_version()) >= v("2.11.0") else "resume"
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(_name=APINames.Torrents, _method=method, data=data, **kwargs)

    torrents_resume = torrents_start

    def torrents_stop(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Stop one or more torrents in qBittorrent.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        # pause renamed to stop in v5.0.0
        method = "stop" if v(self.app_web_api_version()) >= v("2.11.0") else "pause"
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(_name=APINames.Torrents, _method=method, data=data, **kwargs)

    torrents_pause = torrents_stop

    def torrents_delete(
        self,
        delete_files: bool | None = False,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Remove a torrent from qBittorrent and optionally delete its files.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param delete_files: True to delete the torrent's files
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "deleteFiles": bool(delete_files),
        }
        self._post(_name=APINames.Torrents, _method="delete", data=data, **kwargs)

    def torrents_recheck(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Recheck a torrent in qBittorrent.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(_name=APINames.Torrents, _method="recheck", data=data, **kwargs)

    def torrents_reannounce(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Reannounce a torrent.

        This method was introduced with qBittorrent v4.1.2 (Web API v2.0.2).

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(
            _name=APINames.Torrents,
            _method="reannounce",
            data=data,
            version_introduced="2.0.2",
            **kwargs,
        )

    def torrents_increase_priority(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Increase the priority of a torrent. Torrent Queuing must be enabled.

        :raises Conflict409Error:

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(_name=APINames.Torrents, _method="increasePrio", data=data, **kwargs)

    torrents_increasePrio = torrents_increase_priority

    def torrents_decrease_priority(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Decrease the priority of a torrent. Torrent Queuing must be enabled.

        :raises Conflict409Error:

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(_name=APINames.Torrents, _method="decreasePrio", data=data, **kwargs)

    torrents_decreasePrio = torrents_decrease_priority

    def torrents_top_priority(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set torrent as highest priority. Torrent Queuing must be enabled.

        :raises Conflict409Error:

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(_name=APINames.Torrents, _method="topPrio", data=data, **kwargs)

    torrents_topPrio = torrents_top_priority

    def torrents_bottom_priority(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set torrent as lowest priority. Torrent Queuing must be enabled.

        :raises Conflict409Error:

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(_name=APINames.Torrents, _method="bottomPrio", data=data, **kwargs)

    torrents_bottomPrio = torrents_bottom_priority

    def torrents_download_limit(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentLimitsDictionary:
        """Retrieve the download limit for one or more torrents."""
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="downloadLimit",
            data=data,
            response_class=TorrentLimitsDictionary,
            **kwargs,
        )

    torrents_downloadLimit = torrents_download_limit

    def torrents_set_download_limit(
        self,
        limit: str | int | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set the download limit for one or more torrents.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param limit: bytes/second (-1 sets the limit to infinity)
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "limit": limit,
        }
        self._post(
            _name=APINames.Torrents,
            _method="setDownloadLimit",
            data=data,
            **kwargs,
        )

    torrents_setDownloadLimit = torrents_set_download_limit

    def torrents_set_share_limits(
        self,
        ratio_limit: str | int | None = None,
        seeding_time_limit: str | int | None = None,
        inactive_seeding_time_limit: str | int | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set share limits for one or more torrents.

        This method was introduced with qBittorrent v4.1.1 (Web API v2.0.1).

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param ratio_limit: max ratio to seed a torrent.
            (-2 means use the global value and -1 is no limit)
        :param seeding_time_limit: minutes
            (-2 means use the global value and -1 is no limit)
        :param inactive_seeding_time_limit: minutes
            (-2 means use the global value and -1 is no limit)
            (added in Web API v2.9.2)
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "ratioLimit": ratio_limit,
            "seedingTimeLimit": seeding_time_limit,
            "inactiveSeedingTimeLimit": inactive_seeding_time_limit,
        }
        self._post(
            _name=APINames.Torrents,
            _method="setShareLimits",
            data=data,
            version_introduced="2.0.1",
            **kwargs,
        )

    torrents_setShareLimits = torrents_set_share_limits

    def torrents_upload_limit(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentLimitsDictionary:
        """
        Retrieve the upload limit for one or more torrents.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        return self._post_cast(
            _name=APINames.Torrents,
            _method="uploadLimit",
            data=data,
            response_class=TorrentLimitsDictionary,
            **kwargs,
        )

    torrents_uploadLimit = torrents_upload_limit

    def torrents_set_upload_limit(
        self,
        limit: str | int | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set the upload limit for one or more torrents.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param limit: bytes/second (-1 sets the limit to infinity)
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "limit": limit,
        }
        self._post(
            _name=APINames.Torrents,
            _method="setUploadLimit",
            data=data,
            **kwargs,
        )

    torrents_setUploadLimit = torrents_set_upload_limit

    def torrents_set_location(
        self,
        location: str | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set location for torrents' files.

        :raises Forbidden403Error: if the user doesn't have permissions to write to the
            location (only before v4.5.2 - write check was removed.)
        :raises Conflict409Error: if the directory cannot be created at the location

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param location: disk location to move torrent's files
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "location": location,
        }
        self._post(_name=APINames.Torrents, _method="setLocation", data=data, **kwargs)

    torrents_setLocation = torrents_set_location

    def torrents_set_save_path(
        self,
        save_path: str | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set the Save Path for one or more torrents.

        This method was introduced with qBittorrent v4.4.0 (Web API v2.8.4).

        :raises Forbidden403Error: cannot write to directory
        :raises Conflict409Error: cannot create directory

        :param save_path: file path to save torrent contents
        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {
            "id": self._list2string(torrent_hashes, "|"),
            "path": save_path,
        }
        self._post(
            _name=APINames.Torrents,
            _method="setSavePath",
            data=data,
            version_introduced="2.8.4",
            **kwargs,
        )

    torrents_setSavePath = torrents_set_save_path

    def torrents_set_download_path(
        self,
        download_path: str | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set the Download Path for one or more torrents.

        This method was introduced with qBittorrent v4.4.0 (Web API v2.8.4).

        :raises Forbidden403Error: cannot write to directory
        :raises Conflict409Error: cannot create directory

        :param download_path: file path to save torrent contents before torrent
            finishes downloading
        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {
            "id": self._list2string(torrent_hashes, "|"),
            "path": download_path,
        }
        self._post(
            _name=APINames.Torrents,
            _method="setDownloadPath",
            data=data,
            version_introduced="2.8.4",
            **kwargs,
        )

    torrents_setDownloadPath = torrents_set_download_path

    def torrents_set_category(
        self,
        category: str | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set a category for one or more torrents.

        :raises Conflict409Error: for bad category

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param category: category to assign to torrent
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "category": category,
        }
        self._post(_name=APINames.Torrents, _method="setCategory", data=data, **kwargs)

    torrents_setCategory = torrents_set_category

    def torrents_set_auto_management(
        self,
        enable: bool | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Enable or disable automatic torrent management for one or more torrents.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param enable: Defaults to ``True`` if ``None`` or unset;
            use ``False`` to disable
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "enable": True if enable is None else bool(enable),
        }
        self._post(
            _name=APINames.Torrents,
            _method="setAutoManagement",
            data=data,
            **kwargs,
        )

    torrents_setAutoManagement = torrents_set_auto_management

    def torrents_toggle_sequential_download(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Toggle sequential download for one or more torrents.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes)}
        self._post(
            _name=APINames.Torrents,
            _method="toggleSequentialDownload",
            data=data,
            **kwargs,
        )

    torrents_toggleSequentialDownload = torrents_toggle_sequential_download

    def torrents_toggle_first_last_piece_priority(
        self,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Toggle priority of first/last piece downloading.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {"hashes": self._list2string(torrent_hashes, "|")}
        self._post(
            _name=APINames.Torrents,
            _method="toggleFirstLastPiecePrio",
            data=data,
            **kwargs,
        )

    torrents_toggleFirstLastPiecePrio = torrents_toggle_first_last_piece_priority

    def torrents_set_force_start(
        self,
        enable: bool | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Force start one or more torrents.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param enable: Defaults to ``True`` if ``None`` or unset; ``False`` is
            equivalent to :meth:`~TorrentsAPIMixIn.torrents_resume()`.
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "value": True if enable is None else bool(enable),
        }
        self._post(
            _name=APINames.Torrents,
            _method="setForceStart",
            data=data,
            **kwargs,
        )

    torrents_setForceStart = torrents_set_force_start

    def torrents_set_super_seeding(
        self,
        enable: bool | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Set one or more torrents as super seeding.

        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        :param enable: Defaults to ``True`` if ``None`` or unset; ``False`` to disable
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "value": True if enable is None else bool(enable),
        }
        self._post(
            _name=APINames.Torrents,
            _method="setSuperSeeding",
            data=data,
            **kwargs,
        )

    torrents_setSuperSeeding = torrents_set_super_seeding

    def torrents_add_peers(
        self,
        peers: str | Iterable[str] | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentsAddPeersDictionary:
        """
        Add one or more peers to one or more torrents.

        This method was introduced with qBittorrent v4.4.0 (Web API v2.3.0).

        :raises InvalidRequest400Error: for invalid peers

        :param peers: one or more peers to add. each peer should take the form
            'host:port'
        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "peers": self._list2string(peers, "|"),
        }
        return self._post_cast(
            _name=APINames.Torrents,
            _method="addPeers",
            data=data,
            response_class=TorrentsAddPeersDictionary,
            version_introduced="2.3.0",
            **kwargs,
        )

    torrents_addPeers = torrents_add_peers

    # TORRENT CATEGORIES ENDPOINTS
    def torrents_categories(self, **kwargs: APIKwargsT) -> TorrentCategoriesDictionary:
        """
        Retrieve all category definitions.

        This method was introduced with qBittorrent v4.1.4 (Web API v2.1.1).

        Note: ``torrents/categories`` is not available until v2.1.0
        """
        return self._get_cast(
            _name=APINames.Torrents,
            _method="categories",
            response_class=TorrentCategoriesDictionary,
            version_introduced="2.1.1",
            **kwargs,
        )

    def torrents_create_category(
        self,
        name: str | None = None,
        save_path: str | None = None,
        download_path: str | None = None,
        enable_download_path: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Create a new torrent category.

        :raises Conflict409Error: if category name is not valid or unable to create
        :param name: name for new category
        :param save_path: location to save torrents for this category (added in Web API
            2.1.0)
        :param download_path: download location for torrents with this category
        :param enable_download_path: True or False to enable or disable download path
        """
        # default to actually using the specified download path
        if enable_download_path is None and download_path is not None:
            enable_download_path = True

        data = {
            "category": name,
            "savePath": save_path,
            "downloadPath": download_path,
            "downloadPathEnabled": enable_download_path,
        }
        self._post(
            _name=APINames.Torrents,
            _method="createCategory",
            data=data,
            **kwargs,
        )

    torrents_createCategory = torrents_create_category

    def torrents_edit_category(
        self,
        name: str | None = None,
        save_path: str | None = None,
        download_path: str | None = None,
        enable_download_path: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Edit an existing category.

        This method was introduced with qBittorrent v4.1.3 (Web API v2.1.0).

        :raises Conflict409Error: if category name is not valid or unable to create
        :param name: category to edit
        :param save_path: new location to save files for this category
        :param download_path: download location for torrents with this category
        :param enable_download_path: True or False to enable or disable download path
        """

        # default to actually using the specified download path
        if enable_download_path is None and download_path is not None:
            enable_download_path = True

        data = {
            "category": name,
            "savePath": save_path,
            "downloadPath": download_path,
            "downloadPathEnabled": enable_download_path,
        }
        self._post(
            _name=APINames.Torrents,
            _method="editCategory",
            data=data,
            version_introduced="2.1.0",
            **kwargs,
        )

    torrents_editCategory = torrents_edit_category

    def torrents_remove_categories(
        self,
        categories: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Delete one or more categories.

        :param categories: categories to delete
        """
        data = {"categories": self._list2string(categories, "\n")}
        self._post(
            _name=APINames.Torrents,
            _method="removeCategories",
            data=data,
            **kwargs,
        )

    torrents_removeCategories = torrents_remove_categories

    # TORRENT TAGS ENDPOINTS
    def torrents_tags(self, **kwargs: APIKwargsT) -> TagList:
        """
        Retrieve all tag definitions.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3.0).
        """
        return self._get_cast(
            _name=APINames.Torrents,
            _method="tags",
            response_class=TagList,
            version_introduced="2.3.0",
            **kwargs,
        )

    def torrents_add_tags(
        self,
        tags: str | Iterable[str] | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Add one or more tags to one or more torrents.

        Note: Tags that do not exist will be created on-the-fly.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3.0).

        :param tags: tag name or list of tags
        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "tags": self._list2string(tags, ","),
        }
        self._post(
            _name=APINames.Torrents,
            _method="addTags",
            data=data,
            version_introduced="2.3.0",
            **kwargs,
        )

    torrents_addTags = torrents_add_tags

    def torrents_set_tags(
        self,
        tags: str | Iterable[str] | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Upsert one or more tags to one or more torrents.

        Note: Tags that do not exist will be created on-the-fly.

        This method was introduced with qBittorrent v5.1.0 (Web API v2.11.4).

        :param tags: tag name or list of tags
        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "tags": self._list2string(tags, ","),
        }
        self._post(
            _name=APINames.Torrents,
            _method="setTags",
            data=data,
            version_introduced="2.11.4",
            **kwargs,
        )

    torrents_setTags = torrents_set_tags

    def torrents_remove_tags(
        self,
        tags: str | Iterable[str] | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Add one or more tags to one or more torrents.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3.0).

        :param tags: tag name or list of tags
        :param torrent_hashes: single torrent hash or list of torrent hashes.
            Or ``all`` for all torrents.
        """
        data = {
            "hashes": self._list2string(torrent_hashes, "|"),
            "tags": self._list2string(tags, ","),
        }
        self._post(
            _name=APINames.Torrents,
            _method="removeTags",
            data=data,
            version_introduced="2.3.0",
            **kwargs,
        )

    torrents_removeTags = torrents_remove_tags

    def torrents_create_tags(
        self,
        tags: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Create one or more tags.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3.0).

        :param tags: tag name or list of tags
        """
        data = {"tags": self._list2string(tags, ",")}
        self._post(
            _name=APINames.Torrents,
            _method="createTags",
            data=data,
            version_introduced="2.3.0",
            **kwargs,
        )

    torrents_createTags = torrents_create_tags

    def torrents_delete_tags(
        self,
        tags: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Delete one or more tags.

        This method was introduced with qBittorrent v4.2.0 (Web API v2.3.0).

        :param tags: tag name or list of tags
        """
        data = {"tags": self._list2string(tags, ",")}
        self._post(
            _name=APINames.Torrents,
            _method="deleteTags",
            data=data,
            version_introduced="2.3.0",
            **kwargs,
        )

    torrents_deleteTags = torrents_delete_tags


class TorrentDictionary(ClientCache[TorrentsAPIMixIn], ListEntry):
    """
    Item in :class:`TorrentInfoList`. Allows interaction with individual torrents via
    the ``Torrents`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # these are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'transfer_' prepended)
        >>> torrent = client.torrents.info()[0]
        >>> torrent_hash = torrent.info.hash
        >>> # Attributes without inputs and a return value are properties
        >>> properties = torrent.properties
        >>> trackers = torrent.trackers
        >>> files = torrent.files
        >>> # Action methods
        >>> torrent.edit_tracker(original_url="...", new_url="...")
        >>> torrent.remove_trackers(urls="http://127.0.0.2/")
        >>> torrent.rename(new_torrent_name="...")
        >>> torrent.start()
        >>> torrent.stop()
        >>> torrent.recheck()
        >>> torrent.torrents_top_priority()
        >>> torrent.setLocation(location="/home/user/torrents/")
        >>> torrent.setCategory(category="video")
    """  # noqa: E501

    def __init__(
        self,
        data: MutableMapping[str, JsonValueT],
        client: TorrentsAPIMixIn,
    ) -> None:
        self._torrent_hash: str | None = cast(str, data.get("hash", None))
        # The attribute for "# of secs til the next announce" was added in v5.0.0.
        # To avoid clashing with `reannounce()`, rename to `reannounce_in`.
        if "reannounce" in data:
            data["reannounce_in"] = data.pop("reannounce")
        super().__init__(client=client, data=data)

    def sync_local(self) -> None:
        """Update local cache of torrent info."""
        for name, value in self.info.items():
            setattr(self, name, value)

    @property
    def state_enum(self) -> TorrentState:
        """Torrent state enum."""
        try:
            return TorrentState(self.state)
        except ValueError:
            return TorrentState.UNKNOWN

    @property
    def info(self) -> TorrentDictionary:
        """Returns data from :meth:`~TorrentsAPIMixIn.torrents_info` for the torrent."""
        info = self._client.torrents_info(torrent_hashes=self._torrent_hash)
        if len(info) == 1 and info[0].hash == self._torrent_hash:
            return info[0]

        # qBittorrent v4.1.0 didn't support torrent hash parameter
        info = [t for t in self._client.torrents_info() if t.hash == self._torrent_hash]  # type: ignore[assignment]
        if len(info) == 1:
            return info[0]

        return TorrentDictionary(data={}, client=self._client)

    def start(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_start`."""
        self._client.torrents_start(torrent_hashes=self._torrent_hash, **kwargs)

    resume = start

    def stop(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_stop`."""
        self._client.torrents_stop(torrent_hashes=self._torrent_hash, **kwargs)

    pause = stop

    def delete(
        self,
        delete_files: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_delete`."""
        self._client.torrents_delete(
            delete_files=delete_files,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    def recheck(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_recheck`."""
        self._client.torrents_recheck(torrent_hashes=self._torrent_hash, **kwargs)

    def reannounce(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_reannounce`."""
        self._client.torrents_reannounce(torrent_hashes=self._torrent_hash, **kwargs)

    def increase_priority(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_increase_priority`."""
        self._client.torrents_increase_priority(
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    increasePrio = increase_priority

    def decrease_priority(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_decrease_priority`."""
        self._client.torrents_decrease_priority(
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    decreasePrio = decrease_priority

    def top_priority(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_top_priority`."""
        self._client.torrents_top_priority(torrent_hashes=self._torrent_hash, **kwargs)

    topPrio = top_priority

    def bottom_priority(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_bottom_priority`."""
        self._client.torrents_bottom_priority(
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    bottomPrio = bottom_priority

    def set_share_limits(
        self,
        ratio_limit: str | int | None = None,
        seeding_time_limit: str | int | None = None,
        inactive_seeding_time_limit: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_share_limits`."""
        self._client.torrents_set_share_limits(
            ratio_limit=ratio_limit,
            seeding_time_limit=seeding_time_limit,
            inactive_seeding_time_limit=inactive_seeding_time_limit,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setShareLimits = set_share_limits

    @property
    def download_limit(self) -> int:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_download_limit`."""
        return cast(
            int,
            self._client.torrents_download_limit(torrent_hashes=self._torrent_hash).get(
                self._torrent_hash or ""
            ),
        )

    @download_limit.setter
    def download_limit(self, val: str | int) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_download_limit`."""
        self.set_download_limit(limit=val)

    @property
    def downloadLimit(self) -> int:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_download_limit`."""
        return cast(
            int,
            self._client.torrents_download_limit(torrent_hashes=self._torrent_hash).get(
                self._torrent_hash or ""
            ),
        )

    @downloadLimit.setter
    def downloadLimit(self, val: str | int) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_download_limit`."""
        self.set_download_limit(limit=val)

    def set_download_limit(
        self,
        limit: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_download_limit`."""
        self._client.torrents_set_download_limit(
            limit=limit,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setDownloadLimit = set_download_limit

    @property
    def upload_limit(self) -> int:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_upload_limit`."""
        return cast(
            int,
            self._client.torrents_upload_limit(torrent_hashes=self._torrent_hash).get(
                self._torrent_hash or ""
            ),
        )

    @upload_limit.setter
    def upload_limit(self, val: str | int) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_upload_limit`."""
        self.set_upload_limit(limit=val)

    @property
    def uploadLimit(self) -> int:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_upload_limit`."""
        return cast(
            int,
            self._client.torrents_upload_limit(torrent_hashes=self._torrent_hash).get(
                self._torrent_hash or ""
            ),
        )

    @uploadLimit.setter
    def uploadLimit(self, val: str | int) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_upload_limit`."""
        self.set_upload_limit(limit=val)

    def set_upload_limit(
        self,
        limit: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_upload_limit`."""
        self._client.torrents_set_upload_limit(
            limit=limit,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setUploadLimit = set_upload_limit

    def set_location(
        self,
        location: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_location`."""
        self._client.torrents_set_location(
            location=location,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setLocation = set_location

    def set_save_path(
        self,
        save_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_save_path`."""
        self._client.torrents_set_save_path(
            save_path=save_path,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setSavePath = set_save_path

    def set_download_path(
        self,
        download_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_download_path`."""
        self._client.torrents_set_download_path(
            download_path=download_path,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setDownloadPath = set_download_path

    def set_category(
        self,
        category: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_category`."""
        self._client.torrents_set_category(
            category=category,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setCategory = set_category

    def set_auto_management(
        self,
        enable: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_auto_management`."""
        self._client.torrents_set_auto_management(
            enable=enable,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setAutoManagement = set_auto_management

    def toggle_sequential_download(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_toggle_sequential_download`."""
        self._client.torrents_toggle_sequential_download(
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    toggleSequentialDownload = toggle_sequential_download

    def toggle_first_last_piece_priority(self, **kwargs: APIKwargsT) -> None:
        """Implements
        :meth:`~TorrentsAPIMixIn.torrents_toggle_first_last_piece_priority`."""
        self._client.torrents_toggle_first_last_piece_priority(
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    toggleFirstLastPiecePrio = toggle_first_last_piece_priority

    def set_force_start(
        self,
        enable: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_force_start`."""
        self._client.torrents_set_force_start(
            enable=enable,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setForceStart = set_force_start

    def set_super_seeding(
        self,
        enable: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_super_seeding`."""
        self._client.torrents_set_super_seeding(
            enable=enable,
            torrent_hashes=self._torrent_hash,
            **kwargs,
        )

    setSuperSeeding = set_super_seeding

    @property
    def properties(self) -> TorrentPropertiesDictionary:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_properties`."""
        return self._client.torrents_properties(torrent_hash=self._torrent_hash)

    @property
    def trackers(self) -> TrackersList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_trackers`."""
        return self._client.torrents_trackers(torrent_hash=self._torrent_hash)

    @trackers.setter
    def trackers(self, val: Iterable[str]) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_add_trackers`."""
        self.add_trackers(urls=val)

    @property
    def webseeds(self) -> WebSeedsList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_webseeds`."""
        return self._client.torrents_webseeds(torrent_hash=self._torrent_hash)

    def add_webseeds(
        self,
        urls: str | Iterable[str] | None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_add_webseeds`."""
        self._client.torrents_add_webseeds(
            torrent_hash=self._torrent_hash,
            urls=urls,
            **kwargs,
        )

    addWebSeeds = add_webseeds

    def edit_webseed(
        self,
        orig_url: str | None = None,
        new_url: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_edit_webseed`."""
        self._client.torrents_edit_webseed(
            torrent_hash=self._torrent_hash,
            orig_url=orig_url,
            new_url=new_url,
            **kwargs,
        )

    editWebSeed = edit_webseed

    def remove_webseeds(
        self,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_remove_webseeds`."""
        self._client.torrents_remove_webseeds(
            torrent_hash=self._torrent_hash,
            urls=urls,
            **kwargs,
        )

    removeWebSeeds = remove_webseeds

    @property
    def files(self) -> TorrentFilesList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_files`."""
        return self._client.torrents_files(torrent_hash=self._torrent_hash)

    def rename_file(
        self,
        file_id: str | int | None = None,
        new_file_name: str | None = None,
        old_path: str | None = None,
        new_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_rename_file`."""
        self._client.torrents_rename_file(
            torrent_hash=self._torrent_hash,
            file_id=file_id,
            new_file_name=new_file_name,
            old_path=old_path,
            new_path=new_path,
            **kwargs,
        )

    renameFile = rename_file

    def rename_folder(
        self,
        old_path: str | None = None,
        new_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_rename_folder`."""
        self._client.torrents_rename_folder(
            torrent_hash=self._torrent_hash,
            old_path=old_path,
            new_path=new_path,
            **kwargs,
        )

    renameFolder = rename_folder

    @property
    def piece_states(self) -> TorrentPieceInfoList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_piece_states`."""
        return self._client.torrents_piece_states(torrent_hash=self._torrent_hash)

    pieceStates = piece_states

    @property
    def piece_hashes(self) -> TorrentPieceInfoList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_piece_hashes`."""
        return self._client.torrents_piece_hashes(torrent_hash=self._torrent_hash)

    pieceHashes = piece_hashes

    def add_trackers(
        self,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_add_trackers`."""
        self._client.torrents_add_trackers(
            torrent_hash=self._torrent_hash,
            urls=urls,
            **kwargs,
        )

    addTrackers = add_trackers

    def edit_tracker(
        self,
        orig_url: str | None = None,
        new_url: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_edit_tracker`."""
        self._client.torrents_edit_tracker(
            torrent_hash=self._torrent_hash,
            original_url=orig_url,
            new_url=new_url,
            **kwargs,
        )

    editTracker = edit_tracker

    def remove_trackers(
        self,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_remove_trackers`."""
        self._client.torrents_remove_trackers(
            torrent_hash=self._torrent_hash,
            urls=urls,
            **kwargs,
        )

    removeTrackers = remove_trackers

    def file_priority(
        self,
        file_ids: str | int | Iterable[str | int] | None = None,
        priority: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_file_priority`."""
        self._client.torrents_file_priority(
            torrent_hash=self._torrent_hash,
            file_ids=file_ids,
            priority=priority,
            **kwargs,
        )

    filePriority = file_priority

    def rename(self, new_name: str | None = None, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_rename`."""
        self._client.torrents_rename(
            torrent_hash=self._torrent_hash,
            new_torrent_name=new_name,
            **kwargs,
        )

    def add_tags(
        self,
        tags: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_add_tags`."""
        self._client.torrents_add_tags(
            torrent_hashes=self._torrent_hash,
            tags=tags,
            **kwargs,
        )

    addTags = add_tags

    def set_tags(
        self,
        tags: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_tags`."""
        self._client.torrents_set_tags(
            torrent_hashes=self._torrent_hash,
            tags=tags,
            **kwargs,
        )

    setTags = set_tags

    def remove_tags(
        self,
        tags: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_remove_tags`."""
        self._client.torrents_remove_tags(
            torrent_hashes=self._torrent_hash,
            tags=tags,
            **kwargs,
        )

    removeTags = remove_tags

    def export(self, **kwargs: APIKwargsT) -> bytes:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_export`."""
        return self._client.torrents_export(torrent_hash=self._torrent_hash, **kwargs)


class Torrents(ClientCache[TorrentsAPIMixIn]):
    """
    Allows interaction with the ``Torrents`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # these are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'torrents_' prepended)
        >>> torrent_list = client.torrents.info()
        >>> torrent_list_active = client.torrents.info.active()
        >>> torrent_list_active_partial = client.torrents.info.active(limit=100, offset=200)
        >>> torrent_list_downloading = client.torrents.info.downloading()
        >>> # torrent looping
        >>> for torrent in client.torrents.info.completed()
        >>> # all torrents endpoints with a 'hashes' parameters support all method to apply action to all torrents
        >>> client.torrents.stop.all()
        >>> client.torrents.start.all()
        >>> # or specify the individual hashes
        >>> client.torrents.downloadLimit(torrent_hashes=["...", "..."])
    """  # noqa: E501

    def __init__(self, client: TorrentsAPIMixIn) -> None:
        super().__init__(client=client)
        self.info = self._Info(client=client)
        self.start = self._ActionForAllTorrents(
            client=client, func=client.torrents_start
        )
        self.resume = self.start
        self.stop = self._ActionForAllTorrents(client=client, func=client.torrents_stop)
        self.pause = self.stop
        self.delete = self._ActionForAllTorrents(
            client=client, func=client.torrents_delete
        )
        self.recheck = self._ActionForAllTorrents(
            client=client, func=client.torrents_recheck
        )
        self.reannounce = self._ActionForAllTorrents(
            client=client, func=client.torrents_reannounce
        )
        self.increase_priority = self._ActionForAllTorrents(
            client=client, func=client.torrents_increase_priority
        )
        self.increasePrio = self.increase_priority
        self.decrease_priority = self._ActionForAllTorrents(
            client=client, func=client.torrents_decrease_priority
        )
        self.decreasePrio = self.decrease_priority
        self.top_priority = self._ActionForAllTorrents(
            client=client, func=client.torrents_top_priority
        )
        self.topPrio = self.top_priority
        self.bottom_priority = self._ActionForAllTorrents(
            client=client, func=client.torrents_bottom_priority
        )
        self.bottomPrio = self.bottom_priority
        self.download_limit = self._ActionForAllTorrents(
            client=client, func=client.torrents_download_limit
        )
        self.downloadLimit = self.download_limit
        self.upload_limit = self._ActionForAllTorrents(
            client=client, func=client.torrents_upload_limit
        )
        self.uploadLimit = self.upload_limit
        self.set_download_limit = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_download_limit
        )
        self.setDownloadLimit = self.set_download_limit
        self.set_share_limits = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_share_limits
        )
        self.setShareLimits = self.set_share_limits
        self.set_upload_limit = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_upload_limit
        )
        self.setUploadLimit = self.set_upload_limit
        self.set_location = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_location
        )
        self.set_save_path = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_save_path
        )
        self.setSavePath = self.set_save_path
        self.set_download_path = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_download_path
        )
        self.setDownloadPath = self.set_download_path
        self.setLocation = self.set_location
        self.set_category = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_category
        )
        self.setCategory = self.set_category
        self.set_auto_management = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_auto_management
        )
        self.setAutoManagement = self.set_auto_management
        self.toggle_sequential_download = self._ActionForAllTorrents(
            client=client, func=client.torrents_toggle_sequential_download
        )
        self.toggleSequentialDownload = self.toggle_sequential_download
        self.toggle_first_last_piece_priority = self._ActionForAllTorrents(
            client=client, func=client.torrents_toggle_first_last_piece_priority
        )
        self.toggleFirstLastPiecePrio = self.toggle_first_last_piece_priority
        self.set_force_start = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_force_start
        )
        self.setForceStart = self.set_force_start
        self.set_super_seeding = self._ActionForAllTorrents(
            client=client, func=client.torrents_set_super_seeding
        )
        self.setSuperSeeding = self.set_super_seeding
        self.add_peers = self._ActionForAllTorrents(
            client=client, func=client.torrents_add_peers
        )
        self.addPeers = self.add_peers

    class _ActionForAllTorrents(ClientCache["TorrentsAPIMixIn"]):
        def __init__(
            self,
            client: TorrentsAPIMixIn,
            func: Callable[..., Any],
        ) -> None:
            super().__init__(client=client)
            self.func = func

        def __call__(
            self,
            torrent_hashes: str | Iterable[str] | None = None,
            **kwargs: APIKwargsT,
        ) -> Any | None:
            return self.func(torrent_hashes=torrent_hashes, **kwargs)

        def all(self, **kwargs: APIKwargsT) -> Any | None:
            return self.func(torrent_hashes="all", **kwargs)

    class _Info(ClientCache["TorrentsAPIMixIn"]):
        def __call__(
            self,
            status_filter: TorrentStatusesT | None = None,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter=status_filter,
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def all(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="all",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def downloading(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="downloading",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def seeding(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="seeding",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def completed(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="completed",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def stopped(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="stopped",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        paused = stopped

        def active(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="active",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def inactive(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="inactive",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def resumed(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="resumed",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def stalled(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="stalled",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def stalled_uploading(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="stalled_uploading",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def stalled_downloading(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="stalled_downloading",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def checking(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="checking",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def moving(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="moving",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

        def errored(
            self,
            category: str | None = None,
            sort: str | None = None,
            reverse: bool | None = None,
            limit: str | int | None = None,
            offset: str | int | None = None,
            torrent_hashes: str | Iterable[str] | None = None,
            tag: str | None = None,
            private: bool | None = None,
            include_trackers: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> TorrentInfoList:
            return self._client.torrents_info(
                status_filter="errored",
                category=category,
                sort=sort,
                reverse=reverse,
                limit=limit,
                offset=offset,
                torrent_hashes=torrent_hashes,
                tag=tag,
                private=private,
                include_trackers=include_trackers,
                **kwargs,
            )

    def add(
        self,
        urls: str | Iterable[str] | None = None,
        torrent_files: TorrentFilesT | None = None,
        save_path: str | None = None,
        cookie: str | None = None,
        category: str | None = None,
        is_skip_checking: bool | None = None,
        is_paused: bool | None = None,
        is_root_folder: bool | None = None,
        rename: str | None = None,
        upload_limit: str | int | None = None,
        download_limit: str | int | None = None,
        use_auto_torrent_management: bool | None = None,
        is_sequential_download: bool | None = None,
        is_first_last_piece_priority: bool | None = None,
        tags: str | Iterable[str] | None = None,
        content_layout: Literal["Original", "Subfolder", "NoSubfolder"] | None = None,
        ratio_limit: str | float | None = None,
        seeding_time_limit: str | int | None = None,
        download_path: str | None = None,
        use_download_path: bool | None = None,
        stop_condition: Literal["MetadataReceived", "FilesChecked"] | None = None,
        add_to_top_of_queue: bool | None = None,
        inactive_seeding_time_limit: str | int | None = None,
        share_limit_action: Literal[
            "Stop", "Remove", "RemoveWithContent", "EnableSuperSeeding"
        ]
        | None = None,
        ssl_certificate: str | None = None,
        ssl_private_key: str | None = None,
        ssl_dh_params: str | None = None,
        is_stopped: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> str:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_add`."""
        return self._client.torrents_add(
            urls=urls,
            torrent_files=torrent_files,
            save_path=save_path,
            cookie=cookie,
            category=category,
            is_skip_checking=is_skip_checking,
            is_paused=is_paused,
            is_root_folder=is_root_folder,
            rename=rename,
            upload_limit=upload_limit,
            download_limit=download_limit,
            is_sequential_download=is_sequential_download,
            use_auto_torrent_management=use_auto_torrent_management,
            is_first_last_piece_priority=is_first_last_piece_priority,
            tags=tags,
            content_layout=content_layout,
            ratio_limit=ratio_limit,
            seeding_time_limit=seeding_time_limit,
            download_path=download_path,
            use_download_path=use_download_path,
            stop_condition=stop_condition,
            add_to_top_of_queue=add_to_top_of_queue,
            inactive_seeding_time_limit=inactive_seeding_time_limit,
            share_limit_action=share_limit_action,
            ssl_certificate=ssl_certificate,
            ssl_private_key=ssl_private_key,
            ssl_dh_params=ssl_dh_params,
            is_stopped=is_stopped,
            **kwargs,
        )

    def count(self) -> int:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_count`."""
        return self._client.torrents_count()

    def properties(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentPropertiesDictionary:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_properties`."""
        return self._client.torrents_properties(torrent_hash=torrent_hash, **kwargs)

    def trackers(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TrackersList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_trackers`."""
        return self._client.torrents_trackers(torrent_hash=torrent_hash, **kwargs)

    def webseeds(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> WebSeedsList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_webseeds`."""
        return self._client.torrents_webseeds(torrent_hash=torrent_hash, **kwargs)

    def add_webseeds(
        self,
        torrent_hash: str | None = None,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_add_webseeds`."""
        return self._client.torrents_add_webseeds(
            torrent_hash=torrent_hash,
            urls=urls,
            **kwargs,
        )

    addWebSeeds = add_webseeds

    def edit_webseed(
        self,
        torrent_hash: str | None = None,
        orig_url: str | None = None,
        new_url: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_edit_webseed`."""
        return self._client.torrents_edit_webseed(
            torrent_hash=torrent_hash,
            orig_url=orig_url,
            new_url=new_url,
            **kwargs,
        )

    editWebSeed = edit_webseed

    def remove_webseeds(
        self,
        torrent_hash: str | None = None,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_remove_webseeds`."""
        return self._client.torrents_remove_webseeds(
            torrent_hash=torrent_hash,
            urls=urls,
            **kwargs,
        )

    removeWebSeeds = remove_webseeds

    def files(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentFilesList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_files`."""
        return self._client.torrents_files(torrent_hash=torrent_hash, **kwargs)

    def piece_states(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentPieceInfoList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_piece_states`."""
        return self._client.torrents_piece_states(torrent_hash=torrent_hash, **kwargs)

    pieceStates = piece_states

    def piece_hashes(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentPieceInfoList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_piece_hashes`."""
        return self._client.torrents_piece_hashes(torrent_hash=torrent_hash, **kwargs)

    pieceHashes = piece_hashes

    def add_trackers(
        self,
        torrent_hash: str | None = None,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_add_trackers`."""
        return self._client.torrents_add_trackers(
            torrent_hash=torrent_hash,
            urls=urls,
            **kwargs,
        )

    addTrackers = add_trackers

    def edit_tracker(
        self,
        torrent_hash: str | None = None,
        original_url: str | None = None,
        new_url: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_edit_tracker`."""
        return self._client.torrents_edit_tracker(
            torrent_hash=torrent_hash,
            original_url=original_url,
            new_url=new_url,
            **kwargs,
        )

    editTracker = edit_tracker

    def remove_trackers(
        self,
        torrent_hash: str | None = None,
        urls: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_remove_trackers`."""
        return self._client.torrents_remove_trackers(
            torrent_hash=torrent_hash,
            urls=urls,
            **kwargs,
        )

    removeTrackers = remove_trackers

    def file_priority(
        self,
        torrent_hash: str | None = None,
        file_ids: str | int | Iterable[str | int] | None = None,
        priority: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_file_priority`."""
        return self._client.torrents_file_priority(
            torrent_hash=torrent_hash,
            file_ids=file_ids,
            priority=priority,
            **kwargs,
        )

    filePrio = file_priority

    def rename(
        self,
        torrent_hash: str | None = None,
        new_torrent_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_rename`."""
        return self._client.torrents_rename(
            torrent_hash=torrent_hash,
            new_torrent_name=new_torrent_name,
            **kwargs,
        )

    def rename_file(
        self,
        torrent_hash: str | None = None,
        file_id: str | int | None = None,
        new_file_name: str | None = None,
        old_path: str | None = None,
        new_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_rename_file`."""
        return self._client.torrents_rename_file(
            torrent_hash=torrent_hash,
            file_id=file_id,
            new_file_name=new_file_name,
            old_path=old_path,
            new_path=new_path,
            **kwargs,
        )

    renameFile = rename_file

    def rename_folder(
        self,
        torrent_hash: str | None = None,
        old_path: str | None = None,
        new_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_rename_folder`."""
        return self._client.torrents_rename_folder(
            torrent_hash=torrent_hash,
            old_path=old_path,
            new_path=new_path,
            **kwargs,
        )

    renameFolder = rename_folder

    def export(
        self,
        torrent_hash: str | None = None,
        **kwargs: APIKwargsT,
    ) -> bytes:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_export`."""
        return self._client.torrents_export(torrent_hash=torrent_hash, **kwargs)


class TorrentCategories(ClientCache[TorrentsAPIMixIn]):
    """
    Allows interaction with torrent categories within the ``Torrents`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # these are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'torrents_' prepended)
        >>> categories = client.torrent_categories.categories
        >>> # create or edit categories
        >>> client.torrent_categories.create_category(name="Video", save_path="/home/user/torrents/Video")
        >>> client.torrent_categories.edit_category(name="Video", save_path="/data/torrents/Video")
        >>> # edit or create new by assignment
        >>> client.torrent_categories.categories = dict(name="Video", save_path="/hone/user/")
        >>> # delete categories
        >>> client.torrent_categories.removeCategories(categories="Video")
        >>> client.torrent_categories.removeCategories(categories=["Audio", "ISOs"])
    """  # noqa: E501

    @property
    def categories(self) -> TorrentCategoriesDictionary:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_categories`."""
        return self._client.torrents_categories()

    @categories.setter
    def categories(self, val: Mapping[str, str | bool]) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_edit_category`."""
        if val.get("name", "") in self.categories:
            self.edit_category(**val)  # type: ignore[arg-type]
        else:
            self.create_category(**val)  # type: ignore[arg-type]

    def create_category(
        self,
        name: str | None = None,
        save_path: str | None = None,
        download_path: str | None = None,
        enable_download_path: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_create_category`."""
        return self._client.torrents_create_category(
            name=name,
            save_path=save_path,
            download_path=download_path,
            enable_download_path=enable_download_path,
            **kwargs,
        )

    createCategory = create_category

    def edit_category(
        self,
        name: str | None = None,
        save_path: str | None = None,
        download_path: str | None = None,
        enable_download_path: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_edit_category`."""
        return self._client.torrents_edit_category(
            name=name,
            save_path=save_path,
            download_path=download_path,
            enable_download_path=enable_download_path,
            **kwargs,
        )

    editCategory = edit_category

    def remove_categories(
        self,
        categories: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_remove_categories`."""
        return self._client.torrents_remove_categories(categories=categories, **kwargs)

    removeCategories = remove_categories


class TorrentTags(ClientCache[TorrentsAPIMixIn]):
    """
    Allows interaction with torrent tags within the "Torrent" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> tags = client.torrent_tags.tags
        >>> client.torrent_tags.tags = "tv show"  # create category
        >>> client.torrent_tags.create_tags(tags=["tv show", "linux distro"])
        >>> client.torrent_tags.delete_tags(tags="tv show")
    """  # noqa: E501

    @property
    def tags(self) -> TagList:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_tags`."""
        return self._client.torrents_tags()

    @tags.setter
    def tags(self, val: Iterable[str] | None = None) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_create_tags`."""
        self._client.torrents_create_tags(tags=val)

    def add_tags(
        self,
        tags: str | Iterable[str] | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_add_tags`."""
        self._client.torrents_add_tags(
            tags=tags,
            torrent_hashes=torrent_hashes,
            **kwargs,
        )

    addTags = add_tags

    def set_tags(
        self,
        tags: str | Iterable[str] | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_set_tags`."""
        self._client.torrents_set_tags(
            tags=tags,
            torrent_hashes=torrent_hashes,
            **kwargs,
        )

    setTags = set_tags

    def remove_tags(
        self,
        tags: str | Iterable[str] | None = None,
        torrent_hashes: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_remove_tags`."""
        self._client.torrents_remove_tags(
            tags=tags,
            torrent_hashes=torrent_hashes,
            **kwargs,
        )

    removeTags = remove_tags

    def create_tags(
        self,
        tags: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_create_tags`."""
        self._client.torrents_create_tags(tags=tags, **kwargs)

    createTags = create_tags

    def delete_tags(
        self,
        tags: str | Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentsAPIMixIn.torrents_delete_tags`."""
        self._client.torrents_delete_tags(tags=tags, **kwargs)

    deleteTags = delete_tags
