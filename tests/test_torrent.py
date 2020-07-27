from os import path
from time import sleep

import pytest

from qbittorrentapi import Conflict409Error
from qbittorrentapi.helpers import is_version_less_than
from qbittorrentapi.torrents import TorrentPropertiesDictionary
from qbittorrentapi.torrents import TrackersList
from qbittorrentapi.torrents import WebSeedsList
from qbittorrentapi.torrents import TorrentDictionary
from qbittorrentapi.torrents import TorrentFilesList
from qbittorrentapi.torrents import TorrentPieceInfoList

from tests.test_torrents import check, url1, hash1, enable_queueing, disable_queueing


def test_info(test_torrent):
    assert test_torrent.info.hash == test_torrent.hash


def test_sync_local(test_torrent):
    test_torrent.sync_local()
    assert isinstance(test_torrent, TorrentDictionary)


def test_pause_resume(client, test_torrent):
    test_torrent.pause()
    check(lambda: client.torrents_info(torrents_hashes=test_torrent.hash)[0].state, ('stalledDL', 'pausedDL'))

    test_torrent.resume()
    check(lambda: client.torrents_info(torrents_hashes=test_torrent.hash)[0].state, ('pausedDL',), negate=True)


def test_delete(client):
    client.torrents_add(urls=url1)
    check(lambda: [t.hash for t in client.torrents_info()], hash1, reverse=True)
    torrent = [t for t in client.torrents_info() if t.hash == hash1][0]
    torrent.delete(delete_files=True)
    check(lambda: [t.hash for t in client.torrents_info()], hash1, reverse=True, negate=True)


@pytest.mark.parametrize('client_func', (('increase_priority', 'decrease_priority', 'top_priority', 'bottom_priority'),
                                         ('increasePrio', 'decreasePrio', 'topPrio', 'bottomPrio')))
def test_priority(client, test_torrent, client_func):
    disable_queueing(client)

    with pytest.raises(Conflict409Error):
        getattr(test_torrent, client_func[0])()
    with pytest.raises(Conflict409Error):
        getattr(test_torrent, client_func[1])()
    with pytest.raises(Conflict409Error):
        getattr(test_torrent, client_func[2])()
    with pytest.raises(Conflict409Error):
        getattr(test_torrent, client_func[3])()

    enable_queueing(client)

    current_priority = test_torrent.info.priority
    getattr(test_torrent, client_func[0])()
    check(lambda: test_torrent.info.priority < current_priority, True)

    current_priority = test_torrent.info.priority
    getattr(test_torrent, client_func[1])()
    check(lambda: test_torrent.info.priority > current_priority, True)

    current_priority = test_torrent.info.priority
    getattr(test_torrent, client_func[2])()
    check(lambda: test_torrent.info.priority < current_priority, True)

    current_priority = test_torrent.info.priority
    getattr(test_torrent, client_func[3])()
    check(lambda: test_torrent.info.priority > current_priority, True)


@pytest.mark.parametrize('client_func', ('set_share_limits', 'setShareLimits'))
def test_set_share_limits(api_version, test_torrent, client_func):
    if is_version_less_than(api_version, '2.0.1', lteq=False):
        with pytest.raises(NotImplementedError):
            getattr(test_torrent, client_func)(ratio_limit=5, seeding_time_limit=100)
    else:
        getattr(test_torrent, client_func)(ratio_limit=5, seeding_time_limit=100)
        check(lambda: test_torrent.info.max_ratio, 5)
        check(lambda: test_torrent.info.max_seeding_time, 100)


@pytest.mark.parametrize('client_func', (('download_limit', 'set_download_limit'),
                                         ('downloadLimit', 'setDownloadLimit')))
def test_download_limit(test_torrent, client_func):
    setattr(test_torrent, client_func[0], 2048)
    check(lambda: getattr(test_torrent, client_func[0]), 2048)
    check(lambda: test_torrent.info.dl_limit, 2048)

    getattr(test_torrent, client_func[1])(4096)
    check(lambda: getattr(test_torrent, client_func[0]), 4096)
    check(lambda: test_torrent.info.dl_limit, 4096)


@pytest.mark.parametrize('client_func', (('upload_limit', 'set_upload_limit'),
                                         ('uploadLimit', 'setUploadLimit')))
def test_upload_limit(test_torrent, client_func):
    setattr(test_torrent, client_func[0], 2048)
    check(lambda: getattr(test_torrent, client_func[0]), 2048)
    check(lambda: test_torrent.info.up_limit, 2048)

    getattr(test_torrent, client_func[1])(4096)
    check(lambda: getattr(test_torrent, client_func[0]), 4096)
    check(lambda: test_torrent.info.up_limit, 4096)


@pytest.mark.parametrize('client_func', ('set_location', 'setLocation'))
def test_set_location(api_version, test_torrent, client_func):
    if is_version_less_than('2.0.1', api_version, lteq=False):
        loc = path.expanduser('~/Downloads/3/')
        getattr(test_torrent, client_func)(loc)
        check(lambda: test_torrent.info.save_path, loc)


@pytest.mark.parametrize('client_func', ('set_category', 'setCategory'))
@pytest.mark.parametrize('category', ('category 1', 'category_1'))
def test_set_category(client, test_torrent, client_func, category):
    client.torrents_create_category(category=category)
    getattr(test_torrent, client_func)(category=category)
    check(lambda: test_torrent.info.category.replace('+', ' '), category, reverse=True)
    client.torrents_remove_categories(categories=category)


@pytest.mark.parametrize('client_func', ('set_auto_management', 'setAutoManagement'))
def test_set_auto_management(test_torrent, client_func):
    current_setting = test_torrent.auto_tmm
    getattr(test_torrent, client_func)(enable=(not current_setting))
    check(lambda: test_torrent.info.auto_tmm, not current_setting)
    getattr(test_torrent, client_func)(enable=current_setting)
    check(lambda: test_torrent.info.auto_tmm, current_setting)


@pytest.mark.parametrize('client_func', ('toggle_sequential_download', 'toggleSequentialDownload'))
def test_toggle_sequential_download(test_torrent, client_func):
    current_setting = test_torrent.seq_dl
    getattr(test_torrent, client_func)()
    check(lambda: test_torrent.info.seq_dl, not current_setting)
    getattr(test_torrent, client_func)()
    check(lambda: test_torrent.info.seq_dl, current_setting)


@pytest.mark.parametrize('client_func', ('toggle_first_last_piece_priority', 'toggleFirstLastPiecePrio'))
def test_toggle_first_last_piece_priority(api_version, test_torrent, client_func):
    if is_version_less_than('2.0.1', api_version, lteq=False):
        current_setting = test_torrent.f_l_piece_prio
        getattr(test_torrent, client_func)()
        check(lambda: test_torrent.info.f_l_piece_prio, not current_setting)
        getattr(test_torrent, client_func)()
        check(lambda: test_torrent.info.f_l_piece_prio, current_setting)


@pytest.mark.parametrize('client_func', ('set_force_start', 'setForceStart'))
def test_set_force_start(test_torrent, client_func):
    current_setting = test_torrent.force_start
    getattr(test_torrent, client_func)(enable=(not current_setting))
    check(lambda: test_torrent.info.force_start, not current_setting)
    getattr(test_torrent, client_func)(enable=current_setting)
    check(lambda: test_torrent.info.force_start, current_setting)


@pytest.mark.parametrize('client_func', ('set_super_seeding', 'setSuperSeeding'))
def test_set_super_seeding(test_torrent, client_func):
    current_setting = test_torrent.super_seeding
    getattr(test_torrent, client_func)(enable=(not current_setting))
    check(lambda: test_torrent.info.super_seeding, not current_setting)
    getattr(test_torrent, client_func)(enable=current_setting)
    check(lambda: test_torrent.info.super_seeding, current_setting)


def test_properties(test_torrent):
    assert isinstance(test_torrent.properties, TorrentPropertiesDictionary)
    assert 'save_path' in test_torrent.properties


@pytest.mark.parametrize('trackers', ('127.0.0.2', ('127.0.0.3', '127.0.0.4')))
def test_trackers(test_torrent, trackers):
    assert isinstance(test_torrent.trackers, TrackersList)
    assert 'num_peers' in test_torrent.trackers[-1]

    test_torrent.trackers = trackers
    check(lambda: (t.url for t in test_torrent.trackers), trackers, reverse=True)


@pytest.mark.parametrize('client_func', ('add_trackers', 'addTrackers'))
@pytest.mark.parametrize('trackers', ('127.0.0.2', ('127.0.0.3', '127.0.0.4')))
def test_add_tracker(test_torrent, client_func, trackers):
    getattr(test_torrent, client_func)(urls=trackers)
    check(lambda: (t.url for t in test_torrent.trackers), trackers, reverse=True)


@pytest.mark.parametrize('client_func', ('edit_tracker', 'editTracker'))
def test_edit_tracker(api_version, test_torrent, client_func):
    if is_version_less_than(api_version, '2.2.0', lteq=False):
        with pytest.raises(NotImplementedError):
            getattr(test_torrent, client_func)(orig_url='127.0.0.1', new_url='127.0.0.2')
    else:
        test_torrent.add_trackers(urls='127.0.0.1')
        getattr(test_torrent, client_func)(orig_url='127.0.0.1', new_url='127.0.0.2')
        check(lambda: (t.url for t in test_torrent.trackers), '127.0.0.1', reverse=True, negate=True)
        check(lambda: (t.url for t in test_torrent.trackers), '127.0.0.2', reverse=True)


@pytest.mark.parametrize('client_func', ('remove_trackers', 'removeTrackers'))
@pytest.mark.parametrize('trackers', ('127.0.0.2', ('127.0.0.3', '127.0.0.4')))
def test_remove_trackers(api_version, test_torrent, client_func, trackers):
    if is_version_less_than(api_version, '2.2.0', lteq=False):
        with pytest.raises(NotImplementedError):
            getattr(test_torrent, client_func)(urls=trackers)
    else:
        check(lambda: (t.url for t in test_torrent.trackers), trackers, reverse=True, negate=True)
        test_torrent.add_trackers(urls=trackers)
        check(lambda: (t.url for t in test_torrent.trackers), trackers, reverse=True)
        getattr(test_torrent, client_func)(urls=trackers)
        check(lambda: (t.url for t in test_torrent.trackers), trackers, reverse=True, negate=True)


def test_webseeds(test_torrent):
    assert isinstance(test_torrent.webseeds, WebSeedsList)


def test_files(test_torrent):
    assert isinstance(test_torrent.files, TorrentFilesList)
    assert 'id' in test_torrent.files[0]


def test_recheck(client, torrent):
    torrent.recheck()


def test_reannounce(client, torrent):
    torrent.reannounce()


@pytest.mark.parametrize('client_func', ('rename_file', 'renameFile'))
@pytest.mark.parametrize('name', ('new_name', 'new name'))
def test_rename_file(api_version, test_torrent, client_func, name):
    if is_version_less_than(api_version, '2.4.0', lteq=False):
        with pytest.raises(NotImplementedError):
            getattr(test_torrent, client_func)(file_id=0, new_file_name=name)
    else:
        getattr(test_torrent, client_func)(file_id=0, new_file_name=name)
        check(lambda: test_torrent.files[0].name, name)


@pytest.mark.parametrize('client_func', ('piece_states', 'pieceStates'))
def test_piece_states(test_torrent, client_func):
    assert isinstance(getattr(test_torrent, client_func), TorrentPieceInfoList)


@pytest.mark.parametrize('client_func', ('piece_hashes', 'pieceHashes'))
def test_piece_hashes(test_torrent, client_func):
    assert isinstance(getattr(test_torrent, client_func), TorrentPieceInfoList)


@pytest.mark.parametrize('client_func', ('file_priority', 'filePriority'))
def test_file_priority(test_torrent, client_func):
    getattr(test_torrent, client_func)(file_ids=0, priority=7)
    check(lambda: test_torrent.files[0].priority, 7)


@pytest.mark.parametrize('name', ('new_name', 'new name'))
def test_rename(test_torrent, name):
    test_torrent.rename(new_name=name)
    check(lambda: test_torrent.info.name.replace('+', ' '), name)


@pytest.mark.parametrize('client_func', (('add_tags', 'remove_tags'),
                                         ('addTags', 'removeTags')))
@pytest.mark.parametrize('tags', ('tag 1', ('tag 2', 'tag 3')))
def test_add_remove_tags(client, api_version, test_torrent, client_func, tags):
    if is_version_less_than(api_version, '2.3.0', lteq=False):
        with pytest.raises(NotImplementedError):
            getattr(test_torrent, client_func[0])(tags=tags)
        with pytest.raises(NotImplementedError):
            getattr(test_torrent, client_func[1])(tags=tags)
    else:
        getattr(test_torrent, client_func[0])(tags=tags)
        check(lambda: test_torrent.info.tags, tags, reverse=True)

        getattr(test_torrent, client_func[1])(tags=tags)
        check(lambda: test_torrent.info.tags, tags, reverse=True, negate=True)

        client.torrents_delete_tags(tags=tags)
