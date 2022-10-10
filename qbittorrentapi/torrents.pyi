from typing import IO
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List as ListT
from typing import Literal
from typing import Mapping
from typing import Optional
from typing import Text
from typing import Tuple
from typing import TypeVar
from typing import Union

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import Dictionary
from qbittorrentapi.definitions import List
from qbittorrentapi.definitions import ListEntry
from qbittorrentapi.definitions import TorrentStates

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
KWARGS = Any
JsonValueT = Union[None, int, Text, bool, ListT[JsonValueT], Dict[Text, JsonValueT]]

TORRENT_STATUSES_T = Literal[
    "all",
    "downloading",
    "completed",
    "paused",
    "active",
    "inactive",
    "resumed",
    "stalled",
    "stalled_uploading",
    "stalled_downloading",
]

TORRENT_FILES_T = TypeVar(
    "TORRENT_FILES_T",
    bytes,
    Text,
    IO[bytes],
    Mapping[Text, bytes | Text | IO[bytes]],
    Iterable[bytes | Text | IO[bytes]],
)

class TorrentDictionary(Dictionary[K, V]):
    def __init__(
        self, data: Mapping[Any, Any], client: Optional[TorrentsAPIMixIn] = None
    ) -> None: ...
    def sync_local(self) -> None: ...
    @property
    def state_enum(self) -> TorrentStates: ...
    @property
    def info(self) -> TorrentDictionary[Text, JsonValueT]: ...
    def resume(self, **kwargs: KWARGS) -> None: ...
    def pause(self, **kwargs: KWARGS) -> None: ...
    def delete(self, delete_files: bool = False, **kwargs: KWARGS) -> None: ...
    def recheck(self, **kwargs: KWARGS) -> None: ...
    def reannounce(self, **kwargs: KWARGS) -> None: ...
    def increase_priority(self, **kwargs: KWARGS) -> None: ...
    increasePrio = increase_priority
    def decrease_priority(self, **kwargs: KWARGS) -> None: ...
    decreasePrio = decrease_priority
    def top_priority(self, **kwargs: KWARGS) -> None: ...
    topPrio = top_priority
    def bottom_priority(self, **kwargs: KWARGS) -> None: ...
    bottomPrio = bottom_priority
    def set_share_limits(
        self,
        ratio_limit: Optional[Text | int] = None,
        seeding_time_limit: Optional[Text | int] = None,
        **kwargs: KWARGS
    ) -> None: ...
    setShareLimits = set_share_limits
    @property
    def download_limit(self) -> TorrentLimitsDictionary[Text, JsonValueT]: ...
    @download_limit.setter
    def download_limit(self, v: Text | int) -> None: ...
    @property
    def downloadLimit(self) -> TorrentLimitsDictionary[Text, JsonValueT]: ...
    @downloadLimit.setter
    def downloadLimit(self, v: Text | int) -> None: ...
    def set_download_limit(
        self, limit: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> None: ...
    setDownloadLimit = set_download_limit
    @property
    def upload_limit(self) -> TorrentLimitsDictionary[Text, JsonValueT]: ...
    @upload_limit.setter
    def upload_limit(self, v: Text | int) -> None: ...
    @property
    def uploadLimit(self) -> TorrentLimitsDictionary[Text, JsonValueT]: ...
    @uploadLimit.setter
    def uploadLimit(self, v: Text | int) -> None: ...
    def set_upload_limit(
        self, limit: Optional[Text | int] = None, **kwargs: KWARGS
    ) -> None: ...
    setUploadLimit = set_upload_limit
    def set_location(
        self, location: Optional[Text] = None, **kwargs: KWARGS
    ) -> None: ...
    setLocation = set_location
    def set_category(
        self, category: Optional[Text] = None, **kwargs: KWARGS
    ) -> None: ...
    setCategory = set_category
    def set_auto_management(
        self, enable: Optional[bool] = None, **kwargs: KWARGS
    ) -> None: ...
    setAutoManagement = set_auto_management
    def toggle_sequential_download(self, **kwargs: KWARGS) -> None: ...
    toggleSequentialDownload = toggle_sequential_download
    def toggle_first_last_piece_priority(self, **kwargs: KWARGS) -> None: ...
    toggleFirstLastPiecePrio = toggle_first_last_piece_priority
    def set_force_start(
        self, enable: Optional[bool] = None, **kwargs: KWARGS
    ) -> None: ...
    setForceStart = set_force_start
    def set_super_seeding(
        self, enable: Optional[bool] = None, **kwargs: KWARGS
    ) -> None: ...
    setSuperSeeding = set_super_seeding
    @property
    def properties(self) -> TorrentPropertiesDictionary[Text, JsonValueT]: ...
    @property
    def trackers(self) -> TrackersList[Tracker[Text, JsonValueT]]: ...
    @trackers.setter
    def trackers(self, v: Iterable[Text]) -> None: ...
    @property
    def webseeds(self) -> WebSeedsList[WebSeed[Text, JsonValueT]]: ...
    @property
    def files(self) -> TorrentFilesList[TorrentFile[Text, JsonValueT]]: ...
    def rename_file(
        self,
        file_id: Optional[Text | int] = None,
        new_file_name: Optional[Text] = None,
        old_path: Optional[Text] = None,
        new_path: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    renameFile = rename_file
    def rename_folder(
        self,
        old_path: Optional[Text] = None,
        new_path: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    renameFolder = rename_folder
    @property
    def piece_states(
        self,
    ) -> TorrentPieceInfoList[TorrentPieceData[Text, JsonValueT]]: ...
    pieceStates = piece_states
    @property
    def piece_hashes(
        self,
    ) -> TorrentPieceInfoList[TorrentPieceData[Text, JsonValueT]]: ...
    pieceHashes = piece_hashes
    def add_trackers(
        self, urls: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    addTrackers = add_trackers
    def edit_tracker(
        self,
        orig_url: Optional[Text] = None,
        new_url: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    editTracker = edit_tracker
    def remove_trackers(
        self, urls: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    removeTrackers = remove_trackers
    def file_priority(
        self,
        file_ids: Optional[int | Iterable[Text | int]] = None,
        priority: Optional[Text | int] = None,
        **kwargs: KWARGS
    ) -> None: ...
    filePriority = file_priority
    def rename(self, new_name: Optional[Text] = None, **kwargs: KWARGS) -> None: ...
    def add_tags(
        self, tags: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    def remove_tags(
        self, tags: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    def export(self, **kwargs: KWARGS) -> bytes: ...

class TorrentPropertiesDictionary(Dictionary[K, V]): ...
class TorrentLimitsDictionary(Dictionary[K, V]): ...
class TorrentCategoriesDictionary(Dictionary[K, V]): ...
class TorrentsAddPeersDictionary(Dictionary[K, V]): ...

class TorrentFilesList(List[T]):
    def __init__(
        self,
        list_entries: Iterable[ListEntry[Text, JsonValueT]],
        client: Optional[TorrentsAPIMixIn] = None,
    ) -> None: ...

class TorrentFile(ListEntry[K, V]): ...

class WebSeedsList(List[T]):
    def __init__(
        self,
        list_entries: Iterable[ListEntry[Text, JsonValueT]],
        client: Optional[TorrentsAPIMixIn] = None,
    ) -> None: ...

class WebSeed(ListEntry[K, V]): ...

class TrackersList(List[T]):
    def __init__(
        self,
        list_entries: Iterable[ListEntry[Text, JsonValueT]],
        client: Optional[TorrentsAPIMixIn] = None,
    ) -> None: ...

class Tracker(ListEntry[K, V]): ...

class TorrentInfoList(List[T]):
    def __init__(
        self,
        list_entries: Iterable[ListEntry[Text, JsonValueT]],
        client: Optional[TorrentsAPIMixIn] = None,
    ) -> None: ...

class TorrentPieceInfoList(List[T]):
    def __init__(
        self,
        list_entries: Iterable[ListEntry[Text, JsonValueT]],
        client: Optional[TorrentsAPIMixIn] = None,
    ) -> None: ...

class TorrentPieceData(ListEntry[K, V]): ...

class TagList(List[T]):
    def __init__(
        self,
        list_entries: Iterable[ListEntry[Text, JsonValueT]],
        client: Optional[TorrentsAPIMixIn] = None,
    ) -> None: ...

class Tag(ListEntry[K, V]): ...

class Torrents(ClientCache):
    info: _Info
    resume: _ActionForAllTorrents
    pause: _ActionForAllTorrents
    delete: _ActionForAllTorrents
    recheck: _ActionForAllTorrents
    reannounce: _ActionForAllTorrents
    increase_priority: _ActionForAllTorrents
    increasePrio: _ActionForAllTorrents
    decrease_priority: _ActionForAllTorrents
    decreasePrio: _ActionForAllTorrents
    top_priority: _ActionForAllTorrents
    topPrio: _ActionForAllTorrents
    bottom_priority: _ActionForAllTorrents
    bottomPrio: _ActionForAllTorrents
    download_limit: _ActionForAllTorrents
    downloadLimit: _ActionForAllTorrents
    upload_limit: _ActionForAllTorrents
    uploadLimit: _ActionForAllTorrents
    set_download_limit: _ActionForAllTorrents
    setDownloadLimit: _ActionForAllTorrents
    set_share_limits: _ActionForAllTorrents
    setShareLimits: _ActionForAllTorrents
    set_upload_limit: _ActionForAllTorrents
    setUploadLimit: _ActionForAllTorrents
    set_location: _ActionForAllTorrents
    setLocation: _ActionForAllTorrents
    set_save_path: _ActionForAllTorrents
    setSavePath: _ActionForAllTorrents
    set_download_path: _ActionForAllTorrents
    setDownloadPath: _ActionForAllTorrents
    set_category: _ActionForAllTorrents
    setCategory: _ActionForAllTorrents
    set_auto_management: _ActionForAllTorrents
    setAutoManagement: _ActionForAllTorrents
    toggle_sequential_download: _ActionForAllTorrents
    toggleSequentialDownload: _ActionForAllTorrents
    toggle_first_last_piece_priority: _ActionForAllTorrents
    toggleFirstLastPiecePrio: _ActionForAllTorrents
    set_force_start: _ActionForAllTorrents
    setForceStart: _ActionForAllTorrents
    set_super_seeding: _ActionForAllTorrents
    setSuperSeeding: _ActionForAllTorrents
    add_peers: _ActionForAllTorrents
    addPeers: _ActionForAllTorrents
    def __init__(self, client: TorrentsAPIMixIn) -> None: ...
    def add(
        self,
        urls: Optional[Iterable[Text]] = None,
        torrent_files: Optional[TORRENT_FILES_T] = None,
        save_path: Optional[Text] = None,
        cookie: Optional[Text] = None,
        category: Optional[Text] = None,
        is_skip_checking: Optional[bool] = None,
        is_paused: Optional[bool] = None,
        is_root_folder: Optional[bool] = None,
        rename: Optional[Text] = None,
        upload_limit: Optional[Text | int] = None,
        download_limit: Optional[Text | int] = None,
        use_auto_torrent_management: Optional[bool] = None,
        is_sequential_download: Optional[bool] = None,
        is_first_last_piece_priority: Optional[bool] = None,
        tags: Optional[Iterable[Text]] = None,
        content_layout: Optional[
            Literal["Original", "Subfolder", "NoSubFolder"]
        ] = None,
        ratio_limit: Optional[Text | float] = None,
        seeding_time_limit: Optional[Text | int] = None,
        download_path: Optional[Text] = None,
        use_download_path: Optional[bool] = None,
        stop_condition: Optional[Literal["MetadataReceived", "FilesChecked"]] = None,
        **kwargs: KWARGS
    ) -> Text: ...

    class _ActionForAllTorrents(ClientCache):
        func: Callable[..., Any]
        def __init__(
            self, client: TorrentsAPIMixIn, func: Callable[..., Any]
        ) -> None: ...
        def __call__(
            self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
        ) -> Optional[Any]: ...
        def all(self, **kwargs: KWARGS) -> Optional[Any]: ...

    class _Info(ClientCache):
        def __call__(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def all(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def downloading(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def completed(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def paused(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def active(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def inactive(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def resumed(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def stalled(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def stalled_uploading(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
        def stalled_downloading(
            self,
            category: Optional[Text] = None,
            sort: Optional[TORRENT_STATUSES_T] = None,
            reverse: Optional[bool] = None,
            limit: Optional[Text | int] = None,
            offset: Optional[Text | int] = None,
            torrent_hashes: Optional[Iterable[Text]] = None,
            tag: Optional[Text] = None,
            **kwargs: KWARGS
        ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...

class TorrentCategories(ClientCache):
    @property
    def categories(self) -> TorrentCategoriesDictionary[Text, JsonValueT]: ...
    @categories.setter
    def categories(self, v: Iterable[Text]) -> None: ...
    def create_category(
        self,
        name: Optional[Text] = None,
        save_path: Optional[Text] = None,
        download_path: Optional[Text] = None,
        enable_download_path: Optional[bool] = None,
        **kwargs: KWARGS
    ) -> None: ...
    createCategory = create_category
    def edit_category(
        self,
        name: Optional[Text] = None,
        save_path: Optional[Text] = None,
        download_path: Optional[Text] = None,
        enable_download_path: Optional[bool] = None,
        **kwargs: KWARGS
    ) -> None: ...
    editCategory = edit_category
    def remove_categories(
        self, categories: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    removeCategories = remove_categories

class TorrentTags(ClientCache):
    @property
    def tags(self) -> TagList[Tag[Text, JsonValueT]]: ...
    @tags.setter
    def tags(self, v: Optional[Iterable[Text]] = None) -> None: ...
    def add_tags(
        self,
        tags: Optional[Iterable[Text]] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    def remove_tags(
        self,
        tags: Optional[Iterable[Text]] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    def create_tags(
        self, tags: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    def delete_tags(
        self, tags: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...

class TorrentsAPIMixIn(AppAPIMixIn):
    @property
    def torrents(self) -> Torrents: ...
    @property
    def torrent_categories(self) -> TorrentCategories: ...
    @property
    def torrent_tags(self) -> TorrentTags: ...
    def torrents_add(
        self,
        urls: Optional[Iterable[Text]] = None,
        torrent_files: Optional[TORRENT_FILES_T] = None,
        save_path: Optional[Text] = None,
        cookie: Optional[Text] = None,
        category: Optional[Text] = None,
        is_skip_checking: Optional[bool] = None,
        is_paused: Optional[bool] = None,
        is_root_folder: Optional[bool] = None,
        rename: Optional[Text] = None,
        upload_limit: Optional[Text | int] = None,
        download_limit: Optional[Text | int] = None,
        use_auto_torrent_management: Optional[bool] = None,
        is_sequential_download: Optional[bool] = None,
        is_first_last_piece_priority: Optional[bool] = None,
        tags: Optional[Iterable[Text]] = None,
        content_layout: Optional[
            Literal["Original", "Subfolder", "NoSubFolder"]
        ] = None,
        ratio_limit: Optional[Text | float] = None,
        seeding_time_limit: Optional[Text | int] = None,
        download_path: Optional[Text] = None,
        use_download_path: Optional[bool] = None,
        **kwargs: KWARGS
    ) -> Text: ...
    @staticmethod
    def _normalize_torrent_files(
        user_files: TORRENT_FILES_T,
    ) -> Tuple[Dict[Text, IO[bytes] | Tuple[Text, IO[bytes]]], List[IO[bytes]]] | Tuple[
        None, None
    ]: ...
    def torrents_properties(
        self, torrent_hash: Optional[Text] = None, **kwargs: KWARGS
    ) -> TorrentPropertiesDictionary[Text, JsonValueT]: ...
    def torrents_trackers(
        self, torrent_hash: Optional[Text] = None, **kwargs: KWARGS
    ) -> TrackersList[Tracker[Text, JsonValueT]]: ...
    def torrents_webseeds(
        self, torrent_hash: Optional[Text] = None, **kwargs: KWARGS
    ) -> WebSeedsList[WebSeed[Text, JsonValueT]]: ...
    def torrents_files(
        self, torrent_hash: Optional[Text] = None, **kwargs: KWARGS
    ) -> TorrentFilesList[TorrentFile[Text, JsonValueT]]: ...
    def torrents_piece_states(
        self, torrent_hash: Optional[Text] = None, **kwargs: KWARGS
    ) -> TorrentPieceInfoList[TorrentPieceData[Text, JsonValueT]]: ...
    torrents_pieceStates = torrents_piece_states
    def torrents_piece_hashes(
        self, torrent_hash: Optional[Text] = None, **kwargs: KWARGS
    ) -> TorrentPieceInfoList[TorrentPieceData[Text, JsonValueT]]: ...
    torrents_pieceHashes = torrents_piece_hashes
    def torrents_add_trackers(
        self,
        torrent_hash: Optional[Text] = None,
        urls: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_addTrackers = torrents_add_trackers
    def torrents_edit_tracker(
        self,
        torrent_hash: Optional[Text] = None,
        original_url: Optional[Text] = None,
        new_url: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_editTracker = torrents_edit_tracker
    def torrents_remove_trackers(
        self,
        torrent_hash: Optional[Text] = None,
        urls: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_removeTrackers = torrents_remove_trackers
    def torrents_file_priority(
        self,
        torrent_hash: Optional[Text] = None,
        file_ids: Optional[int | Iterable[Text | int]] = None,
        priority: Optional[Text | int] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_filePrio = torrents_file_priority
    def torrents_rename(
        self,
        torrent_hash: Optional[Text] = None,
        new_torrent_name: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    def torrents_rename_file(
        self,
        torrent_hash: Optional[Text] = None,
        file_id: Optional[Text | int] = None,
        new_file_name: Optional[Text] = None,
        old_path: Optional[Text] = None,
        new_path: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_renameFile = torrents_rename_file
    def torrents_rename_folder(
        self,
        torrent_hash: Optional[Text] = None,
        old_path: Optional[Text] = None,
        new_path: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_renameFolder = torrents_rename_folder
    def torrents_export(
        self, torrent_hash: Optional[Text] = None, **kwargs: KWARGS
    ) -> bytes: ...
    def torrents_info(
        self,
        status_filter: Optional[TORRENT_STATUSES_T] = None,
        category: Optional[Text] = None,
        sort: Optional[Text] = None,
        reverse: Optional[bool] = None,
        limit: Optional[Text | int] = None,
        offset: Optional[Text | int] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        tag: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> TorrentInfoList[TorrentDictionary[Text, JsonValueT]]: ...
    def torrents_resume(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    def torrents_pause(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    def torrents_delete(
        self,
        delete_files: bool = False,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    def torrents_recheck(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    def torrents_reannounce(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    def torrents_increase_priority(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_increasePrio = torrents_increase_priority
    def torrents_decrease_priority(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_decreasePrio = torrents_decrease_priority
    def torrents_top_priority(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_topPrio = torrents_top_priority
    def torrents_bottom_priority(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_bottomPrio = torrents_bottom_priority
    def torrents_download_limit(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> TorrentLimitsDictionary[Text, JsonValueT]: ...
    torrents_downloadLimit = torrents_download_limit
    def torrents_set_download_limit(
        self,
        limit: Optional[Text | int] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setDownloadLimit = torrents_set_download_limit
    def torrents_set_share_limits(
        self,
        ratio_limit: Optional[Text | int] = None,
        seeding_time_limit: Optional[Text | int] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setShareLimits = torrents_set_share_limits
    def torrents_upload_limit(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> TorrentLimitsDictionary[Text, JsonValueT]: ...
    torrents_uploadLimit = torrents_upload_limit
    def torrents_set_upload_limit(
        self,
        limit: Optional[Text | int] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setUploadLimit = torrents_upload_limit
    def torrents_set_location(
        self,
        location: Optional[Text] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setLocation = torrents_set_location
    def torrents_set_save_path(
        self,
        save_path: Optional[Text] = None,
        torrents_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setSavePath = torrents_set_save_path
    def torrents_set_download_path(
        self,
        download_path: Optional[Text] = None,
        torrents_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setDownloadPath = torrents_set_download_path
    def torrents_set_category(
        self,
        category: Optional[Text] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setCategory = torrents_set_category
    def torrents_set_auto_management(
        self,
        enable: Optional[bool] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setAutoManagement = torrents_set_auto_management
    def torrents_toggle_sequential_download(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_toggleSequentialDownload = torrents_toggle_sequential_download
    def torrents_toggle_first_last_piece_priority(
        self, torrent_hashes: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_toggleFirstLastPiecePrio = torrents_toggle_first_last_piece_priority
    def torrents_set_force_start(
        self,
        enable: Optional[bool] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setForceStart = torrents_set_force_start
    def torrents_set_super_seeding(
        self,
        enable: Optional[bool] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_setSuperSeeding = torrents_set_super_seeding
    def torrents_add_peers(
        self,
        peers: Optional[Iterable[Text]] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> TorrentsAddPeersDictionary[Text, JsonValueT]: ...
    torrents_addPeers = torrents_add_peers
    def torrents_categories(
        self, **kwargs: KWARGS
    ) -> TorrentCategoriesDictionary[Text, JsonValueT]: ...
    def torrents_create_category(
        self,
        name: Optional[Text] = None,
        save_path: Optional[Text] = None,
        download_path: Optional[Text] = None,
        enable_download_path: Optional[bool] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_createCategory = torrents_create_category
    def torrents_edit_category(
        self,
        name: Optional[Text] = None,
        save_path: Optional[Text] = None,
        download_path: Optional[Text] = None,
        enable_download_path: Optional[bool] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_editCategory = torrents_edit_category
    def torrents_remove_categories(
        self, categories: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_removeCategories = torrents_remove_categories
    def torrents_tags(self, **kwargs: KWARGS) -> TagList[Tag[Text, JsonValueT]]: ...
    def torrents_add_tags(
        self,
        tags: Optional[Iterable[Text]] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_addTags = torrents_add_tags
    def torrents_remove_tags(
        self,
        tags: Optional[Iterable[Text]] = None,
        torrent_hashes: Optional[Iterable[Text]] = None,
        **kwargs: KWARGS
    ) -> None: ...
    torrents_removeTags = torrents_remove_tags
    def torrents_create_tags(
        self, tags: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_createTags = torrents_create_tags
    def torrents_delete_tags(
        self, tags: Optional[Iterable[Text]] = None, **kwargs: KWARGS
    ) -> None: ...
    torrents_deleteTags = torrents_delete_tags
