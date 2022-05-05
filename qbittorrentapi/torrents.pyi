from typing import IO
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Literal
from typing import MutableMapping
from typing import Text
from typing import Tuple
from typing import TypeVar

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.definitions import Dictionary
from qbittorrentapi.definitions import List
from qbittorrentapi.definitions import ListEntry
from qbittorrentapi.definitions import TorrentStates

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
    IO,
    MutableMapping[Text, bytes | Text | IO],
    Iterable[bytes | Text | IO],
)

class TorrentDictionary(Dictionary):
    def __init__(
        self, data: MutableMapping, client: TorrentsAPIMixIn = None
    ) -> None: ...
    def sync_local(self) -> None: ...
    @property
    def state_enum(self) -> TorrentStates: ...
    @property
    def info(self) -> TorrentDictionary: ...
    def resume(self, **kwargs) -> None: ...
    def pause(self, **kwargs) -> None: ...
    def delete(self, delete_files: bool = False, **kwargs) -> None: ...
    def recheck(self, **kwargs) -> None: ...
    def reannounce(self, **kwargs) -> None: ...
    def increase_priority(self, **kwargs) -> None: ...
    increasePrio = increase_priority
    def decrease_priority(self, **kwargs) -> None: ...
    decreasePrio = decrease_priority
    def top_priority(self, **kwargs) -> None: ...
    topPrio = top_priority
    def bottom_priority(self, **kwargs) -> None: ...
    bottomPrio = bottom_priority
    def set_share_limits(
        self,
        ratio_limit: Text | int = None,
        seeding_time_limit: Text | int = None,
        **kwargs
    ) -> None: ...
    setShareLimits = set_share_limits
    @property
    def download_limit(self) -> TorrentLimitsDictionary: ...
    downloadLimit = download_limit
    @downloadLimit.setter
    def downloadLimit(self, v: Text | int) -> None: ...
    @download_limit.setter
    def download_limit(self, v: Text | int) -> None: ...
    def set_download_limit(self, limit: Text | int = None, **kwargs) -> None: ...
    setDownloadLimit = set_download_limit
    @property
    def upload_limit(self) -> TorrentLimitsDictionary: ...
    uploadLimit = upload_limit
    @uploadLimit.setter
    def uploadLimit(self, v: Text | int) -> None: ...
    @upload_limit.setter
    def upload_limit(self, v: Text | int) -> None: ...
    def set_upload_limit(self, limit: Text | int = None, **kwargs) -> None: ...
    setUploadLimit = set_upload_limit
    def set_location(self, location: Text = None, **kwargs) -> None: ...
    setLocation = set_location
    def set_category(self, category: Text = None, **kwargs) -> None: ...
    setCategory = set_category
    def set_auto_management(self, enable: bool = None, **kwargs) -> None: ...
    setAutoManagement = set_auto_management
    def toggle_sequential_download(self, **kwargs) -> None: ...
    toggleSequentialDownload = toggle_sequential_download
    def toggle_first_last_piece_priority(self, **kwargs) -> None: ...
    toggleFirstLastPiecePrio = toggle_first_last_piece_priority
    def set_force_start(self, enable: bool = None, **kwargs) -> None: ...
    setForceStart = set_force_start
    def set_super_seeding(self, enable: bool = None, **kwargs) -> None: ...
    setSuperSeeding = set_super_seeding
    @property
    def properties(self) -> TorrentPropertiesDictionary: ...
    @property
    def trackers(self) -> TrackersList[Tracker]: ...
    @trackers.setter
    def trackers(self, v: Iterable[Text]) -> None: ...
    @property
    def webseeds(self) -> WebSeedsList[WebSeed]: ...
    @property
    def files(self) -> TorrentFilesList[TorrentFile]: ...
    def rename_file(
        self,
        file_id: Text | int = None,
        new_file_name: Text = None,
        old_path: Text = None,
        new_path: Text = None,
        **kwargs
    ) -> None: ...
    renameFile = rename_file
    def rename_folder(
        self, old_path: Text = None, new_path: Text = None, **kwargs
    ) -> None: ...
    renameFolder = rename_folder
    @property
    def piece_states(self): ...
    pieceStates = piece_states
    @property
    def piece_hashes(self) -> TorrentPieceInfoList[TorrentPieceData]: ...
    pieceHashes = piece_hashes
    def add_trackers(self, urls: Iterable[Text] = None, **kwargs) -> None: ...
    addTrackers = add_trackers
    def edit_tracker(
        self, orig_url: Text = None, new_url: Text = None, **kwargs
    ) -> None: ...
    editTracker = edit_tracker
    def remove_trackers(self, urls: Iterable[Text] = None, **kwargs) -> None: ...
    removeTrackers = remove_trackers
    def file_priority(
        self,
        file_ids: int | Iterable[Text | int] = None,
        priority: Text | int = None,
        **kwargs
    ) -> None: ...
    filePriority = file_priority
    def rename(self, new_name: Text = None, **kwargs) -> None: ...
    def add_tags(self, tags: Iterable[Text] = None, **kwargs) -> None: ...
    def remove_tags(self, tags: Iterable[Text] = None, **kwargs) -> None: ...
    def export(self, **kwargs) -> bytes: ...

class TorrentPropertiesDictionary(Dictionary): ...
class TorrentLimitsDictionary(Dictionary): ...
class TorrentCategoriesDictionary(Dictionary): ...
class TorrentsAddPeersDictionary(Dictionary): ...

class TorrentFilesList(List):
    def __init__(
        self, list_entries: Iterable[Text], client: TorrentsAPIMixIn = None
    ) -> None: ...

class TorrentFile(ListEntry): ...

class WebSeedsList(List):
    def __init__(
        self, list_entries: Iterable[Text], client: TorrentsAPIMixIn = None
    ) -> None: ...

class WebSeed(ListEntry): ...

class TrackersList(List):
    def __init__(
        self, list_entries: Iterable[Text], client: TorrentsAPIMixIn = None
    ) -> None: ...

class Tracker(ListEntry): ...

class TorrentInfoList(List):
    def __init__(
        self, list_entries: Iterable[Text], client: TorrentsAPIMixIn = None
    ) -> None: ...

class TorrentPieceInfoList(List):
    def __init__(
        self, list_entries: Iterable[Text], client: TorrentsAPIMixIn = None
    ) -> None: ...

class TorrentPieceData(ListEntry): ...

class TagList(List):
    def __init__(
        self, list_entries: Iterable[Text], client: TorrentsAPIMixIn = None
    ) -> None: ...

class Tag(ListEntry): ...

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
        urls: Iterable[Text] = None,
        torrent_files: TORRENT_FILES_T = None,
        save_path: Text = None,
        cookie: Text = None,
        category: Text = None,
        is_skip_checking: bool = None,
        is_paused: bool = None,
        is_root_folder: bool = None,
        rename: Text = None,
        upload_limit: Text | int = None,
        download_limit: Text | int = None,
        use_auto_torrent_management: bool = None,
        is_sequential_download: bool = None,
        is_first_last_piece_priority: bool = None,
        tags: Iterable[Text] = None,
        content_layout: Literal["Original", "Subfolder", "NoSubFolder"] = None,
        ratio_limit: Text | float = None,
        seeding_time_limit: Text | int = None,
        **kwargs
    ) -> Text: ...

    class _ActionForAllTorrents(ClientCache):
        func: Callable
        def __init__(self, client: TorrentsAPIMixIn, func: Callable) -> None: ...
        def __call__(self, torrent_hashes: Iterable[Text] = None, **kwargs): ...
        def all(self, **kwargs): ...

    class _Info(ClientCache):
        def __call__(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def all(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def downloading(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def completed(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def paused(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def active(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def inactive(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def resumed(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def stalled(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def stalled_uploading(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...
        def stalled_downloading(
            self,
            category: Text = None,
            sort: TORRENT_STATUSES_T = None,
            reverse: bool = None,
            limit: Text | int = None,
            offset: Text | int = None,
            torrent_hashes: Iterable[Text] = None,
            tag: Text = None,
            **kwargs
        ) -> TorrentInfoList[TorrentDictionary]: ...

class TorrentCategories(ClientCache):
    @property
    def categories(self) -> TorrentCategoriesDictionary: ...
    @categories.setter
    def categories(self, v: Iterable[Text]) -> None: ...
    def create_category(
        self,
        name: Text = None,
        save_path: Text = None,
        download_path: Text = None,
        enable_download_path: bool = None,
        **kwargs
    ): ...
    createCategory = create_category
    def edit_category(
        self,
        name: Text = None,
        save_path: Text = None,
        download_path: Text = None,
        enable_download_path: bool = None,
        **kwargs
    ): ...
    editCategory = edit_category
    def remove_categories(self, categories: Iterable[Text] = None, **kwargs): ...
    removeCategories = remove_categories

class TorrentTags(ClientCache):
    @property
    def tags(self) -> TagList[Tag]: ...
    @tags.setter
    def tags(self, v: Iterable[Text] = None) -> None: ...
    def add_tags(
        self,
        tags: Iterable[Text] = None,
        torrent_hashes: Iterable[Text] = None,
        **kwargs
    ) -> None: ...
    def remove_tags(
        self,
        tags: Iterable[Text] = None,
        torrent_hashes: Iterable[Text] = None,
        **kwargs
    ) -> None: ...
    def create_tags(self, tags: Iterable[Text] = None, **kwargs) -> None: ...
    def delete_tags(self, tags: Iterable[Text] = None, **kwargs) -> None: ...

class TorrentsAPIMixIn(AppAPIMixIn):
    @property
    def torrents(self) -> Torrents: ...
    @property
    def torrent_categories(self) -> TorrentCategories: ...
    @property
    def torrent_tags(self) -> TorrentTags: ...
    def torrents_add(
        self,
        urls: Iterable[Text] = None,
        torrent_files: TORRENT_FILES_T = None,
        save_path: Text = None,
        cookie: Text = None,
        category: Text = None,
        is_skip_checking: bool = None,
        is_paused: bool = None,
        is_root_folder: bool = None,
        rename: Text = None,
        upload_limit: Text | int = None,
        download_limit: Text | int = None,
        use_auto_torrent_management: bool = None,
        is_sequential_download: bool = None,
        is_first_last_piece_priority: bool = None,
        tags: Iterable[Text] = None,
        content_layout: Literal["Original", "Subfolder", "NoSubFolder"] = None,
        ratio_limit: Text | float = None,
        seeding_time_limit: Text | int = None,
        download_path: Text = None,
        use_download_path: bool = None,
        **kwargs
    ) -> Text: ...
    @staticmethod
    def _normalize_torrent_files(
        user_files: TORRENT_FILES_T,
    ) -> Tuple[Dict[Text, IO | Tuple[Text, IO]], List[IO]] | Tuple[None, None]: ...
    def torrents_properties(
        self, torrent_hash: Text = None, **kwargs
    ) -> TorrentPropertiesDictionary: ...
    def torrents_trackers(
        self, torrent_hash: Text = None, **kwargs
    ) -> TrackersList[Tracker]: ...
    def torrents_webseeds(
        self, torrent_hash: Text = None, **kwargs
    ) -> WebSeedsList[WebSeed]: ...
    def torrents_files(
        self, torrent_hash: Text = None, **kwargs
    ) -> TorrentFilesList[TorrentFile]: ...
    def torrents_piece_states(
        self, torrent_hash: Text = None, **kwargs
    ) -> TorrentPieceInfoList[TorrentPieceData]: ...
    torrents_pieceStates = torrents_piece_states
    def torrents_piece_hashes(
        self, torrent_hash: Text = None, **kwargs
    ) -> TorrentPieceInfoList[TorrentPieceData]: ...
    torrents_pieceHashes = torrents_piece_hashes
    def torrents_add_trackers(
        self, torrent_hash: Text = None, urls: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_addTrackers = torrents_add_trackers
    def torrents_edit_tracker(
        self,
        torrent_hash: Text = None,
        original_url: Text = None,
        new_url: Text = None,
        **kwargs
    ) -> None: ...
    torrents_editTracker = torrents_edit_tracker
    def torrents_remove_trackers(
        self, torrent_hash: Text = None, urls: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_removeTrackers = torrents_remove_trackers
    def torrents_file_priority(
        self,
        torrent_hash: Text = None,
        file_ids: int | Iterable[Text | int] = None,
        priority: Text | int = None,
        **kwargs
    ) -> None: ...
    torrents_filePrio = torrents_file_priority
    def torrents_rename(
        self, torrent_hash: Text = None, new_torrent_name: Text = None, **kwargs
    ) -> None: ...
    def torrents_rename_file(
        self,
        torrent_hash: Text = None,
        file_id: Text | int = None,
        new_file_name: Text = None,
        old_path: Text = None,
        new_path: Text = None,
        **kwargs
    ) -> None: ...
    torrents_renameFile = torrents_rename_file
    def torrents_rename_folder(
        self,
        torrent_hash: Text = None,
        old_path: Text = None,
        new_path: Text = None,
        **kwargs
    ) -> None: ...
    torrents_renameFolder = torrents_rename_folder
    def torrents_export(self, torrent_hash: Text = None, **kwargs) -> bytes: ...
    def torrents_info(
        self,
        status_filter: TORRENT_STATUSES_T = None,
        category: Text = None,
        sort: Text = None,
        reverse: bool = None,
        limit: Text | int = None,
        offset: Text | int = None,
        torrent_hashes: Iterable[Text] = None,
        tag: Text = None,
        **kwargs
    ) -> TorrentInfoList[TorrentDictionary]: ...
    def torrents_resume(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    def torrents_pause(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    def torrents_delete(
        self,
        delete_files: bool = False,
        torrent_hashes: Iterable[Text] = None,
        **kwargs
    ) -> None: ...
    def torrents_recheck(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    def torrents_reannounce(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    def torrents_increase_priority(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_increasePrio = torrents_increase_priority
    def torrents_decrease_priority(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_decreasePrio = torrents_decrease_priority
    def torrents_top_priority(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_topPrio = torrents_top_priority
    def torrents_bottom_priority(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_bottomPrio = torrents_bottom_priority
    def torrents_download_limit(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> TorrentLimitsDictionary: ...
    torrents_downloadLimit = torrents_download_limit
    def torrents_set_download_limit(
        self, limit: Text | int = None, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_setDownloadLimit = torrents_set_download_limit
    def torrents_set_share_limits(
        self,
        ratio_limit: Text | int = None,
        seeding_time_limit: Text | int = None,
        torrent_hashes: Iterable[Text] = None,
        **kwargs
    ) -> None: ...
    torrents_setShareLimits = torrents_set_share_limits
    def torrents_upload_limit(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> TorrentLimitsDictionary: ...
    torrents_uploadLimit = torrents_upload_limit
    def torrents_set_upload_limit(
        self, limit: Text | int = None, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_setUploadLimit = torrents_upload_limit
    def torrents_set_location(
        self, location: Text = None, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_setLocation = torrents_set_location
    def torrents_set_save_path(
        self, save_path: Text = None, torrents_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_setSavePath = torrents_set_save_path
    def torrents_set_download_path(
        self,
        download_path: Text = None,
        torrents_hashes: Iterable[Text] = None,
        **kwargs
    ) -> None: ...
    torrents_setDownloadPath = torrents_set_download_path
    def torrents_set_category(
        self, category: Text = None, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_setCategory = torrents_set_category
    def torrents_set_auto_management(
        self, enable: bool = None, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_setAutoManagement = torrents_set_auto_management
    def torrents_toggle_sequential_download(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_toggleSequentialDownload = torrents_toggle_sequential_download
    def torrents_toggle_first_last_piece_priority(
        self, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_toggleFirstLastPiecePrio = torrents_toggle_first_last_piece_priority
    def torrents_set_force_start(
        self, enable: bool = None, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_setForceStart = torrents_set_force_start
    def torrents_set_super_seeding(
        self, enable: bool = None, torrent_hashes: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_setSuperSeeding = torrents_set_super_seeding
    def torrents_add_peers(
        self,
        peers: Iterable[Text] = None,
        torrent_hashes: Iterable[Text] = None,
        **kwargs
    ) -> TorrentsAddPeersDictionary: ...
    torrents_addPeers = torrents_add_peers
    def torrents_categories(self, **kwargs) -> TorrentCategoriesDictionary: ...
    def torrents_create_category(
        self,
        name: Text = None,
        save_path: Text = None,
        download_path: Text = None,
        enable_download_path: bool = None,
        **kwargs
    ) -> None: ...
    torrents_createCategory = torrents_create_category
    def torrents_edit_category(
        self,
        name: Text = None,
        save_path: Text = None,
        download_path: Text = None,
        enable_download_path: bool = None,
        **kwargs
    ) -> None: ...
    torrents_editCategory = torrents_edit_category
    def torrents_remove_categories(
        self, categories: Iterable[Text] = None, **kwargs
    ) -> None: ...
    torrents_removeCategories = torrents_remove_categories
    def torrents_tags(self, **kwargs) -> TagList[Tag]: ...
    def torrents_add_tags(
        self,
        tags: Iterable[Text] = None,
        torrent_hashes: Iterable[Text] = None,
        **kwargs
    ) -> None: ...
    torrents_addTags = torrents_add_tags
    def torrents_remove_tags(
        self,
        tags: Iterable[Text] = None,
        torrent_hashes: Iterable[Text] = None,
        **kwargs
    ) -> None: ...
    torrents_removeTags = torrents_remove_tags
    def torrents_create_tags(self, tags: Iterable[Text] = None, **kwargs) -> None: ...
    torrents_createTags = torrents_create_tags
    def torrents_delete_tags(self, tags: Iterable[Text] = None, **kwargs) -> None: ...
    torrents_deleteTags = torrents_delete_tags
