import errno
import logging
from os import path
import platform
from sys import version_info
from time import sleep

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

import pytest
import requests

from qbittorrentapi.exceptions import Forbidden403Error
from qbittorrentapi.exceptions import Conflict409Error
from qbittorrentapi.exceptions import InvalidRequest400Error
from qbittorrentapi.exceptions import TorrentFileError
from qbittorrentapi.exceptions import TorrentFileNotFoundError
from qbittorrentapi.exceptions import TorrentFilePermissionError
from qbittorrentapi.torrents import TorrentPropertiesDictionary
from qbittorrentapi.torrents import TrackersList
from qbittorrentapi.torrents import WebSeedsList
from qbittorrentapi.torrents import TorrentFilesList
from qbittorrentapi.torrents import TorrentPieceInfoList
from qbittorrentapi.torrents import TorrentInfoList
from qbittorrentapi.torrents import TorrentLimitsDictionary
from qbittorrentapi.torrents import TorrentsAddPeersDictionary
from qbittorrentapi.torrents import TorrentCategoriesDictionary
from qbittorrentapi.torrents import TagList

from tests.conftest import (
    check,
    new_torrent_standalone,
    retry,
    root_folder_torrent_hash,
    root_folder_torrent_file,
    torrent1_filename,
    torrent2_filename,
    torrent1_hash,
    torrent2_hash,
    torrent1_url,
    torrent2_url,
)
from tests.conftest import get_func, is_version_less_than


def disable_queueing(client):
    if client.app.preferences.queueing_enabled:
        client.app.preferences = dict(queueing_enabled=False)


def enable_queueing(client):
    if not client.app.preferences.queueing_enabled:
        client.app.preferences = dict(queueing_enabled=True)


@pytest.mark.parametrize(
    "client_func",
    (("torrents_add", "torrents_delete"), ("torrents.add", "torrents.delete")),
)
def test_add_delete(client, api_version, client_func):
    def download_file(url, filename=None, return_bytes=False):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with requests.get(url) as r:
                    r.raise_for_status()
                    if return_bytes:
                        return r.content
                    with open(path.expanduser("~/%s" % filename), "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024):
                            f.write(chunk)
            except (Exception if attempt < (max_attempts - 1) else ZeroDivisionError):
                pass  # throw away errors until we hit the retry limit
            else:
                return
        raise Exception("Download failed: %s" % url)

    def delete():
        get_func(client, client_func[1])(
            delete_files=True, torrent_hashes=torrent1_hash
        )
        get_func(client, client_func[1])(
            delete_files=True, torrent_hashes=torrent2_hash
        )
        check(
            lambda: [t.hash for t in client.torrents_info()],
            torrent2_hash,
            reverse=True,
            negate=True,
        )

    def check_torrents_added(f):
        def inner(**kwargs):
            try:
                f(**kwargs)
                check(
                    lambda: [t.hash for t in client.torrents_info()],
                    torrent1_hash,
                    reverse=True,
                )
                if kwargs.get("single", False) is False:
                    check(
                        lambda: [t.hash for t in client.torrents_info()],
                        torrent2_hash,
                        reverse=True,
                    )
            finally:
                sleep(1)
                delete()

        return inner

    @check_torrents_added
    def add_by_filename(single):
        download_file(url=torrent1_url, filename=torrent1_filename)
        download_file(url=torrent2_url, filename=torrent2_filename)
        files = ("~/%s" % torrent1_filename, "~/%s" % torrent2_filename)

        if single:
            assert get_func(client, client_func[0])(torrent_files=files[0]) == "Ok."
        else:
            assert get_func(client, client_func[0])(torrent_files=files) == "Ok."

    @check_torrents_added
    def add_by_filename_dict(single):
        download_file(url=torrent1_url, filename=torrent1_filename)
        download_file(url=torrent2_url, filename=torrent2_filename)

        if single:
            assert (
                get_func(client, client_func[0])(
                    torrent_files={torrent1_filename: "~/%s" % torrent1_filename}
                )
                == "Ok."
            )
        else:
            files = {
                torrent1_filename: "~/%s" % torrent1_filename,
                torrent2_filename: "~/%s" % torrent2_filename,
            }
            assert get_func(client, client_func[0])(torrent_files=files) == "Ok."

    @check_torrents_added
    def add_by_filehandles(single):
        download_file(url=torrent1_url, filename=torrent1_filename)
        download_file(url=torrent2_url, filename=torrent2_filename)
        files = (
            open(path.expanduser("~/" + torrent1_filename), "rb"),
            open(path.expanduser("~/" + torrent2_filename), "rb"),
        )

        if single:
            assert get_func(client, client_func[0])(torrent_files=files[0]) == "Ok."
        else:
            assert get_func(client, client_func[0])(torrent_files=files) == "Ok."

        for file in files:
            file.close()

    @check_torrents_added
    def add_by_bytes(single):
        files = (
            download_file(torrent1_url, return_bytes=True),
            download_file(torrent2_url, return_bytes=True),
        )

        if single:
            assert get_func(client, client_func[0])(torrent_files=files[0]) == "Ok."
        else:
            assert get_func(client, client_func[0])(torrent_files=files) == "Ok."

    @check_torrents_added
    def add_by_url(single):
        urls = (torrent1_url, torrent2_url)

        if single:
            get_func(client, client_func[0])(urls=urls[0])
        else:
            get_func(client, client_func[0])(urls=urls)

    if is_version_less_than("2.0.0", api_version, lteq=False):
        # something was wrong with torrents_add on v2.0.0 (the initial version)
        add_by_filename(single=False)
        add_by_filename(single=True)
        add_by_filename_dict(single=False)
        add_by_filename_dict(single=True)
        add_by_url(single=False)
        add_by_url(single=True)
        add_by_filehandles(single=False)
        add_by_filehandles(single=True)
        add_by_bytes(single=False)
        add_by_bytes(single=True)


def test_add_torrent_file_fail(client, monkeypatch):
    # torrent add is wonky in python2 because of support for raw bytes...
    if version_info[0] > 2:
        with pytest.raises(TorrentFileNotFoundError):
            client.torrents_add(torrent_files="/tmp/asdfasdfasdfasdf")

        with pytest.raises(TorrentFilePermissionError):
            client.torrents_add(torrent_files="/etc/shadow")

        if platform.python_implementation() == "CPython":
            with pytest.raises(TorrentFileError):

                def fake_open(*arg, **kwargs):
                    raise IOError(errno.ENODEV)

                with monkeypatch.context() as m:
                    m.setitem(__builtins__, "open", fake_open)
                    client.torrents_add(torrent_files="/etc/hosts")


def test_close_file_fail(client, monkeypatch, caplog):
    def fake_norm_files(files):
        return {object: object}, (object,)

    def post(*args, **kwargs):
        return "OK"

    if version_info[0] > 2:
        with monkeypatch.context() as m:
            m.setattr(client, "_normalize_torrent_files", fake_norm_files)
            m.setattr(client, "_post", post)
            with caplog.at_level(logging.WARNING, logger="qbittorrentapi"):
                client.torrents_add(torrent_files=object)
                assert "Failed to close file" in caplog.text


@pytest.mark.parametrize("keep_root_folder", (True, False, None))
@pytest.mark.parametrize(
    "content_layout", (None, "Original", "Subfolder", "NoSubfolder")
)
def test_add_options(client, api_version, keep_root_folder, content_layout):
    client.torrents_delete(torrent_hashes=root_folder_torrent_hash, delete_files=True)
    if is_version_less_than("2.3.0", api_version, lteq=True):
        client.torrents_create_tags("option-tag")
    torrent = next(
        new_torrent_standalone(
            torrent_hash=root_folder_torrent_hash,
            client=client,
            torrent_files=root_folder_torrent_file,
            save_path=path.expanduser("~/test_download/"),
            category="test_category",
            is_paused=True,
            upload_limit=1024,
            download_limit=2048,
            is_sequential_download=True,
            is_first_last_piece_priority=True,
            is_root_folder=keep_root_folder,
            rename="this is a new name for the torrent",
            use_auto_torrent_management=False,
            tags="option-tag",
            content_layout=content_layout,
            ratio_limit=2,
            seeding_time_limit=120,
        )
    )
    check(lambda: torrent.info.category, "test_category")
    check(
        lambda: torrent.info.state,
        ("pausedDL", "checkingResumeData"),
        reverse=True,
        any=True,
    )
    check(lambda: torrent.info.save_path, path.expanduser("~/test_download/"))
    check(lambda: torrent.info.up_limit, 1024)
    check(lambda: torrent.info.dl_limit, 2048)
    check(lambda: torrent.info.seq_dl, True)
    if is_version_less_than("2.0.1", api_version, lteq=True):
        check(lambda: torrent.info.f_l_piece_prio, True)
    if content_layout is None:
        check(
            lambda: torrent.files[0]["name"].startswith("root_folder"),
            keep_root_folder in {True, None},
        )
    check(lambda: torrent.info.name, "this is a new name for the torrent")
    check(lambda: torrent.info.auto_tmm, False)
    if is_version_less_than("2.6.2", api_version, lteq=True):
        check(lambda: torrent.info.tags, "option-tag")

    if is_version_less_than("2.7", api_version, lteq=True):
        # after web api v2.7...root dir is driven by content_layout
        if content_layout is None:
            should_root_dir_exists = keep_root_folder in {None, True}
        else:
            should_root_dir_exists = content_layout in {"Original", "Subfolder"}
    else:
        # before web api v2.7...it is driven by is_root_folder
        if content_layout is not None and keep_root_folder is None:
            should_root_dir_exists = content_layout in {"Original", "Subfolder"}
        else:
            should_root_dir_exists = keep_root_folder in {None, True}
    check(
        lambda: any(f["name"].startswith("root_folder") for f in torrent.files),
        should_root_dir_exists,
    )

    if is_version_less_than("2.8.1", api_version, lteq=True):
        check(lambda: torrent.info.ratio_limit, 2)
        check(lambda: torrent.info.seeding_time_limit, 120)


def test_properties(client, orig_torrent):
    props = client.torrents_properties(torrent_hash=orig_torrent.hash)
    assert isinstance(props, TorrentPropertiesDictionary)


def test_trackers(client, orig_torrent):
    trackers = client.torrents_trackers(torrent_hash=orig_torrent.hash)
    assert isinstance(trackers, TrackersList)


def test_webseeds(client, orig_torrent):
    web_seeds = client.torrents_webseeds(torrent_hash=orig_torrent.hash)
    assert isinstance(web_seeds, WebSeedsList)


def test_files(client, orig_torrent):
    files = client.torrents_files(torrent_hash=orig_torrent.hash)
    assert isinstance(files, TorrentFilesList)
    assert "availability" in files[0]

    assert all(file["id"] == file["index"] for file in files)


@pytest.mark.parametrize(
    "client_func", ("torrents_piece_states", "torrents_pieceStates")
)
def test_piece_states(client, orig_torrent, client_func):
    piece_states = get_func(client, client_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_states, TorrentPieceInfoList)


@pytest.mark.parametrize(
    "client_func", ("torrents_piece_hashes", "torrents_pieceHashes")
)
def test_piece_hashes(client, orig_torrent, client_func):
    piece_hashes = get_func(client, client_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_hashes, TorrentPieceInfoList)


@pytest.mark.parametrize("trackers", ("127.0.0.1", ("127.0.0.2", "127.0.0.3")))
@pytest.mark.parametrize(
    "client_func", ("torrents_add_trackers", "torrents_addTrackers")
)
def test_add_trackers(client, trackers, client_func, new_torrent):
    get_func(client, client_func)(torrent_hash=new_torrent.hash, urls=trackers)
    check(lambda: (t.url for t in new_torrent.trackers), trackers, reverse=True)


@pytest.mark.parametrize(
    "client_func", ("torrents_edit_tracker", "torrents_editTracker")
)
def test_edit_tracker(client, api_version, client_func, orig_torrent):
    if is_version_less_than(api_version, "2.2.0", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(
                torrent_hash=orig_torrent.hash,
                original_url="127.1.0.1",
                new_url="127.1.0.2",
            )
    else:
        orig_torrent.add_trackers("127.1.0.1")
        get_func(client, client_func)(
            torrent_hash=orig_torrent.hash,
            original_url="127.1.0.1",
            new_url="127.1.0.2",
        )
        check(lambda: (t.url for t in orig_torrent.trackers), "127.1.0.2", reverse=True)
        getattr(client, "torrents_remove_trackers")(
            torrent_hash=orig_torrent.hash, urls="127.1.0.2"
        )


@pytest.mark.parametrize(
    "trackers",
    (
        ("127.2.0.1",),
        ("127.2.0.2", "127.2.0.3"),
    ),
)
@pytest.mark.parametrize(
    "client_func", ("torrents_remove_trackers", "torrents_removeTrackers")
)
def test_remove_trackers(client, api_version, trackers, client_func, orig_torrent):
    if is_version_less_than(api_version, "2.2.0", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(torrent_hash=orig_torrent.hash, urls=trackers)
    else:
        orig_torrent.add_trackers(trackers)
        get_func(client, client_func)(torrent_hash=orig_torrent.hash, urls=trackers)
        check(
            lambda: (t.url for t in orig_torrent.trackers),
            trackers,
            reverse=True,
            negate=True,
        )


@pytest.mark.parametrize("client_func", ("torrents_file_priority", "torrents_filePrio"))
def test_file_priority(client, orig_torrent, orig_torrent_hash, client_func):
    get_func(client, client_func)(
        torrent_hash=orig_torrent_hash, file_ids=0, priority=6
    )
    check(lambda: orig_torrent.files[0].priority, 6)
    get_func(client, client_func)(
        torrent_hash=orig_torrent_hash, file_ids=0, priority=7
    )
    check(lambda: orig_torrent.files[0].priority, 7)


@pytest.mark.parametrize("new_name", (("new name 2", "new_name_2"),))
def test_rename(client, orig_torrent_hash, orig_torrent, new_name):
    client.torrents_rename(torrent_hash=orig_torrent_hash, new_torrent_name=new_name[0])
    check(lambda: orig_torrent.info.name.replace("+", " "), new_name[0])


@pytest.mark.parametrize("new_name", ("new name file 2", "new_name_file_2"))
@pytest.mark.parametrize("client_func", ("torrents_rename_file", "torrents_renameFile"))
def test_rename_file(
    client,
    api_version,
    new_torrent,
    new_name,
    client_func,
):
    if is_version_less_than(api_version, "2.4.0", lteq=False):
        with pytest.raises(NotImplementedError):
            getattr(client, client_func)(
                torrent_hash=new_torrent.hash, file_id=0, new_file_name=new_name
            )
    else:
        # pre-v4.3.3 rename_file signature
        getattr(client, client_func)(
            torrent_hash=new_torrent.hash, file_id=0, new_file_name=new_name
        )
        check(lambda: new_torrent.files[0].name.replace("+", " "), new_name)
        # test invalid file ID is rejected
        with pytest.raises(Conflict409Error):
            getattr(client, client_func)(
                torrent_hash=new_torrent.hash, file_id=10, new_file_name=new_name
            )
        # post-v4.3.3 rename_file signature
        getattr(client, client_func)(
            torrent_hash=new_torrent.hash,
            old_path=new_torrent.files[0].name,
            new_path=new_name + "_new",
        )
        check(lambda: new_torrent.files[0].name.replace("+", " "), new_name + "_new")
        # test invalid old_path is rejected
        with pytest.raises(Conflict409Error):
            getattr(client, client_func)(
                torrent_hash=new_torrent.hash, old_path="asdf", new_path="xcvb"
            )


@pytest.mark.parametrize("new_name", ("asdf zxcv", "asdf_zxcv"))
@pytest.mark.parametrize(
    "client_func", ("torrents_rename_folder", "torrents_renameFolder")
)
def test_rename_folder(client, app_version, new_torrent, new_name, client_func):
    if is_version_less_than(app_version, "v4.3.3", lteq=False):
        with pytest.raises(NotImplementedError):
            getattr(client, client_func)(
                torrent_hash="asdf", old_path="asdf", new_path="zxcv"
            )
    # need to ensure we're at least on v4.3.3 to run test
    if is_version_less_than("v4.3.2", app_version, lteq=False):
        # move the file in to a new folder
        orig_file_path = new_torrent.files[0].name
        new_folder = "qwer"
        client.torrents_rename_file(
            torrent_hash=new_torrent.hash,
            old_path=orig_file_path,
            new_path=new_folder + "/" + orig_file_path,
        )
        sleep(1)  # qBittorrent crashes if you make these calls too fast...
        # test rename that new folder
        getattr(client, client_func)(
            torrent_hash=new_torrent.hash,
            old_path=new_folder,
            new_path=new_name,
        )
        check(
            lambda: new_torrent.files[0].name.replace("+", " "),
            new_name + "/" + orig_file_path,
        )


@pytest.mark.parametrize("client_func", ("torrents_info", "torrents.info"))
def test_torrents_info(client, api_version, orig_torrent_hash, client_func):
    assert isinstance(get_func(client, client_func)(), TorrentInfoList)
    if "." in client_func:
        assert isinstance(get_func(client, client_func).all(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).downloading(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).completed(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).paused(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).active(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).inactive(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).resumed(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).stalled(), TorrentInfoList)
        assert isinstance(
            get_func(client, client_func).stalled_uploading(), TorrentInfoList
        )
        assert isinstance(
            get_func(client, client_func).stalled_downloading(), TorrentInfoList
        )

    if is_version_less_than(api_version, "2.0.1", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(torrent_hashes=orig_torrent_hash)


@pytest.mark.parametrize(
    "client_func",
    (("torrents_pause", "torrents_resume"), ("torrents.pause", "torrents.resume")),
)
def test_pause_resume(client, orig_torrent, orig_torrent_hash, client_func):
    get_func(client, client_func[0])(torrent_hashes=orig_torrent_hash)
    check(
        lambda: client.torrents_info(torrents_hashes=orig_torrent.hash)[0].state,
        ("stalledDL", "pausedDL"),
        any=True,
        check_limit=20,
    )

    get_func(client, client_func[1])(torrent_hashes=orig_torrent_hash)
    check(
        lambda: client.torrents_info(torrents_hashes=orig_torrent.hash)[0].state,
        "pausedDL",
        negate=True,
        check_limit=20,
    )


def test_action_for_all_torrents(client):
    client.torrents.resume.all()
    for torrent in client.torrents.info():
        check(
            lambda: client.torrents_info(torrents_hashes=torrent.hash)[0].state,
            ("pausedDL",),
            negate=True,
        )
    client.torrents.pause.all()
    for torrent in client.torrents.info():
        check(
            lambda: client.torrents_info(torrents_hashes=torrent.hash)[0].state,
            ("stalledDL", "pausedDL"),
            any=True,
        )


@pytest.mark.parametrize("client_func", ("torrents_recheck", "torrents.recheck"))
def test_recheck(client, orig_torrent_hash, client_func):
    get_func(client, client_func)(torrent_hashes=orig_torrent_hash)


@pytest.mark.parametrize("client_func", ("torrents_reannounce", "torrents.reannounce"))
def test_reannounce(client, api_version, orig_torrent_hash, client_func):
    if is_version_less_than(api_version, "2.0.2", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(torrent_hashes=orig_torrent_hash)
    else:
        get_func(client, client_func)(torrent_hashes=orig_torrent_hash)


@pytest.mark.parametrize(
    "client_func",
    (
        (
            "torrents_increase_priority",
            "torrents_decrease_priority",
            "torrents_top_priority",
            "torrents_bottom_priority",
        ),
        (
            "torrents_increasePrio",
            "torrents_decreasePrio",
            "torrents_topPrio",
            "torrents_bottomPrio",
        ),
    ),
)
def test_priority(client, new_torrent, client_func):
    disable_queueing(client)

    with pytest.raises(Conflict409Error):
        get_func(client, client_func[0])(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        get_func(client, client_func[1])(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        get_func(client, client_func[2])(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        get_func(client, client_func[3])(torrent_hashes=new_torrent.hash)

    enable_queueing(client)

    @retry
    def test1(current_priority):
        get_func(client, client_func[0])(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.priority < current_priority, True)

    @retry
    def test2(current_priority):
        get_func(client, client_func[1])(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.priority > current_priority, True)

    @retry
    def test3(current_priority):
        get_func(client, client_func[2])(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.priority < current_priority, True)

    @retry
    def test4(current_priority):
        get_func(client, client_func[3])(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.priority > current_priority, True)

    current_priority = new_torrent.info.priority
    test1(current_priority)
    current_priority = new_torrent.info.priority
    test2(current_priority)
    current_priority = new_torrent.info.priority
    test3(current_priority)
    current_priority = new_torrent.info.priority
    test4(current_priority)


@pytest.mark.parametrize(
    "client_func",
    (
        ("torrents_set_download_limit", "torrents_download_limit"),
        ("torrents_setDownloadLimit", "torrents_downloadLimit"),
        ("torrents.set_download_limit", "torrents.download_limit"),
        ("torrents.setDownloadLimit", "torrents.downloadLimit"),
    ),
)
def test_download_limit(client, client_func, orig_torrent):
    orig_download_limit = get_func(client, client_func[1])(
        torrent_hashes=orig_torrent.hash
    )[orig_torrent.hash]

    get_func(client, client_func[0])(torrent_hashes=orig_torrent.hash, limit=100)
    assert isinstance(
        get_func(client, client_func[1])(torrent_hashes=orig_torrent.hash),
        TorrentLimitsDictionary,
    )
    check(
        lambda: get_func(client, client_func[1])(torrent_hashes=orig_torrent.hash)[
            orig_torrent.hash
        ],
        100,
    )

    # reset download limit
    get_func(client, client_func[0])(
        torrent_hashes=orig_torrent.hash, limit=orig_download_limit
    )
    check(
        lambda: get_func(client, client_func[1])(torrent_hashes=orig_torrent.hash)[
            orig_torrent.hash
        ],
        orig_download_limit,
    )


@pytest.mark.parametrize(
    "client_func",
    (
        ("torrents_set_upload_limit", "torrents_upload_limit"),
        ("torrents_setUploadLimit", "torrents_uploadLimit"),
        ("torrents.set_upload_limit", "torrents.upload_limit"),
        ("torrents.setUploadLimit", "torrents.uploadLimit"),
    ),
)
def test_upload_limit(client, client_func, orig_torrent):
    orig_upload_limit = get_func(client, client_func[1])(
        torrent_hashes=orig_torrent.hash
    )[orig_torrent.hash]

    get_func(client, client_func[0])(torrent_hashes=orig_torrent.hash, limit=100)
    assert isinstance(
        get_func(client, client_func[1])(torrent_hashes=orig_torrent.hash),
        TorrentLimitsDictionary,
    )
    check(
        lambda: get_func(client, client_func[1])(torrent_hashes=orig_torrent.hash)[
            orig_torrent.hash
        ],
        100,
    )

    # reset upload limit
    get_func(client, client_func[0])(
        torrent_hashes=orig_torrent.hash, limit=orig_upload_limit
    )
    check(
        lambda: get_func(client, client_func[1])(torrent_hashes=orig_torrent.hash)[
            orig_torrent.hash
        ],
        orig_upload_limit,
    )


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_set_share_limits",
        "torrents_setShareLimits",
        "torrents.set_share_limits",
        "torrents.setShareLimits",
    ),
)
def test_set_share_limits(client, api_version, client_func, orig_torrent):
    if is_version_less_than(api_version, "2.0.1", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(
                ratio_limit=2, seeding_time_limit=5, torrent_hashes=orig_torrent.hash
            )
    else:
        get_func(client, client_func)(
            ratio_limit=2, seeding_time_limit=5, torrent_hashes=orig_torrent.hash
        )
        check(lambda: orig_torrent.info.max_ratio, 2)
        check(lambda: orig_torrent.info.max_seeding_time, 5)
        get_func(client, client_func)(
            ratio_limit=3, seeding_time_limit=6, torrent_hashes=orig_torrent.hash
        )
        check(lambda: orig_torrent.info.max_ratio, 3)
        check(lambda: orig_torrent.info.max_seeding_time, 6)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_set_location",
        "torrents_setLocation",
        "torrents.set_location",
        "torrents.setLocation",
    ),
)
def test_set_location(client, api_version, client_func, new_torrent):
    if is_version_less_than("2.0.1", api_version, lteq=False):
        home = path.expanduser("~")
        # whether the location is writable is only checked after version 2.0.1
        if is_version_less_than("2.0.1", api_version, lteq=False):
            with pytest.raises(Forbidden403Error):
                get_func(client, client_func)(
                    location="/etc/", torrent_hashes=new_torrent.hash
                )

        get_func(client, client_func)(
            location="%s/Downloads/1/" % home, torrent_hashes=new_torrent.hash
        )
        check(lambda: new_torrent.info.save_path, "%s/Downloads/1/" % home)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_set_category",
        "torrents_setCategory",
        "torrents.set_category",
        "torrents.setCategory",
    ),
)
@pytest.mark.parametrize("name", ("awesome cat", "awesome_cat"))
def test_set_category(client, client_func, name, orig_torrent):
    with pytest.raises(Conflict409Error):
        get_func(client, client_func)(
            category="/!@#$%^&*(", torrent_hashes=orig_torrent.hash
        )

    client.torrents_create_category(name=name)
    try:
        get_func(client, client_func)(category=name, torrent_hashes=orig_torrent.hash)
        check(lambda: orig_torrent.info.category.replace("+", " "), name)
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_set_auto_management",
        "torrents_setAutoManagement",
        "torrents.set_auto_management",
        "torrents.setAutoManagement",
    ),
)
def test_torrents_set_auto_management(client, client_func, orig_torrent):
    current_setting = orig_torrent.info.auto_tmm
    get_func(client, client_func)(
        enable=(not current_setting), torrent_hashes=orig_torrent.hash
    )
    check(lambda: orig_torrent.info.auto_tmm, (not current_setting))
    get_func(client, client_func)(
        enable=False, torrent_hashes=orig_torrent.hash
    )  # leave on False


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_toggle_sequential_download",
        "torrents_toggleSequentialDownload",
        "torrents.toggle_sequential_download",
        "torrents.toggleSequentialDownload",
    ),
)
def test_toggle_sequential_download(client, client_func, orig_torrent):
    current_setting = orig_torrent.info.seq_dl
    get_func(client, client_func)(torrent_hashes=orig_torrent.hash)
    check(lambda: orig_torrent.info.seq_dl, not current_setting)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_toggle_first_last_piece_priority",
        "torrents_toggleFirstLastPiecePrio",
        "torrents.toggle_first_last_piece_priority",
        "torrents.toggleFirstLastPiecePrio",
    ),
)
def test_toggle_first_last_piece_priority(
    client, api_version, client_func, new_torrent
):
    if is_version_less_than("2.0.0", api_version, lteq=False):
        current_setting = new_torrent.info.f_l_piece_prio
        sleep(1)
        get_func(client, client_func)(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.f_l_piece_prio, not current_setting)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_set_force_start",
        "torrents_setForceStart",
        "torrents.set_force_start",
        "torrents.setForceStart",
    ),
)
def test_set_force_start(client, client_func, orig_torrent):
    current_setting = orig_torrent.info.force_start
    get_func(client, client_func)(
        enable=(not current_setting), torrent_hashes=orig_torrent.hash
    )
    check(lambda: orig_torrent.info.force_start, not current_setting)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_set_super_seeding",
        "torrents_setSuperSeeding",
        "torrents.set_super_seeding",
        "torrents.setSuperSeeding",
    ),
)
def test_set_super_seeding(client, client_func, orig_torrent):
    # this may or may not actually be working....
    get_func(client, client_func)(enable=False, torrent_hashes=orig_torrent.hash)
    check(lambda: orig_torrent.info.force_start, False)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_add_peers",
        "torrents_addPeers",
        "torrents.add_peers",
        "torrents.addPeers",
    ),
)
@pytest.mark.parametrize(
    "peers", ("127.0.0.1:5000", ("127.0.0.1:5000", "127.0.0.2:5000"), "127.0.0.1")
)
def test_torrents_add_peers(client, api_version, orig_torrent, client_func, peers):
    if is_version_less_than(api_version, "2.3.0", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(peers=peers, torrent_hashes=orig_torrent.hash)
    else:
        if all(map(lambda p: ":" not in p, peers)):
            with pytest.raises(InvalidRequest400Error):
                get_func(client, client_func)(
                    peers=peers, torrent_hashes=orig_torrent.hash
                )
        else:
            p = get_func(client, client_func)(
                peers=peers, torrent_hashes=orig_torrent.hash
            )
            # can only actually verify the peer was added if it's a valid peer
            # check(lambda: client.sync_torrent_peers(torrent_hash=orig_torrent_hash)['peers'], peers, reverse=True)
            assert isinstance(p, TorrentsAddPeersDictionary)


def test_categories1(client, api_version):
    if is_version_less_than(api_version, "2.1.1", lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_categories()
    else:
        assert isinstance(client.torrents_categories(), TorrentCategoriesDictionary)


def test_categories2(client, api_version):
    if is_version_less_than(api_version, "2.1.1", lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrent_categories.categories
    else:
        name = "new_category"
        client.torrent_categories.categories = {"name": name, "savePath": "/tmp"}
        assert name in client.torrent_categories.categories
        client.torrent_categories.categories = {"name": name, "savePath": "/tmp/new"}
        assert client.torrent_categories.categories[name]["savePath"] == "/tmp/new"
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_create_category",
        "torrents_createCategory",
        "torrent_categories.create_category",
        "torrent_categories.createCategory",
    ),
)
@pytest.mark.parametrize("save_path", (None, "", "/tmp/"))
@pytest.mark.parametrize("name", ("name", "name 1"))
def test_create_categories(
    client, api_version, orig_torrent, client_func, save_path, name
):
    extra_kwargs = dict(save_path=save_path)
    if is_version_less_than(api_version, "2.1.0", lteq=False) and save_path is not None:
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(name=name, save_path=save_path)
        extra_kwargs = {}

    try:
        get_func(client, client_func)(name=name, **extra_kwargs)
        client.torrents_set_category(torrent_hashes=orig_torrent.hash, category=name)
        check(lambda: orig_torrent.info.category.replace("+", " "), name)
        if is_version_less_than("2.1.1", api_version):
            check(
                lambda: [n.replace("+", " ") for n in client.torrents_categories()],
                name,
                reverse=True,
            )
            check(
                lambda: (cat.savePath for cat in client.torrents_categories().values()),
                save_path or "",
                reverse=True,
            )
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_edit_category",
        "torrents_editCategory",
        "torrent_categories.edit_category",
        "torrent_categories.editCategory",
    ),
)
@pytest.mark.parametrize("save_path", ("", "/tmp/"))
@pytest.mark.parametrize("name", ("editcategory",))
def test_edit_category(client, api_version, client_func, save_path, name):
    if is_version_less_than(api_version, "2.1.0", lteq=False) and save_path is not None:
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(name=name, save_path=save_path)

    if is_version_less_than("2.1.1", api_version):
        try:
            client.torrents_create_category(name=name, save_path="/tmp/tmp")
            get_func(client, client_func)(name=name, save_path=save_path)
            check(
                lambda: [n.replace("+", " ") for n in client.torrents_categories()],
                name,
                reverse=True,
            )
            check(
                lambda: (cat.savePath for cat in client.torrents_categories().values()),
                save_path or "",
                reverse=True,
            )
        finally:
            client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_remove_categories",
        "torrents_removeCategories",
        "torrent_categories.remove_categories",
        "torrent_categories.removeCategories",
    ),
)
@pytest.mark.parametrize("categories", (("category1",), ("category1", "category 2")))
def test_remove_category(client, api_version, orig_torrent, client_func, categories):
    for name in categories:
        client.torrents_create_category(name=name)
    orig_torrent.set_category(category=categories[0])
    get_func(client, client_func)(categories=categories)
    if is_version_less_than("2.1.1", api_version):
        check(
            lambda: [n.replace("+", " ") for n in client.torrents_categories()],
            categories,
            reverse=True,
            negate=True,
        )
    check(lambda: orig_torrent.info.category, categories[0], negate=True)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_tags",
        "torrent_tags.tags",
    ),
)
def test_tags(client, api_version, client_func):
    if is_version_less_than(api_version, "2.3.0", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)()
    else:
        try:
            assert isinstance(get_func(client, client_func)(), TagList)
        except:
            assert isinstance(get_func(client, client_func), TagList)


def test_add_tag_though_property(client, api_version):
    name = "newtag"
    if is_version_less_than(api_version, "2.3.0", lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrent_tags.tags = name
    else:
        client.torrent_tags.tags = name
        assert name in client.torrent_tags.tags
        client.torrent_tags.delete_tags(name)
        assert name not in client.torrent_tags.tags


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_add_tags",
        "torrents_addTags",
        "torrent_tags.add_tags",
        "torrent_tags.addTags",
    ),
)
@pytest.mark.parametrize("tags", (("tag1",), ("tag1", "tag 2")))
def test_add_tags(client, api_version, orig_torrent, client_func, tags):
    if is_version_less_than(api_version, "2.3.0", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(tags=tags, torrent_hashes=orig_torrent.hash)
    else:
        try:
            get_func(client, client_func)(tags=tags, torrent_hashes=orig_torrent.hash)
            check(lambda: orig_torrent.info.tags, tags, reverse=True)
        finally:
            client.torrents_delete_tags(tags=tags)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_remove_tags",
        "torrents_removeTags",
        "torrent_tags.remove_tags",
        "torrent_tags.removeTags",
    ),
)
@pytest.mark.parametrize("tags", (("tag1",), ("tag1", "tag 2")))
def test_remove_tags(client, api_version, orig_torrent, client_func, tags):
    if is_version_less_than(api_version, "2.3.0", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(tags=tags, torrent_hashes=orig_torrent.hash)
    else:
        try:
            orig_torrent.add_tags(tags=tags)
            get_func(client, client_func)(tags=tags, torrent_hashes=orig_torrent.hash)
            check(lambda: orig_torrent.info.tags, tags, reverse=True, negate=True)
        finally:
            client.torrents_delete_tags(tags=tags)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_create_tags",
        "torrents_createTags",
        "torrent_tags.create_tags",
        "torrent_tags.createTags",
    ),
)
@pytest.mark.parametrize("tags", (("tag1",), ("tag1", "tag 2")))
def test_create_tags(client, api_version, client_func, tags):
    if is_version_less_than(api_version, "2.3.0", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(tags=tags)
    else:
        try:
            get_func(client, client_func)(tags=tags)
            check(lambda: client.torrents_tags(), tags, reverse=True)
        finally:
            client.torrents_delete_tags(tags=tags)


@pytest.mark.parametrize(
    "client_func",
    (
        "torrents_delete_tags",
        "torrents_deleteTags",
        "torrent_tags.delete_tags",
        "torrent_tags.deleteTags",
    ),
)
@pytest.mark.parametrize("tags", (("tag1",), ("tag1", "tag 2")))
def test_delete_tags(client, api_version, client_func, tags):
    if is_version_less_than(api_version, "2.3.0", lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(tags=tags)
    else:
        client.torrents_create_tags(tags=tags)
        get_func(client, client_func)(tags=tags)
        check(lambda: client.torrents_tags(), tags, reverse=True, negate=True)
