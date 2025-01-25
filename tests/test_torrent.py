import platform
from time import sleep
from types import MethodType
from unittest.mock import MagicMock

import pytest

from qbittorrentapi import (
    APINames,
    Conflict409Error,
    TorrentDictionary,
    TorrentFilesList,
    TorrentPieceInfoList,
    TorrentPropertiesDictionary,
    TorrentStates,
    TrackersList,
    WebSeedsList,
)
from qbittorrentapi._version_support import v
from tests.test_torrents import disable_queueing, enable_queueing
from tests.utils import check, mkpath, retry


def test_info(orig_torrent, monkeypatch):
    assert orig_torrent.info.hash == orig_torrent.hash
    # mimic <=v2.0.1 where torrents_info() doesn't support hash arg
    with monkeypatch.context() as m:
        m.setattr(orig_torrent._client, "app_version", MagicMock(return_value="2.0.0"))
        assert orig_torrent.info.hash == orig_torrent.hash

    # ensure if things are really broken, an empty TorrentDictionary is returned...
    if platform.python_implementation() == "CPython":
        with monkeypatch.context() as m:

            def fake_info(*args, **kwargs):
                return []

            m.setattr(orig_torrent._client, "torrents_info", fake_info)
            assert isinstance(orig_torrent.info, TorrentDictionary)
            assert bool(orig_torrent.info) is False


def test_sync_local(orig_torrent):
    orig_torrent.state = "gibberish"
    assert orig_torrent.state == "gibberish"
    orig_torrent.sync_local()
    assert isinstance(orig_torrent, TorrentDictionary)
    assert orig_torrent.state != "gibberish"


def test_state_enum(orig_torrent):
    assert orig_torrent.state_enum in TorrentStates
    assert orig_torrent.state_enum is not TorrentStates.UNKNOWN
    orig_torrent.resume()
    check(
        lambda: orig_torrent.sync_local() is None
        and orig_torrent.state_enum.is_downloading,
        True,
    )
    # simulate an unknown torrent.state
    orig_torrent.state = "gibberish"
    assert orig_torrent.state_enum is TorrentStates.UNKNOWN
    # restore torrent state
    orig_torrent.sync_local()
    check(lambda: orig_torrent.state_enum.is_downloading, True)


# test fails on 4.1.0 release
@pytest.mark.skipif_before_api_version("2.0.1")
def test_pause_resume(client, new_torrent):
    new_torrent.pause()
    check(
        lambda: client.torrents_info(torrent_hashes=new_torrent.hash)[
            0
        ].state_enum.is_paused,
        True,
    )

    new_torrent.resume()
    check(
        lambda: client.torrents_info(torrent_hashes=new_torrent.hash)[
            0
        ].state_enum.is_paused,
        False,
    )


# test fails on 4.1.0 release
@pytest.mark.skipif_before_api_version("2.0.1")
def test_stop_start(client, new_torrent):
    new_torrent.stop()
    check(
        lambda: client.torrents_info(torrent_hashes=new_torrent.hash)[
            0
        ].state_enum.is_paused,
        True,
    )

    new_torrent.resume()
    check(
        lambda: client.torrents_info(torrent_hashes=new_torrent.hash)[
            0
        ].state_enum.is_paused,
        False,
    )


@pytest.mark.parametrize("delete", [True, False, None, 0, 1])
def test_delete(client_mock, new_torrent, delete):
    new_torrent.delete(delete_files=delete)
    client_mock._post.assert_called_with(
        _name=APINames.Torrents,
        _method="delete",
        data={
            "hashes": new_torrent.hash,
            "deleteFiles": bool(delete),
        },
    )
    check(
        lambda: [t.hash for t in client_mock.torrents_info()],
        new_torrent.hash,
        reverse=True,
        negate=True,
    )


@pytest.mark.parametrize(
    "inc_prio_func, dec_prio_func, top_prio_func, bottom_prio_func",
    [
        ("increase_priority", "decrease_priority", "top_priority", "bottom_priority"),
        ("increasePrio", "decreasePrio", "topPrio", "bottomPrio"),
    ],
)
def test_priority(
    client, new_torrent, inc_prio_func, dec_prio_func, top_prio_func, bottom_prio_func
):
    disable_queueing(client)

    with pytest.raises(Conflict409Error):
        new_torrent.func(inc_prio_func)()
    with pytest.raises(Conflict409Error):
        new_torrent.func(dec_prio_func)()
    with pytest.raises(Conflict409Error):
        new_torrent.func(top_prio_func)()
    with pytest.raises(Conflict409Error):
        new_torrent.func(bottom_prio_func)()

    enable_queueing(client)
    sleep(0.25)  # putting sleeps in since these keep crashing qbittorrent

    current_priority = new_torrent.info.priority
    new_torrent.func(inc_prio_func)()
    sleep(0.25)
    check(lambda: new_torrent.info.priority < current_priority, True)

    current_priority = new_torrent.info.priority
    new_torrent.func(dec_prio_func)()
    sleep(0.25)
    check(lambda: new_torrent.info.priority > current_priority, True)

    current_priority = new_torrent.info.priority
    new_torrent.func(top_prio_func)()
    sleep(0.25)
    check(lambda: new_torrent.info.priority < current_priority, True)

    current_priority = new_torrent.info.priority
    new_torrent.func(bottom_prio_func)()
    sleep(0.25)
    check(lambda: new_torrent.info.priority > current_priority, True)


@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "set_share_limits_func", ["set_share_limits", "setShareLimits"]
)
def test_set_share_limits(orig_torrent, set_share_limits_func):
    orig_torrent.func(set_share_limits_func)(
        ratio_limit=5, seeding_time_limit=100, inactive_seeding_time_limit=200
    )
    check(lambda: orig_torrent.info.max_ratio, 5)
    check(lambda: orig_torrent.info.max_seeding_time, 100)
    if "max_inactive_seeding_time" in orig_torrent.info:
        check(lambda: orig_torrent.info.max_inactive_seeding_time, 200)


@pytest.mark.skipif_after_api_version("2.0.1")
@pytest.mark.parametrize(
    "set_share_limits_func", ["set_share_limits", "setShareLimits"]
)
def test_set_share_limits_not_implemented(orig_torrent, set_share_limits_func):
    with pytest.raises(NotImplementedError):
        orig_torrent.func(set_share_limits_func)(ratio_limit=5, seeding_time_limit=100)


@pytest.mark.parametrize(
    "down_limit_func, set_down_limit_func",
    [("download_limit", "set_download_limit"), ("downloadLimit", "setDownloadLimit")],
)
def test_download_limit(orig_torrent, down_limit_func, set_down_limit_func):
    setattr(orig_torrent, down_limit_func, 2048)
    check(lambda: orig_torrent.func(down_limit_func), 2048)
    check(lambda: orig_torrent.info.dl_limit, 2048)

    orig_torrent.func(set_down_limit_func)(4096)
    check(lambda: orig_torrent.func(down_limit_func), 4096)
    check(lambda: orig_torrent.info.dl_limit, 4096)


@pytest.mark.parametrize(
    "up_limit_func, set_up_limit_func",
    [("upload_limit", "set_upload_limit"), ("uploadLimit", "setUploadLimit")],
)
def test_upload_limit(orig_torrent, up_limit_func, set_up_limit_func):
    setattr(orig_torrent, up_limit_func, 2048)
    check(lambda: orig_torrent.func(up_limit_func), 2048)
    check(lambda: orig_torrent.info.up_limit, 2048)

    orig_torrent.func(set_up_limit_func)(4096)
    check(lambda: orig_torrent.func(up_limit_func), 4096)
    check(lambda: orig_torrent.info.up_limit, 4096)


@pytest.mark.skipif_before_api_version("2.0.2")
@pytest.mark.parametrize("set_loc_func", ["set_location", "setLocation"])
def test_set_location(new_torrent, set_loc_func, tmp_path):
    sleep(0.5)
    loc = mkpath(tmp_path, "3")
    new_torrent.func(set_loc_func)(loc)
    check(lambda: mkpath(new_torrent.info.save_path), mkpath(loc))


@pytest.mark.skipif_before_api_version("2.8.4")
@pytest.mark.parametrize("set_save_path_func", ["set_save_path", "setSavePath"])
def test_set_save_path(new_torrent, set_save_path_func, tmp_path):
    loc = mkpath(tmp_path, "savepath3")
    new_torrent.func(set_save_path_func)(loc)
    # qBittorrent may return trailing separators depending on version....
    check(lambda: mkpath(new_torrent.info.save_path), mkpath(loc))


@pytest.mark.skipif_before_api_version("2.8.4")
@pytest.mark.parametrize("set_down_path_func", ["set_download_path", "setDownloadPath"])
def test_set_download_path(new_torrent, set_down_path_func, tmp_path):
    loc = mkpath(tmp_path, "downloadpath3")
    new_torrent.func(set_down_path_func)(loc)
    # qBittorrent may return trailing separators depending on version....
    check(lambda: mkpath(new_torrent.info.download_path), mkpath(loc))


@pytest.mark.parametrize("set_cat_func", ["set_category", "setCategory"])
@pytest.mark.parametrize("category", ["category 1", "category_1"])
def test_set_category(client, orig_torrent, set_cat_func, category):
    client.torrents_create_category(category=category)
    orig_torrent.func(set_cat_func)(category=category)
    check(lambda: orig_torrent.info.category.replace("+", " "), category, reverse=True)
    client.torrents_remove_categories(categories=category)


@pytest.mark.parametrize(
    "set_auto_mgmt_func", ["set_auto_management", "setAutoManagement"]
)
def test_set_auto_management(orig_torrent, set_auto_mgmt_func):
    current_setting = orig_torrent.auto_tmm
    orig_torrent.func(set_auto_mgmt_func)(enable=(not current_setting))
    check(lambda: orig_torrent.info.auto_tmm, not current_setting)
    orig_torrent.func(set_auto_mgmt_func)(enable=current_setting)
    check(lambda: orig_torrent.info.auto_tmm, current_setting)


@pytest.mark.parametrize(
    "toggle_seq_down_func", ["toggle_sequential_download", "toggleSequentialDownload"]
)
def test_toggle_sequential_download(orig_torrent, toggle_seq_down_func):
    current_setting = orig_torrent.seq_dl
    orig_torrent.func(toggle_seq_down_func)()
    check(lambda: orig_torrent.info.seq_dl, not current_setting)
    orig_torrent.func(toggle_seq_down_func)()
    check(lambda: orig_torrent.info.seq_dl, current_setting)


@pytest.mark.skipif_before_api_version("2.0.2")
@pytest.mark.parametrize(
    "toggle_piece_prio_func",
    ["toggle_first_last_piece_priority", "toggleFirstLastPiecePrio"],
)
def test_toggle_first_last_piece_priority(orig_torrent, toggle_piece_prio_func):
    current_setting = orig_torrent.f_l_piece_prio
    orig_torrent.func(toggle_piece_prio_func)()
    check(lambda: orig_torrent.info.f_l_piece_prio, not current_setting)


@pytest.mark.parametrize("set_force_start_func", ["set_force_start", "setForceStart"])
def test_set_force_start(orig_torrent, set_force_start_func):
    current_setting = orig_torrent.force_start
    orig_torrent.func(set_force_start_func)(enable=(not current_setting))
    check(lambda: orig_torrent.info.force_start, not current_setting)
    orig_torrent.func(set_force_start_func)(enable=current_setting)
    check(lambda: orig_torrent.info.force_start, current_setting)


@pytest.mark.parametrize(
    "set_super_seeding_func", ["set_super_seeding", "setSuperSeeding"]
)
def test_set_super_seeding(orig_torrent, set_super_seeding_func):
    current_setting = orig_torrent.super_seeding
    orig_torrent.func(set_super_seeding_func)(enable=(not current_setting))
    check(lambda: orig_torrent.info.super_seeding, not current_setting)
    orig_torrent.func(set_super_seeding_func)(enable=current_setting)
    check(lambda: orig_torrent.info.super_seeding, current_setting)


def test_properties(orig_torrent):
    assert isinstance(orig_torrent.properties, TorrentPropertiesDictionary)
    assert "save_path" in orig_torrent.properties


@pytest.mark.parametrize("trackers", ["127.0.0.2", ["127.0.0.3", "127.0.0.4"]])
def test_trackers(orig_torrent, trackers):
    assert isinstance(orig_torrent.trackers, TrackersList)
    assert "num_peers" in orig_torrent.trackers[-1]

    orig_torrent.trackers = trackers
    check(lambda: (t.url for t in orig_torrent.trackers), trackers, reverse=True)


@pytest.mark.parametrize("add_trackers_func", ["add_trackers", "addTrackers"])
@pytest.mark.parametrize("trackers", ["127.0.0.2", ["127.0.0.3", "127.0.0.4"]])
def test_add_tracker(new_torrent, add_trackers_func, trackers):
    new_torrent.func(add_trackers_func)(urls=trackers)
    sleep(0.1)  # try to stop crashing qbittorrent
    check(lambda: (t.url for t in new_torrent.trackers), trackers, reverse=True)


@pytest.mark.skipif_before_api_version("2.2.0")
@pytest.mark.parametrize("edit_tracker_func", ["edit_tracker", "editTracker"])
def test_edit_tracker(orig_torrent, edit_tracker_func):
    orig_torrent.add_trackers(urls="127.0.1.1")
    orig_torrent.func(edit_tracker_func)(orig_url="127.0.1.1", new_url="127.0.1.2")
    check(
        lambda: (t.url for t in orig_torrent.trackers),
        "127.0.1.1",
        reverse=True,
        negate=True,
    )
    check(lambda: (t.url for t in orig_torrent.trackers), "127.0.1.2", reverse=True)
    orig_torrent.remove_trackers(urls="127.0.1.2")


@pytest.mark.skipif_after_api_version("2.2.0")
@pytest.mark.parametrize("edit_tracker_func", ["edit_tracker", "editTracker"])
def test_edit_tracker_not_implemented(orig_torrent, edit_tracker_func):
    with pytest.raises(NotImplementedError):
        orig_torrent.func(edit_tracker_func)()


@pytest.mark.skipif_before_api_version("2.2.0")
@pytest.mark.parametrize("remove_trackers_func", ["remove_trackers", "removeTrackers"])
@pytest.mark.parametrize("trackers", ["127.0.2.2", ["127.0.2.3", "127.0.2.4"]])
def test_remove_trackers(orig_torrent, remove_trackers_func, trackers):
    check(
        lambda: (t.url for t in orig_torrent.trackers),
        trackers,
        reverse=True,
        negate=True,
    )
    orig_torrent.add_trackers(urls=trackers)
    check(lambda: (t.url for t in orig_torrent.trackers), trackers, reverse=True)
    orig_torrent.func(remove_trackers_func)(urls=trackers)
    check(
        lambda: (t.url for t in orig_torrent.trackers),
        trackers,
        reverse=True,
        negate=True,
    )


@pytest.mark.skipif_after_api_version("2.2.0")
@pytest.mark.parametrize("remove_trackers_func", ["remove_trackers", "removeTrackers"])
def test_remove_trackers_not_implemented(orig_torrent, remove_trackers_func):
    with pytest.raises(NotImplementedError):
        orig_torrent.func(remove_trackers_func)()


def test_webseeds(orig_torrent):
    assert isinstance(orig_torrent.webseeds, WebSeedsList)


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize("add_webseeds_func", ["add_webseeds", "addWebSeeds"])
@pytest.mark.parametrize(
    "webseeds",
    [
        "http://example/webseedone",
        ["http://example/webseedone", "http://example/webseedtwo"],
    ],
)
def test_add_webseed(new_torrent, add_webseeds_func, webseeds):
    assert new_torrent.webseeds == WebSeedsList([])
    new_torrent.func(add_webseeds_func)(urls=webseeds)
    assert sorted([w.url for w in new_torrent.webseeds]) == (
        webseeds if isinstance(webseeds, list) else [webseeds]
    )


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize("edit_webseed_func", ["edit_webseed", "editWebSeed"])
def test_edit_webseeds(new_torrent, edit_webseed_func):
    assert new_torrent.webseeds == WebSeedsList([])
    new_torrent.add_webseeds(urls="http://example/asdf")
    new_torrent.edit_webseed(
        orig_url="http://example/asdf", new_url="http://example/vbnm"
    )
    assert new_torrent.webseeds[0].url == "http://example/vbnm"


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize("remove_webseeds_func", ["remove_webseeds", "removeWebSeeds"])
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
    new_torrent.func(remove_webseeds_func)(urls=webseeds)
    for webseed in webseeds if isinstance(webseeds, list) else [webseeds]:
        assert webseed not in {w.url for w in new_torrent.webseeds}


def test_files(orig_torrent):
    assert isinstance(orig_torrent.files, TorrentFilesList)
    assert "id" in orig_torrent.files[0]


def test_recheck(orig_torrent):
    orig_torrent.recheck()


@pytest.mark.skipif_before_api_version("2.0.2")
def test_reannounce(orig_torrent):
    orig_torrent.reannounce()


@pytest.mark.skipif_after_api_version("2.0.2")
def test_reannounce_not_implemented(orig_torrent):
    with pytest.raises(NotImplementedError):
        orig_torrent.reannounce()


@pytest.mark.skipif_before_api_version("2.10")
def test_reannounce_in(orig_torrent):
    assert "reannounce_in" in orig_torrent.info
    assert type(orig_torrent.reannounce) is MethodType


@pytest.mark.skipif_after_api_version("2.10")
def test_reannounce_in_not_present(orig_torrent):
    assert "reannounce_in" not in orig_torrent.info


@pytest.mark.skipif_before_api_version("2.4.0")
@pytest.mark.parametrize("rename_file_func", ["rename_file", "renameFile"])
@pytest.mark.parametrize("name", ["new_name", "new name"])
def test_rename_file(app_version, new_torrent, rename_file_func, name):
    @retry()
    def run_test_old():
        new_torrent.func(rename_file_func)(file_id=0, new_file_name=name)
        check(lambda: new_torrent.files[0].name, name)

    run_test_old()

    if v(app_version) >= v("v4.3.3"):

        @retry()
        def run_test_new():
            curr_name = new_torrent.files[0].name
            new_name = "NEW_" + name
            new_torrent.func(rename_file_func)(old_path=curr_name, new_path=new_name)
            check(lambda: new_torrent.files[0].name, new_name)

        run_test_new()


@pytest.mark.skipif_after_api_version("2.4.0")
@pytest.mark.parametrize("rename_file_func", ["rename_file", "renameFile"])
def test_rename_file_not_implemented(new_torrent, rename_file_func):
    with pytest.raises(NotImplementedError):
        new_torrent.func(rename_file_func)()


@pytest.mark.skipif_before_api_version("2.7")
@pytest.mark.parametrize("rename_folder_func", ["rename_folder", "renameFolder"])
@pytest.mark.parametrize("name", ["new_name", "new name"])
def test_rename_folder(app_version, new_torrent, rename_folder_func, name):
    # need to ensure we're at least on v4.3.3 to run test since
    # both v4.3.2 and v4.3.2 both use Web API 2.7
    if v(app_version) >= v("v4.3.3"):
        # move the file in to a new folder
        orig_file_path = new_torrent.files[0].name
        new_folder = "qwer"
        new_torrent.rename_file(
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
        new_torrent.func(rename_folder_func)(
            old_path=new_folder,
            new_path=name,
        )
        check(
            lambda: new_torrent.files[0].name.replace("+", " "),
            name + "/" + orig_file_path,
        )


@pytest.mark.skipif_after_api_version("2.4.0")
@pytest.mark.parametrize("rename_folder_func", ["rename_folder", "renameFolder"])
def test_rename_folder_not_implemented(new_torrent, rename_folder_func):
    with pytest.raises(NotImplementedError):
        new_torrent.func(rename_folder_func)()


@pytest.mark.skipif_before_api_version("2.8.14")
def test_export(orig_torrent):
    assert isinstance(orig_torrent.export(), bytes)


@pytest.mark.skipif_after_api_version("2.8.14")
def test_export_not_implemented(orig_torrent):
    with pytest.raises(NotImplementedError):
        orig_torrent.export()


@pytest.mark.parametrize("piece_states_func", ["piece_states", "pieceStates"])
def test_piece_states(orig_torrent, piece_states_func):
    assert isinstance(orig_torrent.func(piece_states_func), TorrentPieceInfoList)


@pytest.mark.parametrize("piece_hashes_func", ["piece_hashes", "pieceHashes"])
def test_piece_hashes(orig_torrent, piece_hashes_func):
    assert isinstance(orig_torrent.func(piece_hashes_func), TorrentPieceInfoList)


@pytest.mark.parametrize("file_prio_func", ["file_priority", "filePriority"])
def test_file_priority(orig_torrent, file_prio_func):
    orig_torrent.func(file_prio_func)(file_ids=0, priority=7)
    check(lambda: orig_torrent.files[0].priority, 7)


@pytest.mark.parametrize("name", ["new_name", "new name"])
def test_rename(new_torrent, name):
    new_torrent.rename(new_name=name)
    check(lambda: new_torrent.info.name.replace("+", " "), name)


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "add_tags_func, remove_tags_func",
    [("add_tags", "remove_tags"), ("addTags", "removeTags")],
)
@pytest.mark.parametrize("tags", ["tag 1", ["tag 2", "tag 3"]])
def test_add_remove_tags(client, orig_torrent, add_tags_func, remove_tags_func, tags):
    try:
        orig_torrent.func(add_tags_func)(tags=tags)
        check(lambda: orig_torrent.info.tags, tags, reverse=True)

        orig_torrent.func(remove_tags_func)(tags=tags)
        check(lambda: orig_torrent.info.tags, tags, reverse=True, negate=True)
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_after_api_version("2.3.0")
@pytest.mark.parametrize(
    "add_tags_func, remove_tags_func",
    [("add_tags", "remove_tags"), ("addTags", "removeTags")],
)
def test_add_remove_tags_not_implemented(
    client, orig_torrent, add_tags_func, remove_tags_func
):
    with pytest.raises(NotImplementedError):
        orig_torrent.func(add_tags_func)()
    with pytest.raises(NotImplementedError):
        orig_torrent.func(remove_tags_func)()


@pytest.mark.skipif_before_api_version("2.11.4")
@pytest.mark.parametrize("set_tags_func", ["set_tags", "setTags"])
@pytest.mark.parametrize("tags", ["tag 1", ["tag 2", "tag 3"]])
def test_set_tags(client, orig_torrent, set_tags_func, tags):
    try:
        orig_torrent.add_tags(tags="extra-tag")
        orig_torrent.func(set_tags_func)(tags=tags)
        check(lambda: orig_torrent.info.tags, tags, reverse=True)
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_after_api_version("2.11.4")
@pytest.mark.parametrize("set_tags_func", ["set_tags", "setTags"])
def test_set_tags_not_implemented(client, orig_torrent, set_tags_func):
    with pytest.raises(NotImplementedError):
        orig_torrent.func(set_tags_func)()
