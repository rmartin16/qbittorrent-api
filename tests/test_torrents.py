import errno
import platform
import sys
from time import sleep

import pytest
import requests

from qbittorrentapi import APINames
from qbittorrentapi._version_support import v
from qbittorrentapi.exceptions import (
    Conflict409Error,
    Forbidden403Error,
    InvalidRequest400Error,
    TorrentFileError,
    TorrentFileNotFoundError,
    TorrentFilePermissionError,
)
from qbittorrentapi.torrents import (
    TagList,
    TorrentCategoriesDictionary,
    TorrentFilesList,
    TorrentInfoList,
    TorrentLimitsDictionary,
    TorrentPieceInfoList,
    TorrentPropertiesDictionary,
    TorrentsAddPeersDictionary,
    TrackersList,
    WebSeedsList,
)
from tests.conftest import (
    ROOT_FOLDER_TORRENT_FILE,
    ROOT_FOLDER_TORRENT_HASH,
    TORRENT1_FILENAME,
    TORRENT1_HASH,
    TORRENT1_URL,
    TORRENT2_FILENAME,
    TORRENT2_HASH,
    TORRENT2_URL,
    new_torrent_standalone,
)
from tests.utils import check, mkpath, retry


def disable_queueing(client):
    if client.app.preferences.queueing_enabled:
        client.app.set_preferences(dict(queueing_enabled=False))


def enable_queueing(client):
    if not client.app.preferences.queueing_enabled:
        client.app.set_preferences(dict(queueing_enabled=True))


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    all_dotted_methods = {
        meth
        for namespace in [APINames.Torrents, "torrent_tags", "torrent_categories"]
        for meth in dir(getattr(client, namespace))
    }

    for meth in [meth for meth in dir(client) if meth.startswith("torrents_")]:
        assert meth.removeprefix("torrents_") in all_dotted_methods


# something was wrong with torrents_add on v2.0.0 (the initial version)
@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "add_func, delete_func",
    [("torrents_add", "torrents_delete"), ("torrents.add", "torrents.delete")],
)
def test_add_delete(client, add_func, delete_func, tmp_path):
    def download_file(url, filename=None, return_bytes=False):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with requests.get(url, timeout=30) as r:
                    r.raise_for_status()
                    if return_bytes:
                        return r.content
                    with open(mkpath(tmp_path, filename), "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024):
                            f.write(chunk)
            except Exception if attempt < (max_attempts - 1) else ZeroDivisionError:
                pass  # throw away errors until we hit the retry limit
            else:
                return
        raise Exception(f"Download failed: {url}")

    def delete():
        client.func(delete_func)(delete_files=True, torrent_hashes=TORRENT1_HASH)
        client.func(delete_func)(delete_files=True, torrent_hashes=TORRENT2_HASH)
        check(
            lambda: [t.hash for t in client.torrents_info()],
            TORRENT2_HASH,
            reverse=True,
            negate=True,
        )

    def check_torrents_added(f):
        def inner(**kwargs):
            try:
                f(**kwargs)
                check(
                    lambda: [t.hash for t in client.torrents_info()],
                    TORRENT1_HASH,
                    reverse=True,
                )
                if kwargs.get("single", False) is False:
                    check(
                        lambda: [t.hash for t in client.torrents_info()],
                        TORRENT2_HASH,
                        reverse=True,
                    )
            finally:
                delete()

        return inner

    @retry()
    @check_torrents_added
    def add_by_filename(single):
        download_file(url=TORRENT1_URL, filename=TORRENT1_FILENAME)
        download_file(url=TORRENT2_URL, filename=TORRENT2_FILENAME)
        files = (
            mkpath(tmp_path, TORRENT1_FILENAME),
            mkpath(tmp_path, TORRENT2_FILENAME),
        )

        if single:
            assert client.func(add_func)(torrent_files=files[0]) == "Ok."
        else:
            assert client.func(add_func)(torrent_files=files) == "Ok."

    @retry()
    @check_torrents_added
    def add_by_filename_dict(single):
        download_file(url=TORRENT1_URL, filename=TORRENT1_FILENAME)
        download_file(url=TORRENT2_URL, filename=TORRENT2_FILENAME)

        if single:
            assert (
                client.func(add_func)(
                    torrent_files={
                        TORRENT1_FILENAME: mkpath(tmp_path, TORRENT1_FILENAME)
                    }
                )
                == "Ok."
            )
        else:
            files = {
                TORRENT1_FILENAME: mkpath(tmp_path, TORRENT1_FILENAME),
                TORRENT2_FILENAME: mkpath(tmp_path, TORRENT2_FILENAME),
            }
            assert client.func(add_func)(torrent_files=files) == "Ok."

    @retry()
    @check_torrents_added
    def add_by_filehandles(single):
        download_file(url=TORRENT1_URL, filename=TORRENT1_FILENAME)
        download_file(url=TORRENT2_URL, filename=TORRENT2_FILENAME)
        files = (
            open(mkpath(tmp_path, TORRENT1_FILENAME), "rb"),  # noqa: SIM115
            open(mkpath(tmp_path, TORRENT2_FILENAME), "rb"),  # noqa: SIM115
        )

        if single:
            assert client.func(add_func)(torrent_files=files[0]) == "Ok."
        else:
            assert client.func(add_func)(torrent_files=files) == "Ok."

        for file in files:
            file.close()

    @retry()
    @check_torrents_added
    def add_by_bytes(single):
        files = (
            download_file(TORRENT1_URL, return_bytes=True),
            download_file(TORRENT2_URL, return_bytes=True),
        )

        if single:
            assert client.func(add_func)(torrent_files=files[0]) == "Ok."
        else:
            assert client.func(add_func)(torrent_files=files) == "Ok."

    @retry()
    @check_torrents_added
    def add_by_url(single):
        urls = (TORRENT1_URL, TORRENT2_URL)

        if single:
            client.func(add_func)(urls=urls[0])
        else:
            client.func(add_func)(urls=urls)

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
    with pytest.raises(TorrentFileNotFoundError):
        client.torrents_add(torrent_files="/tmp/asdfasdfasdfasdf")

    with pytest.raises(TorrentFilePermissionError):
        client.torrents_add(torrent_files="/etc/shadow")

    if platform.python_implementation() == "CPython":
        with pytest.raises(TorrentFileError):

            def fake_open(*arg, **kwargs):
                raise OSError(errno.ENODEV)

            with monkeypatch.context() as m:
                m.setitem(__builtins__, "open", fake_open)
                client.torrents_add(torrent_files="/etc/hosts")


@pytest.mark.parametrize("keep_root_folder", [True, False, None])
@pytest.mark.parametrize(
    "content_layout", [None, "Original", "Subfolder", "NoSubfolder"]
)
def test_add_options(client, api_version, keep_root_folder, content_layout, tmp_path):
    @retry(3)
    def do_test():
        if v(api_version) >= v("2.3.0"):
            client.torrents_create_tags("option-tag")
        new_torrent = new_torrent_standalone(
            client=client,
            torrent_files=ROOT_FOLDER_TORRENT_FILE,
            torrent_hash=ROOT_FOLDER_TORRENT_HASH,
            save_path=mkpath(tmp_path, "test_download"),
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

        with new_torrent as torrent:
            check(lambda: torrent.info.category, "test_category")
            check(
                lambda: torrent.info.state,
                ("pausedDL", "checkingResumeData"),
                reverse=True,
                any=True,
            )
            check(
                lambda: mkpath(torrent.info.save_path),
                mkpath(tmp_path, "test_download"),
            )
            check(lambda: torrent.info.up_limit, 1024)
            check(lambda: torrent.info.dl_limit, 2048)
            check(lambda: torrent.info.seq_dl, True)
            if v(api_version) >= v("2.0.1"):
                check(lambda: torrent.info.f_l_piece_prio, True)
            if content_layout is None:
                check(
                    lambda: torrent.files[0]["name"].startswith("root_folder"),
                    keep_root_folder in {True, None},
                )
            check(lambda: torrent.info.name, "this is a new name for the torrent")
            check(lambda: torrent.info.auto_tmm, False)
            if v(api_version) >= v("2.6.2"):
                check(lambda: torrent.info.tags, "option-tag")

            if v(api_version) >= v("2.7"):
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

            if v(api_version) >= v("2.8.1"):
                check(lambda: torrent.info.ratio_limit, 2)
                check(lambda: torrent.info.seeding_time_limit, 120)

    do_test()


@pytest.mark.skipif_before_api_version("2.8.4")
@pytest.mark.parametrize("use_download_path", [None, True, False])
def test_torrents_add_download_path(client, use_download_path, tmp_path):
    client.torrents_delete(torrent_hashes=ROOT_FOLDER_TORRENT_HASH, delete_files=True)
    save_path = mkpath(tmp_path, "down_path_save_path_test")
    download_path = mkpath(tmp_path, "down_path_test")
    new_torrent = new_torrent_standalone(
        client=client,
        torrent_hash=ROOT_FOLDER_TORRENT_HASH,
        torrent_files=ROOT_FOLDER_TORRENT_FILE,
        download_path=download_path,
        use_download_path=use_download_path,
        test_download_limit=1024,
        save_path=save_path,
    )

    with new_torrent as torrent:
        if use_download_path is False:
            check(
                lambda: mkpath(torrent.info.download_path), download_path, negate=True
            )
        else:
            check(lambda: mkpath(torrent.info.download_path), download_path)


@pytest.mark.skipif_before_api_version("2.9.3")
@pytest.mark.parametrize("count_func", ["torrents_count", "torrents.count"])
def test_count(client, count_func):
    assert client.func(count_func)() == 1


@pytest.mark.skipif_after_api_version("2.9.3")
@pytest.mark.parametrize("count_func", ["torrents_count", "torrents.count"])
def test_count_not_implemented(client, count_func):
    with pytest.raises(NotImplementedError):
        assert client.func(count_func)() == 1


@pytest.mark.parametrize(
    "properties_func", ["torrents_properties", "torrents.properties"]
)
def test_properties(client, orig_torrent, properties_func):
    props = client.func(properties_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(props, TorrentPropertiesDictionary)


@pytest.mark.parametrize("trackers_func", ["torrents_trackers", "torrents.trackers"])
def test_trackers(client, orig_torrent, trackers_func):
    trackers = client.func(trackers_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(trackers, TrackersList)


@pytest.mark.parametrize("trackers_func", ["torrents_trackers", "torrents.trackers"])
def test_trackers_slice(client, orig_torrent, trackers_func):
    trackers = client.func(trackers_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(trackers[1:2], TrackersList)


@pytest.mark.parametrize("webseeds_func", ["torrents_webseeds", "torrents.webseeds"])
def test_webseeds(client, orig_torrent, webseeds_func):
    web_seeds = client.func(webseeds_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(web_seeds, WebSeedsList)


@pytest.mark.parametrize("webseeds_func", ["torrents_webseeds", "torrents.webseeds"])
def test_webseeds_slice(client, orig_torrent, webseeds_func):
    web_seeds = client.func(webseeds_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(web_seeds[1:2], WebSeedsList)


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize(
    "add_webseeds_func",
    [
        "torrents_add_webseeds",
        "torrents_addWebSeeds",
        "torrents.add_webseeds",
        "torrents.addWebSeeds",
    ],
)
@pytest.mark.parametrize(
    "webseeds",
    [
        "http://example/webseedone",
        ["http://example/webseedone", "http://example/webseedtwo"],
    ],
)
def test_add_webseeds(client, new_torrent, add_webseeds_func, webseeds):
    assert new_torrent.webseeds == WebSeedsList([])
    client.func(add_webseeds_func)(torrent_hash=new_torrent.hash, urls=webseeds)
    assert sorted([w.url for w in new_torrent.webseeds]) == (
        webseeds if isinstance(webseeds, list) else [webseeds]
    )


@pytest.mark.skipif_after_api_version("2.11.3")
@pytest.mark.parametrize(
    "add_webseeds_func",
    [
        "torrents_add_webseeds",
        "torrents_addWebSeeds",
        "torrents.add_webseeds",
        "torrents.addWebSeeds",
    ],
)
def test_add_webseeds_not_implemented(client, orig_torrent, add_webseeds_func):
    with pytest.raises(NotImplementedError):
        client.func(add_webseeds_func)()


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize(
    "edit_webseed_func",
    [
        "torrents_edit_webseed",
        "torrents_editWebSeed",
        "torrents.edit_webseed",
        "torrents.editWebSeed",
    ],
)
def test_edit_webseeds(client, new_torrent, edit_webseed_func):
    assert new_torrent.webseeds == WebSeedsList([])
    new_torrent.add_webseeds(urls="http://example/asdf")
    client.func(edit_webseed_func)(
        torrent_hash=new_torrent.hash,
        orig_url="http://example/asdf",
        new_url="http://example/qwer",
    )
    assert new_torrent.webseeds[0].url == "http://example/qwer"


@pytest.mark.skipif_after_api_version("2.11.3")
@pytest.mark.parametrize(
    "edit_webseed_func",
    [
        "torrents_edit_webseed",
        "torrents_editWebSeed",
        "torrents.edit_webseed",
        "torrents.editWebSeed",
    ],
)
def test_edit_webseed_not_implemented(client, orig_torrent, edit_webseed_func):
    with pytest.raises(NotImplementedError):
        client.func(edit_webseed_func)()


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize(
    "remove_webseeds_func",
    [
        "torrents_remove_webseeds",
        "torrents_removeWebSeeds",
        "torrents.remove_webseeds",
        "torrents.removeWebSeeds",
    ],
)
@pytest.mark.parametrize(
    "webseeds",
    [
        "http://example/webseedone",
        ["http://example/webseedone", "http://example/webseedtwo"],
    ],
)
def test_remove_webseeds(client, new_torrent, remove_webseeds_func, webseeds):
    assert new_torrent.webseeds == WebSeedsList([])
    new_torrent.add_webseeds(
        urls=[
            "http://example/webseedone",
            "http://example/webseedtwo",
            "http://example/webseedthree",
        ]
    )
    client.func(remove_webseeds_func)(torrent_hash=new_torrent.hash, urls=webseeds)
    for webseed in webseeds if isinstance(webseeds, list) else [webseeds]:
        assert webseed not in {w.url for w in new_torrent.webseeds}


@pytest.mark.skipif_after_api_version("2.11.3")
@pytest.mark.parametrize(
    "remove_webseeds_func",
    [
        "torrents_remove_webseeds",
        "torrents_removeWebSeeds",
        "torrents.remove_webseeds",
        "torrents.removeWebSeeds",
    ],
)
def test_remove_webseeds_not_implemented(client, orig_torrent, remove_webseeds_func):
    with pytest.raises(NotImplementedError):
        client.func(remove_webseeds_func)()


@pytest.mark.parametrize("files_func", ["torrents_files", "torrents.files"])
def test_files(client, orig_torrent, files_func):
    files = client.func(files_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(files, TorrentFilesList)
    assert "availability" in files[0]
    assert all(file["id"] == file["index"] for file in files)


@pytest.mark.parametrize("files_func", ["torrents_files", "torrents.files"])
def test_files_slice(client, orig_torrent, files_func):
    files = client.func(files_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(files[1:2], TorrentFilesList)


@pytest.mark.parametrize(
    "piece_state_func",
    [
        "torrents_piece_states",
        "torrents_pieceStates",
        "torrents.piece_states",
        "torrents.pieceStates",
    ],
)
def test_piece_states(client, orig_torrent, piece_state_func):
    piece_states = client.func(piece_state_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_states, TorrentPieceInfoList)


@pytest.mark.parametrize(
    "piece_state_func",
    [
        "torrents_piece_states",
        "torrents_pieceStates",
        "torrents.piece_states",
        "torrents.pieceStates",
    ],
)
def test_piece_states_slice(client, orig_torrent, piece_state_func):
    piece_states = client.func(piece_state_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_states[1:2], TorrentPieceInfoList)


@pytest.mark.parametrize(
    "piece_hashes_func",
    [
        "torrents_piece_hashes",
        "torrents_pieceHashes",
        "torrents.piece_hashes",
        "torrents.pieceHashes",
    ],
)
def test_piece_hashes(client, orig_torrent, piece_hashes_func):
    piece_hashes = client.func(piece_hashes_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_hashes, TorrentPieceInfoList)


@pytest.mark.parametrize(
    "piece_hashes_func",
    [
        "torrents_piece_hashes",
        "torrents_pieceHashes",
        "torrents.piece_hashes",
        "torrents.pieceHashes",
    ],
)
def test_piece_hashes_slice(client, orig_torrent, piece_hashes_func):
    piece_hashes = client.func(piece_hashes_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_hashes[1:2], TorrentPieceInfoList)


@pytest.mark.parametrize("trackers", ["127.0.0.1", ["127.0.0.2", "127.0.0.3"]])
@pytest.mark.parametrize(
    "add_trackers_func",
    [
        "torrents_add_trackers",
        "torrents_addTrackers",
        "torrents.add_trackers",
        "torrents.addTrackers",
    ],
)
def test_add_trackers(client, trackers, new_torrent, add_trackers_func):
    client.func(add_trackers_func)(torrent_hash=new_torrent.hash, urls=trackers)
    check(lambda: (t.url for t in new_torrent.trackers), trackers, reverse=True)


@pytest.mark.skipif_before_api_version("2.2.0")
@pytest.mark.parametrize(
    "edit_trackers_func",
    [
        "torrents_edit_tracker",
        "torrents_editTracker",
        "torrents.edit_tracker",
        "torrents.editTracker",
    ],
)
def test_edit_tracker(client, orig_torrent, edit_trackers_func):
    orig_torrent.add_trackers("127.1.0.1")
    client.func(edit_trackers_func)(
        torrent_hash=orig_torrent.hash,
        original_url="127.1.0.1",
        new_url="127.1.0.2",
    )
    check(lambda: (t.url for t in orig_torrent.trackers), "127.1.0.2", reverse=True)
    client.torrents_remove_trackers(torrent_hash=orig_torrent.hash, urls="127.1.0.2")


@pytest.mark.skipif_after_api_version("2.2.0")
@pytest.mark.parametrize(
    "edit_trackers_func",
    [
        "torrents_edit_tracker",
        "torrents_editTracker",
        "torrents.edit_tracker",
        "torrents.editTracker",
    ],
)
def test_edit_tracker_not_implemented(client, orig_torrent, edit_trackers_func):
    with pytest.raises(NotImplementedError):
        client.func(edit_trackers_func)()


@pytest.mark.skipif_before_api_version("2.2.0")
@pytest.mark.parametrize(
    "trackers",
    [
        ["127.2.0.1"],
        ["127.2.0.2", "127.2.0.3"],
    ],
)
@pytest.mark.parametrize(
    "remove_trackers_func",
    [
        "torrents_remove_trackers",
        "torrents_removeTrackers",
        "torrents.remove_trackers",
        "torrents.removeTrackers",
    ],
)
def test_remove_trackers(client, trackers, orig_torrent, remove_trackers_func):
    orig_torrent.add_trackers(trackers)
    client.func(remove_trackers_func)(torrent_hash=orig_torrent.hash, urls=trackers)
    check(
        lambda: (t.url for t in orig_torrent.trackers),
        trackers,
        reverse=True,
        negate=True,
    )


@pytest.mark.skipif_after_api_version("2.2.0")
@pytest.mark.parametrize(
    "remove_trackers_func",
    [
        "torrents_remove_trackers",
        "torrents_removeTrackers",
        "torrents.remove_trackers",
        "torrents.removeTrackers",
    ],
)
def test_remove_trackers_not_implemented(client, orig_torrent, remove_trackers_func):
    with pytest.raises(NotImplementedError):
        client.func(remove_trackers_func)()


@pytest.mark.parametrize(
    "file_prio_func",
    [
        "torrents_file_priority",
        "torrents_filePrio",
        "torrents.file_priority",
        "torrents.filePrio",
    ],
)
def test_file_priority(client, orig_torrent, file_prio_func):
    client.func(file_prio_func)(torrent_hash=orig_torrent.hash, file_ids=0, priority=6)
    check(lambda: orig_torrent.files[0].priority, 6)
    client.func(file_prio_func)(torrent_hash=orig_torrent.hash, file_ids=0, priority=7)
    check(lambda: orig_torrent.files[0].priority, 7)


@pytest.mark.parametrize("new_name", ["new name 2", "new_name_2"])
@pytest.mark.parametrize("rename_func", ["torrents_rename", "torrents.rename"])
def test_rename(client, new_torrent, new_name, rename_func):
    client.func(rename_func)(torrent_hash=new_torrent.hash, new_torrent_name=new_name)
    check(lambda: new_torrent.info.name.replace("+", " "), new_name)


@pytest.mark.skipif_before_api_version("2.4.0")
@pytest.mark.parametrize("new_name", ["new name file 2", "new_name_file_2"])
@pytest.mark.parametrize(
    "rename_file_func",
    [
        "torrents_rename_file",
        "torrents_renameFile",
        "torrents.rename_file",
        "torrents.renameFile",
    ],
)
def test_rename_file(
    client,
    new_torrent,
    new_name,
    rename_file_func,
):
    # pre-v4.3.3 rename_file signature
    client.func(rename_file_func)(
        torrent_hash=new_torrent.hash, file_id=0, new_file_name=new_name
    )
    check(lambda: new_torrent.files[0].name.replace("+", " "), new_name)
    # test invalid file ID is rejected
    with pytest.raises(Conflict409Error):
        client.func(rename_file_func)(
            torrent_hash=new_torrent.hash, file_id=10, new_file_name=new_name
        )
    # post-v4.3.3 rename_file signature
    new_new_name = new_name + "NEW"
    client.func(rename_file_func)(
        torrent_hash=new_torrent.hash,
        old_path=new_torrent.files[0].name,
        new_path=new_new_name,
    )
    check(lambda: new_torrent.files[0].name.replace("+", " "), new_new_name)
    # test invalid old_path is rejected
    with pytest.raises(Conflict409Error):
        client.func(rename_file_func)(
            torrent_hash=new_torrent.hash, old_path="asdf", new_path="xcvb"
        )


@pytest.mark.skipif_after_api_version("2.4.0")
@pytest.mark.parametrize(
    "rename_file_func",
    [
        "torrents_rename_file",
        "torrents_renameFile",
        "torrents.rename_file",
        "torrents.renameFile",
    ],
)
def test_rename_file_not_implemented(
    client,
    new_torrent,
    rename_file_func,
):
    with pytest.raises(NotImplementedError):
        client.func(rename_file_func)()


@pytest.mark.skipif_before_api_version("2.7")
@pytest.mark.parametrize("new_name", ["asdf zxcv", "asdf_zxcv"])
@pytest.mark.parametrize(
    "rename_folder_func",
    [
        "torrents_rename_folder",
        "torrents_renameFolder",
        "torrents.rename_folder",
        "torrents.renameFolder",
    ],
)
def test_rename_folder(client, app_version, new_torrent, new_name, rename_folder_func):
    if v(app_version) >= v("v4.3.3"):
        # move the file in to a new folder
        orig_file_path = new_torrent.files[0].name
        new_folder = "qwer"
        client.torrents_rename_file(
            torrent_hash=new_torrent.hash,
            old_path=orig_file_path,
            new_path=new_folder + "/" + orig_file_path,
        )

        # wait for the folder to be renamed
        check(
            lambda: [f.name.split("/")[0] for f in new_torrent.files],
            new_folder,
            reverse=True,
        )

        # test rename that new folder
        client.func(rename_folder_func)(
            torrent_hash=new_torrent.hash,
            old_path=new_folder,
            new_path=new_name,
        )
        check(
            lambda: new_torrent.files[0].name.replace("+", " "),
            new_name + "/" + orig_file_path,
        )
    elif v(app_version) >= v("v4.3.2"):
        with pytest.raises(NotImplementedError):
            client.func(rename_folder_func)()


@pytest.mark.skipif_after_api_version("2.7")
@pytest.mark.parametrize(
    "rename_folder_func",
    [
        "torrents_rename_folder",
        "torrents_renameFolder",
        "torrents.rename_folder",
        "torrents.renameFolder",
    ],
)
def test_rename_folder_not_implemented(client, rename_folder_func):
    with pytest.raises(NotImplementedError):
        client.func(rename_folder_func)()


@pytest.mark.skipif_before_api_version("2.8.14")
@pytest.mark.parametrize("export_func", ["torrents_export", "torrents.export"])
def test_export(client, orig_torrent, export_func):
    assert isinstance(client.func(export_func)(torrent_hash=orig_torrent.hash), bytes)


@pytest.mark.skipif_after_api_version("2.8.14")
@pytest.mark.parametrize("export_func", ["torrents_export", "torrents.export"])
def test_export_not_implemented(client, export_func):
    with pytest.raises(NotImplementedError):
        client.func(export_func)()


@pytest.mark.parametrize("info_func", ["torrents_info", "torrents.info"])
def test_torrents_info(client, info_func):
    assert isinstance(client.func(info_func)(), TorrentInfoList)
    if "." in info_func:
        assert isinstance(client.func(info_func).all(), TorrentInfoList)
        assert isinstance(client.func(info_func).downloading(), TorrentInfoList)
        assert isinstance(client.func(info_func).seeding(), TorrentInfoList)
        assert isinstance(client.func(info_func).completed(), TorrentInfoList)
        assert isinstance(client.func(info_func).paused(), TorrentInfoList)
        assert isinstance(client.func(info_func).active(), TorrentInfoList)
        assert isinstance(client.func(info_func).inactive(), TorrentInfoList)
        assert isinstance(client.func(info_func).resumed(), TorrentInfoList)
        assert isinstance(client.func(info_func).stalled(), TorrentInfoList)
        assert isinstance(client.func(info_func).stalled_uploading(), TorrentInfoList)
        assert isinstance(client.func(info_func).stalled_downloading(), TorrentInfoList)
        assert isinstance(client.func(info_func).checking(), TorrentInfoList)
        assert isinstance(client.func(info_func).moving(), TorrentInfoList)
        assert isinstance(client.func(info_func).errored(), TorrentInfoList)


def test_torrents_info_slice(client):
    assert isinstance(client.torrents_info()[1:2], TorrentInfoList)


@pytest.mark.skipif_before_api_version("2.8.3")
@pytest.mark.parametrize("info_func", ["torrents_info", "torrents.info"])
def test_torrents_info_tag(client, new_torrent, info_func):
    tag_name = "tag_filter_name"
    client.torrents_add_tags(tags=tag_name, torrent_hashes=new_torrent.hash)
    torrents = client.func(info_func)(torrent_hashes=new_torrent.hash, tag=tag_name)
    assert new_torrent.hash in {t.hash for t in torrents}


# test fails on 4.1.0 release
@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "stop_func, start_func",
    [
        ("torrents_stop", "torrents_start"),
        ("torrents_pause", "torrents_resume"),
        ("torrents.stop", "torrents.start"),
        ("torrents.pause", "torrents.resume"),
    ],
)
def test_stop_start(client, new_torrent, stop_func, start_func):
    client.func(stop_func)(torrent_hashes=new_torrent.hash)
    check(
        lambda: client.torrents_info(torrent_hashes=new_torrent.hash)[
            0
        ].state_enum.is_paused,
        True,
    )

    client.func(start_func)(torrent_hashes=new_torrent.hash)
    check(
        lambda: client.torrents_info(torrent_hashes=new_torrent.hash)[
            0
        ].state_enum.is_paused,
        False,
    )


def test_action_for_all_torrents(client):
    client.torrents.resume.all()
    for torrent in client.torrents.info():
        check(
            lambda: client.torrents_info(torrent_hashes=torrent.hash)[0].state,
            {"pausedDL", "stoppedDL"},
            negate=True,
        )
    client.torrents.pause.all()
    for torrent in client.torrents.info():
        check(
            lambda: client.torrents_info(torrent_hashes=torrent.hash)[0].state,
            {"stalledDL", "pausedDL", "stoppedDL"},
            any=True,
        )


@pytest.mark.parametrize("recheck_func", ["torrents_recheck", "torrents.recheck"])
def test_recheck(client, orig_torrent, recheck_func):
    client.func(recheck_func)(torrent_hashes=orig_torrent.hash)


@pytest.mark.skipif_before_api_version("2.0.2")
@pytest.mark.parametrize(
    "reannounce_func", ["torrents_reannounce", "torrents.reannounce"]
)
def test_reannounce(client, orig_torrent, reannounce_func):
    client.func(reannounce_func)(torrent_hashes=orig_torrent.hash)


@pytest.mark.skipif_after_api_version("2.0.2")
@pytest.mark.parametrize(
    "reannounce_func", ["torrents_reannounce", "torrents.reannounce"]
)
def test_reannounce_not_implemented(client, reannounce_func):
    with pytest.raises(NotImplementedError):
        client.func(reannounce_func)()


# priority doesn't seem to work on v4.1.0
@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "inc_prio_func, dec_prio_func, top_prio_func, bottom_prio_func",
    [
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
    ],
)
def test_priority(
    client, new_torrent, inc_prio_func, dec_prio_func, top_prio_func, bottom_prio_func
):
    disable_queueing(client)

    with pytest.raises(Conflict409Error):
        client.func(inc_prio_func)(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        client.func(dec_prio_func)(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        client.func(top_prio_func)(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        client.func(bottom_prio_func)(torrent_hashes=new_torrent.hash)

    enable_queueing(client)

    @retry()
    def test1(current_priority):
        client.func(inc_prio_func)(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.priority < current_priority, True)

    @retry()
    def test2(current_priority):
        client.func(dec_prio_func)(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.priority > current_priority, True)

    @retry()
    def test3(current_priority):
        client.func(top_prio_func)(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.priority < current_priority, True)

    @retry()
    def test4(current_priority):
        client.func(bottom_prio_func)(torrent_hashes=new_torrent.hash)
        check(lambda: new_torrent.info.priority > current_priority, True)

    test1(current_priority=new_torrent.info.priority)
    test2(current_priority=new_torrent.info.priority)
    test3(current_priority=new_torrent.info.priority)
    test4(current_priority=new_torrent.info.priority)


@pytest.mark.parametrize(
    "set_down_limit_func, down_limit_func",
    [
        ("torrents_set_download_limit", "torrents_download_limit"),
        ("torrents_setDownloadLimit", "torrents_downloadLimit"),
        ("torrents.set_download_limit", "torrents.download_limit"),
        ("torrents.setDownloadLimit", "torrents.downloadLimit"),
    ],
)
def test_download_limit(client, orig_torrent, set_down_limit_func, down_limit_func):
    orig_download_limit = client.func(down_limit_func)(
        torrent_hashes=orig_torrent.hash
    )[orig_torrent.hash]

    client.func(set_down_limit_func)(torrent_hashes=orig_torrent.hash, limit=100)
    assert isinstance(
        client.func(down_limit_func)(torrent_hashes=orig_torrent.hash),
        TorrentLimitsDictionary,
    )
    check(
        lambda: client.func(down_limit_func)(torrent_hashes=orig_torrent.hash)[
            orig_torrent.hash
        ],
        100,
    )

    # reset download limit
    client.func(set_down_limit_func)(
        torrent_hashes=orig_torrent.hash, limit=orig_download_limit
    )
    check(
        lambda: client.func(down_limit_func)(torrent_hashes=orig_torrent.hash)[
            orig_torrent.hash
        ],
        orig_download_limit,
    )


@pytest.mark.parametrize(
    "set_up_limit_func, up_limit_func",
    [
        ("torrents_set_upload_limit", "torrents_upload_limit"),
        ("torrents_setUploadLimit", "torrents_uploadLimit"),
        ("torrents.set_upload_limit", "torrents.upload_limit"),
        ("torrents.setUploadLimit", "torrents.uploadLimit"),
    ],
)
def test_upload_limit(client, orig_torrent, set_up_limit_func, up_limit_func):
    orig_upload_limit = client.func(up_limit_func)(torrent_hashes=orig_torrent.hash)[
        orig_torrent.hash
    ]

    client.func(set_up_limit_func)(torrent_hashes=orig_torrent.hash, limit=100)
    assert isinstance(
        client.func(up_limit_func)(torrent_hashes=orig_torrent.hash),
        TorrentLimitsDictionary,
    )
    check(
        lambda: client.func(up_limit_func)(torrent_hashes=orig_torrent.hash)[
            orig_torrent.hash
        ],
        100,
    )

    # reset upload limit
    client.func(set_up_limit_func)(
        torrent_hashes=orig_torrent.hash, limit=orig_upload_limit
    )
    check(
        lambda: client.func(up_limit_func)(torrent_hashes=orig_torrent.hash)[
            orig_torrent.hash
        ],
        orig_upload_limit,
    )


@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "set_share_limits_func",
    [
        "torrents_set_share_limits",
        "torrents_setShareLimits",
        "torrents.set_share_limits",
        "torrents.setShareLimits",
    ],
)
def test_set_share_limits(client, orig_torrent, set_share_limits_func):
    client.func(set_share_limits_func)(
        ratio_limit=2,
        seeding_time_limit=5,
        inactive_seeding_time_limit=8,
        torrent_hashes=orig_torrent.hash,
    )
    check(lambda: orig_torrent.info.max_ratio, 2)
    check(lambda: orig_torrent.info.max_seeding_time, 5)
    if "max_inactive_seeding_time" in orig_torrent.info:
        check(lambda: orig_torrent.info.max_inactive_seeding_time, 8)

    client.func(set_share_limits_func)(
        ratio_limit=3,
        seeding_time_limit=6,
        inactive_seeding_time_limit=9,
        torrent_hashes=orig_torrent.hash,
    )
    check(lambda: orig_torrent.info.max_ratio, 3)
    check(lambda: orig_torrent.info.max_seeding_time, 6)
    if "max_inactive_seeding_time" in orig_torrent.info:
        check(lambda: orig_torrent.info.max_inactive_seeding_time, 9)


@pytest.mark.skipif_after_api_version("2.0.1")
@pytest.mark.parametrize(
    "set_share_limits_func",
    [
        "torrents_set_share_limits",
        "torrents_setShareLimits",
        "torrents.set_share_limits",
        "torrents.setShareLimits",
    ],
)
def test_set_share_limits_not_implemented(client, set_share_limits_func):
    with pytest.raises(NotImplementedError):
        client.func(set_share_limits_func)()


@pytest.mark.skipif_before_api_version("2.0.2")
@pytest.mark.parametrize(
    "set_loc_func",
    [
        "torrents_set_location",
        "torrents_setLocation",
        "torrents.set_location",
        "torrents.setLocation",
    ],
)
def test_set_location(client, app_version, new_torrent, set_loc_func, tmp_path):
    # stopped erroring when the write check was removed for API
    if v(app_version) < v("v4.5.2"):
        with pytest.raises(Forbidden403Error):
            client.func(set_loc_func)(location="/etc/", torrent_hashes=new_torrent.hash)

    sleep(0.5)
    loc = mkpath(tmp_path, "1")
    client.func(set_loc_func)(location=loc, torrent_hashes=new_torrent.hash)
    # qBittorrent may return trailing separators depending on version....
    check(lambda: mkpath(new_torrent.info.save_path), loc, any=True)


@pytest.mark.skipif_before_api_version("2.8.4")
@pytest.mark.parametrize(
    "set_save_path_func",
    [
        "torrents_set_save_path",
        "torrents_setSavePath",
        "torrents.set_save_path",
        "torrents.setSavePath",
    ],
)
def test_set_save_path(client, new_torrent, set_save_path_func, tmp_path):
    with pytest.raises(Forbidden403Error):
        client.func(set_save_path_func)(
            save_path="/etc/", torrent_hashes=new_torrent.hash
        )
    with pytest.raises(Conflict409Error):
        client.func(set_save_path_func)(
            save_path="/etc/asdf", torrent_hashes=new_torrent.hash
        )

    loc = mkpath(tmp_path, "savepath1")
    client.func(set_save_path_func)(save_path=loc, torrent_hashes=new_torrent.hash)
    # qBittorrent may return trailing separators depending on version....
    check(lambda: mkpath(new_torrent.info.save_path), loc, any=True)


@pytest.mark.skipif_after_api_version("2.8.4")
@pytest.mark.parametrize(
    "set_save_path_func",
    [
        "torrents_set_save_path",
        "torrents_setSavePath",
        "torrents.set_save_path",
        "torrents.setSavePath",
    ],
)
def test_set_save_path_not_implemented(client, set_save_path_func):
    with pytest.raises(NotImplementedError):
        client.func(set_save_path_func)()


@pytest.mark.skipif_before_api_version("2.8.4")
@pytest.mark.parametrize(
    "set_down_path_func",
    [
        "torrents_set_download_path",
        "torrents_setDownloadPath",
        "torrents.set_download_path",
        "torrents.setDownloadPath",
    ],
)
def test_set_download_path(client, new_torrent, set_down_path_func, tmp_path):
    with pytest.raises(Forbidden403Error):
        client.func(set_down_path_func)(
            download_path="/etc/", torrent_hashes=new_torrent.hash
        )
    with pytest.raises(Conflict409Error):
        client.func(set_down_path_func)(
            download_path="/etc/asdf", torrent_hashes=new_torrent.hash
        )

    loc = mkpath(tmp_path, "savepath1")
    client.func(set_down_path_func)(download_path=loc, torrent_hashes=new_torrent.hash)
    # qBittorrent may return trailing separators depending on version....
    check(lambda: mkpath(new_torrent.info.download_path), loc, any=True)


@pytest.mark.skipif_after_api_version("2.8.4")
@pytest.mark.parametrize(
    "set_down_path_func",
    [
        "torrents_set_download_path",
        "torrents_setDownloadPath",
        "torrents.set_download_path",
        "torrents.setDownloadPath",
    ],
)
def test_set_download_path_not_implemented(client, new_torrent, set_down_path_func):
    with pytest.raises(NotImplementedError):
        client.func(set_down_path_func)()


@pytest.mark.parametrize(
    "set_cat_func",
    [
        "torrents_set_category",
        "torrents_setCategory",
        "torrents.set_category",
        "torrents.setCategory",
    ],
)
@pytest.mark.parametrize("name", ["awesome cat", "awesome_cat"])
def test_set_category(client, orig_torrent, set_cat_func, name):
    with pytest.raises(Conflict409Error):
        client.func(set_cat_func)(
            category="/!@#$%^&*(", torrent_hashes=orig_torrent.hash
        )

    client.torrents_create_category(name=name)
    try:
        client.func(set_cat_func)(category=name, torrent_hashes=orig_torrent.hash)
        check(lambda: orig_torrent.info.category.replace("+", " "), name)
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize(
    "set_auto_mgmt_func",
    [
        "torrents_set_auto_management",
        "torrents_setAutoManagement",
        "torrents.set_auto_management",
        "torrents.setAutoManagement",
    ],
)
def test_torrents_set_auto_management(client, orig_torrent, set_auto_mgmt_func):
    current_setting = orig_torrent.info.auto_tmm
    client.func(set_auto_mgmt_func)(
        enable=(not current_setting), torrent_hashes=orig_torrent.hash
    )
    check(lambda: orig_torrent.info.auto_tmm, (not current_setting))
    client.func(set_auto_mgmt_func)(
        enable=False, torrent_hashes=orig_torrent.hash
    )  # leave on False


@pytest.mark.parametrize(
    "toggle_seq_down_func",
    [
        "torrents_toggle_sequential_download",
        "torrents_toggleSequentialDownload",
        "torrents.toggle_sequential_download",
        "torrents.toggleSequentialDownload",
    ],
)
def test_toggle_sequential_download(client, orig_torrent, toggle_seq_down_func):
    current_setting = orig_torrent.info.seq_dl
    client.func(toggle_seq_down_func)(torrent_hashes=orig_torrent.hash)
    check(lambda: orig_torrent.info.seq_dl, not current_setting)


@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "toggle_piece_prio_func",
    [
        "torrents_toggle_first_last_piece_priority",
        "torrents_toggleFirstLastPiecePrio",
        "torrents.toggle_first_last_piece_priority",
        "torrents.toggleFirstLastPiecePrio",
    ],
)
def test_toggle_first_last_piece_priority(client, new_torrent, toggle_piece_prio_func):
    current_setting = new_torrent.info.f_l_piece_prio
    client.func(toggle_piece_prio_func)(torrent_hashes=new_torrent.hash)
    check(lambda: new_torrent.info.f_l_piece_prio, not current_setting)


@pytest.mark.parametrize(
    "set_force_start_func",
    [
        "torrents_set_force_start",
        "torrents_setForceStart",
        "torrents.set_force_start",
        "torrents.setForceStart",
    ],
)
def test_set_force_start(client, orig_torrent, set_force_start_func):
    current_setting = orig_torrent.info.force_start
    client.func(set_force_start_func)(
        enable=(not current_setting), torrent_hashes=orig_torrent.hash
    )
    check(lambda: orig_torrent.info.force_start, not current_setting)


@pytest.mark.parametrize(
    "set_super_seeding_func",
    [
        "torrents_set_super_seeding",
        "torrents_setSuperSeeding",
        "torrents.set_super_seeding",
        "torrents.setSuperSeeding",
    ],
)
def test_set_super_seeding(client, orig_torrent, set_super_seeding_func):
    client.func(set_super_seeding_func)(enable=False, torrent_hashes=orig_torrent.hash)
    check(lambda: orig_torrent.info.force_start, False)


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "add_peers_func",
    [
        "torrents_add_peers",
        "torrents_addPeers",
        "torrents.add_peers",
        "torrents.addPeers",
    ],
)
@pytest.mark.parametrize(
    "peers", ["127.0.0.1:5000", ["127.0.0.1:5000", "127.0.0.2:5000"], "127.0.0.1"]
)
def test_torrents_add_peers(client, orig_torrent, add_peers_func, peers):
    if all(":" not in p for p in peers):
        with pytest.raises(InvalidRequest400Error):
            client.func(add_peers_func)(peers=peers, torrent_hashes=orig_torrent.hash)
    else:
        p = client.func(add_peers_func)(peers=peers, torrent_hashes=orig_torrent.hash)
        assert isinstance(p, TorrentsAddPeersDictionary)


@pytest.mark.skipif_after_api_version("2.3.0")
@pytest.mark.parametrize(
    "add_peers_func",
    [
        "torrents_add_peers",
        "torrents_addPeers",
        "torrents.add_peers",
        "torrents.addPeers",
    ],
)
def test_torrents_add_peers_not_implemented(client, add_peers_func):
    with pytest.raises(NotImplementedError):
        client.func(add_peers_func)()


def _categories_save_path_key(api_version):
    """With qBittorrent 4.4.0 (Web API 2.8.4), the key in the category definition
    returned changed from savePath to save_path...."""
    if v(api_version) == v("2.8.4"):
        return "save_path"
    return "savePath"


@pytest.mark.skipif_before_api_version("2.1.1")
def test_categories1(client):
    assert isinstance(client.torrents_categories(), TorrentCategoriesDictionary)


@pytest.mark.skipif_after_api_version("2.1.1")
def test_categories1_not_implemented(client, api_version):
    with pytest.raises(NotImplementedError):
        client.torrents_categories()


@pytest.mark.skipif_before_api_version("2.1.1")
def test_categories2(client, api_version, tmp_path):
    save_path_key = _categories_save_path_key(api_version)
    name = "new_category"
    client.torrent_categories.categories = {"name": name, save_path_key: tmp_path}
    assert name in client.torrent_categories.categories
    client.torrent_categories.categories = {
        "name": name,
        save_path_key: mkpath(tmp_path, "new"),
    }
    assert mkpath(client.torrent_categories.categories[name][save_path_key]) == mkpath(
        tmp_path, "new"
    )
    client.torrents_remove_categories(categories=name)


@pytest.mark.skipif_after_api_version("2.1.1")
def test_categories2_not_implemented(client):
    with pytest.raises(NotImplementedError):
        _ = client.torrent_categories.categories


@pytest.mark.parametrize(
    "create_cat_func",
    [
        "torrents_create_category",
        "torrents_createCategory",
        "torrent_categories.create_category",
        "torrent_categories.createCategory",
    ],
)
@pytest.mark.parametrize("filepath", [None, "", "/tmp/"])
@pytest.mark.parametrize("name", ["name", "name 1"])
@pytest.mark.parametrize("enable_download_path", [None, True, False])
def test_create_categories(
    client,
    api_version,
    orig_torrent,
    create_cat_func,
    filepath,
    name,
    enable_download_path,
):
    save_path = download_path = filepath
    if filepath:
        save_path += "save"
        download_path += "download"

    try:
        client.func(create_cat_func)(
            name=name,
            save_path=save_path,
            download_path=download_path,
            enable_download_path=enable_download_path,
        )
        client.torrents_set_category(torrent_hashes=orig_torrent.hash, category=name)
        check(lambda: orig_torrent.info.category.replace("+", " "), name)
        if v(api_version) >= v("2.2"):
            check(
                lambda: [n.replace("+", " ") for n in client.torrents_categories()],
                name,
                reverse=True,
            )
            save_path_key = _categories_save_path_key(api_version)
            check(
                lambda: [
                    mkpath(cat[save_path_key])
                    for cat in client.torrents_categories().values()
                ],
                mkpath(save_path) or "",
                reverse=True,
            )
        if v(api_version) >= v("2.8.4") and enable_download_path is not False:
            check(
                lambda: [
                    mkpath(cat.get("download_path", ""))
                    for cat in client.torrents_categories().values()
                ],
                mkpath(download_path) or "",
                reverse=True,
            )
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.skipif_before_api_version("2.1.0")
@pytest.mark.parametrize(
    "edit_cat_func",
    [
        "torrents_edit_category",
        "torrents_editCategory",
        "torrent_categories.edit_category",
        "torrent_categories.editCategory",
    ],
)
@pytest.mark.parametrize("filepath", ["", "/tmp/"])
@pytest.mark.parametrize("name", ["editcategory"])
@pytest.mark.parametrize("enable_download_path", [None, True, False])
def test_edit_category(
    client, api_version, edit_cat_func, filepath, name, enable_download_path
):
    try:
        client.torrents_create_category(
            name=name, save_path="/tmp/savetmp", download_path="/tmp/savetmp"
        )
        save_path = mkpath(filepath + "save/")
        download_path = mkpath(filepath + "down/")
        client.func(edit_cat_func)(
            name=name,
            save_path=save_path,
            download_path=download_path,
            enable_download_path=enable_download_path,
        )
        check(
            lambda: [n.replace("+", " ") for n in client.torrents_categories()],
            name,
            reverse=True,
        )
        save_path_key = _categories_save_path_key(api_version)
        check(
            lambda: (
                mkpath(cat[save_path_key])
                for cat in client.torrents_categories().values()
            ),
            mkpath(save_path) or "",
            reverse=True,
        )
        if v(api_version) >= v("2.8.4") and enable_download_path is not False:
            check(
                lambda: [
                    mkpath(cat.get("download_path", ""))
                    for cat in client.torrents_categories().values()
                ],
                mkpath(download_path) or "",
                reverse=True,
            )
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.skipif_after_api_version("2.1.0")
@pytest.mark.parametrize(
    "edit_cat_func",
    (
        "torrents_edit_category",
        "torrents_editCategory",
        "torrent_categories.edit_category",
        "torrent_categories.editCategory",
    ),
)
def test_edit_category_not_implemented(client, edit_cat_func):
    with pytest.raises(NotImplementedError):
        client.func(edit_cat_func)()


@pytest.mark.parametrize(
    "remove_cat_func",
    [
        "torrents_remove_categories",
        "torrents_removeCategories",
        "torrent_categories.remove_categories",
        "torrent_categories.removeCategories",
    ],
)
@pytest.mark.parametrize("categories", [["category1"], ["category1", "category 2"]])
def test_remove_category(
    client, api_version, orig_torrent, remove_cat_func, categories
):
    for name in categories:
        client.torrents_create_category(name=name)
    orig_torrent.set_category(category=categories[0])
    client.func(remove_cat_func)(categories=categories)
    if v(api_version) >= v("2.2"):
        check(
            lambda: [n.replace("+", " ") for n in client.torrents_categories()],
            categories,
            reverse=True,
            negate=True,
        )
    check(lambda: orig_torrent.info.category, categories[0], negate=True)


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "tags_func",
    [
        "torrents_tags",
        "torrent_tags.tags",
    ],
)
def test_tags(client, tags_func):
    try:
        assert isinstance(client.func(tags_func)(), TagList)
    except TypeError:
        assert isinstance(client.func(tags_func), TagList)


@pytest.mark.skipif_before_api_version("2.3.0")
def test_tags_slice(client):
    assert isinstance(client.torrents_tags()[1:2], TagList)


@pytest.mark.skipif_after_api_version("2.3.0")
@pytest.mark.parametrize(
    "tags_func",
    [
        "torrents_tags",
        "torrent_tags.tags",
    ],
)
def test_tags_not_implemented(client, tags_func):
    with pytest.raises(NotImplementedError):
        client.func(tags_func)()


@pytest.mark.skipif_before_api_version("2.3.0")
def test_add_tag_though_property(client):
    name = "newtag"
    client.torrent_tags.tags = name
    assert name in client.torrent_tags.tags
    client.torrent_tags.delete_tags(name)
    assert name not in client.torrent_tags.tags


@pytest.mark.skipif_after_api_version("2.3.0")
def test_add_tag_though_property_not_implemented(client):
    with pytest.raises(NotImplementedError):
        client.torrent_tags.tags = "asdf"


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "add_tags_func",
    [
        "torrents_add_tags",
        "torrents_addTags",
        "torrent_tags.add_tags",
        "torrent_tags.addTags",
    ],
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_add_tags(client, orig_torrent, add_tags_func, tags):
    try:
        client.func(add_tags_func)(tags=tags, torrent_hashes=orig_torrent.hash)
        check(lambda: orig_torrent.info.tags, tags, reverse=True)
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_after_api_version("2.3.0")
@pytest.mark.parametrize(
    "add_tags_func",
    [
        "torrents_add_tags",
        "torrents_addTags",
        "torrent_tags.add_tags",
        "torrent_tags.addTags",
    ],
)
def test_add_tags_not_implemented(client, add_tags_func):
    with pytest.raises(NotImplementedError):
        client.func(add_tags_func)()


@pytest.mark.skipif_before_api_version("2.11.4")
@pytest.mark.parametrize(
    "set_tags_func",
    [
        "torrents_set_tags",
        "torrents_setTags",
        "torrent_tags.set_tags",
        "torrent_tags.setTags",
    ],
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_set_tags(client, orig_torrent, set_tags_func, tags):
    try:
        client.torrents_add_tags(tags="extra-tag", torrent_hashes=orig_torrent.hash)
        client.func(set_tags_func)(tags=tags, torrent_hashes=orig_torrent.hash)
        check(lambda: orig_torrent.info.tags, tags, reverse=True)
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_after_api_version("2.11.4")
@pytest.mark.parametrize(
    "set_tags_func",
    [
        "torrents_set_tags",
        "torrents_setTags",
        "torrent_tags.set_tags",
        "torrent_tags.setTags",
    ],
)
def test_set_tags_not_implemented(client, set_tags_func):
    with pytest.raises(NotImplementedError):
        client.func(set_tags_func)()


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "remove_tags_func",
    [
        "torrents_remove_tags",
        "torrents_removeTags",
        "torrent_tags.remove_tags",
        "torrent_tags.removeTags",
    ],
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_remove_tags(client, orig_torrent, remove_tags_func, tags):
    try:
        orig_torrent.add_tags(tags=tags)
        client.func(remove_tags_func)(tags=tags, torrent_hashes=orig_torrent.hash)
        check(lambda: orig_torrent.info.tags, tags, reverse=True, negate=True)
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_after_api_version("2.3.0")
@pytest.mark.parametrize(
    "remove_tags_func",
    [
        "torrents_remove_tags",
        "torrents_removeTags",
        "torrent_tags.remove_tags",
        "torrent_tags.removeTags",
    ],
)
def test_remove_tags_not_implemented(client, remove_tags_func):
    with pytest.raises(NotImplementedError):
        client.func(remove_tags_func)()


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "create_tags_func",
    [
        "torrents_create_tags",
        "torrents_createTags",
        "torrent_tags.create_tags",
        "torrent_tags.createTags",
    ],
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_create_tags(client, create_tags_func, tags):
    try:
        client.func(create_tags_func)(tags=tags)
        check(lambda: client.torrents_tags(), tags, reverse=True)
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_after_api_version("2.3.0")
@pytest.mark.parametrize(
    "create_tags_func",
    [
        "torrents_create_tags",
        "torrents_createTags",
        "torrent_tags.create_tags",
        "torrent_tags.createTags",
    ],
)
def test_create_tags_not_implemented(client, create_tags_func):
    with pytest.raises(NotImplementedError):
        client.func(create_tags_func)()


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "delete_tags_func",
    [
        "torrents_delete_tags",
        "torrents_deleteTags",
        "torrent_tags.delete_tags",
        "torrent_tags.deleteTags",
    ],
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_delete_tags(client, delete_tags_func, tags):
    client.torrents_create_tags(tags=tags)
    client.func(delete_tags_func)(tags=tags)
    check(lambda: client.torrents_tags(), tags, reverse=True, negate=True)


@pytest.mark.skipif_after_api_version("2.3.0")
@pytest.mark.parametrize(
    "delete_tags_func",
    [
        "torrents_delete_tags",
        "torrents_deleteTags",
        "torrent_tags.delete_tags",
        "torrent_tags.deleteTags",
    ],
)
def test_delete_tags_not_implemented(client, delete_tags_func):
    with pytest.raises(NotImplementedError):
        client.func(delete_tags_func)()
