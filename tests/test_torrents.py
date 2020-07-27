from os import path
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
from qbittorrentapi.exceptions import TorrentFileNotFoundError
from qbittorrentapi.exceptions import TorrentFilePermissionError
from qbittorrentapi.helpers import is_version_less_than
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

from tests.conftest import check, filename1, filename2, hash1, hash2, url1, url2


def get_func(client, func_str):
    func = client
    for attr in func_str.split('.'):
        func = getattr(func, attr)
    return func


def disable_queueing(client):
    if client.app.preferences.queueing_enabled:
        client.app.preferences = dict(queueing_enabled=False)


def enable_queueing(client):
    if not client.app.preferences.queueing_enabled:
        client.app.preferences = dict(queueing_enabled=True)


@pytest.mark.parametrize('client_func', (('torrents_add', 'torrents_delete'),
                                         ('torrents.add', 'torrents.delete')))
def test_add_delete(client, api_version, client_func):
    def download_file(url, filename):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with requests.get(url) as r:
                    r.raise_for_status()
                    with open(path.expanduser('~/%s' % filename), 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024):
                            f.write(chunk)
            except (Exception if attempt < (max_attempts - 1) else ZeroDivisionError):
                pass  # throw away errors until we hit the retry limit
            else:
                return
        raise Exception('Download failed: %s' % url)

    def delete():
        get_func(client, client_func[1])(delete_files=True, torrent_hashes=hash1)
        get_func(client, client_func[1])(delete_files=True, torrent_hashes=hash2)
        check(lambda: [t.hash for t in client.torrents_info()], hash2, reverse=True, negate=True)

    def check_torrents_added():
        try:
            check(lambda: [t.hash for t in client.torrents_info()], hash1, reverse=True)
            check(lambda: [t.hash for t in client.torrents_info()], hash2, reverse=True)
        finally:
            delete()

    def add_by_file():
        download_file(url=url1, filename=filename1)
        download_file(url=url2, filename=filename2)
        files = ('~/%s' % filename1, '~/%s' % filename2)
        assert get_func(client, client_func[0])(torrent_files=files) == 'Ok.'

    def add_by_url():
        get_func(client, client_func[0])(urls=(url1, url2))

    if is_version_less_than('2.0.0', api_version, lteq=False):
        add_by_file()
        sleep(2)
        check_torrents_added()
        sleep(2)
        add_by_url()
        sleep(2)
        check_torrents_added()


def test_add_torrent_file_fail(client):
    with pytest.raises(TorrentFileNotFoundError):
        client.torrents_add(torrent_files='/tmp/asdfasdfasdfasdf')

    with pytest.raises(TorrentFilePermissionError):
        client.torrents_add(torrent_files='/etc/shadow')


def test_add_options(api_version, test_torrent):
    check(lambda: test_torrent.category, 'test_category')
    check(lambda: test_torrent.state, 'pausedDL')
    check(lambda: test_torrent.save_path, path.expanduser('~/test_download/'))
    check(lambda: test_torrent.up_limit, 1024)
    check(lambda: test_torrent.dl_limit, 2048)
    check(lambda: test_torrent.seq_dl, True)
    if is_version_less_than('2.0.0', api_version, lteq=False):
        check(lambda: test_torrent.f_l_piece_prio, True)


def test_properties(client, test_torrent):
    props = client.torrents_properties(torrent_hash=test_torrent.hash)
    assert isinstance(props, TorrentPropertiesDictionary)


def test_trackers(client, test_torrent):
    trackers = client.torrents_trackers(torrent_hash=test_torrent.hash)
    assert isinstance(trackers, TrackersList)


def test_webseeds(client, test_torrent):
    web_seeds = client.torrents_webseeds(torrent_hash=test_torrent.hash)
    assert isinstance(web_seeds, WebSeedsList)


def test_files(client, test_torrent):
    files = client.torrents_files(torrent_hash=test_torrent.hash)
    assert isinstance(files, TorrentFilesList)
    assert 'availability' in files[0]


@pytest.mark.parametrize('client_func', ('torrents_piece_states', 'torrents_pieceStates'))
def test_piece_states(client, test_torrent, client_func):
    piece_states = get_func(client, client_func)(torrent_hash=test_torrent.hash)
    assert isinstance(piece_states, TorrentPieceInfoList)


@pytest.mark.parametrize('client_func', ('torrents_piece_hashes', 'torrents_pieceHashes'))
def test_piece_hashes(client, test_torrent, client_func):
    piece_hashes = get_func(client, client_func)(torrent_hash=test_torrent.hash)
    assert isinstance(piece_hashes, TorrentPieceInfoList)


@pytest.mark.parametrize('trackers', ('127.0.0.1', ('127.0.0.2', '127.0.0.3')))
@pytest.mark.parametrize('client_func', ('torrents_add_trackers', 'torrents_addTrackers'))
def test_add_trackers(client, trackers, client_func, test_torrent):
    get_func(client, client_func)(torrent_hash=test_torrent.hash, urls=trackers)
    check(lambda: (t.url for t in test_torrent.trackers), trackers, reverse=True)


@pytest.mark.parametrize('client_func', ('torrents_edit_tracker', 'torrents_editTracker'))
def test_edit_tracker(client, api_version, client_func, test_torrent):
    if is_version_less_than(api_version, '2.2.0', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(torrent_hash=test_torrent.hash, original_url='127.1.0.1', new_url='127.1.0.2')
    else:
        test_torrent.add_trackers('127.1.0.1')
        get_func(client, client_func)(torrent_hash=test_torrent.hash, original_url='127.1.0.1', new_url='127.1.0.2')
        check(lambda: (t.url for t in test_torrent.trackers), '127.1.0.2', reverse=True)


@pytest.mark.parametrize('trackers', (('127.2.0.1',), ('127.2.0.2', '127.2.0.3'),))
@pytest.mark.parametrize('client_func', ('torrents_remove_trackers', 'torrents_removeTrackers'))
def test_remove_trackers(client, api_version, trackers, client_func, test_torrent):
    if is_version_less_than(api_version, '2.2.0', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(torrent_hash=test_torrent.hash, urls=trackers)
    else:
        test_torrent.add_trackers(trackers)
        get_func(client, client_func)(torrent_hash=test_torrent.hash, urls=trackers)
        check(lambda: (t.url for t in test_torrent.trackers), trackers, reverse=True, negate=True)


@pytest.mark.parametrize('client_func', ('torrents_file_priority', 'torrents_filePrio'))
def test_file_priority(client, torrent, torrent_hash, client_func, test_torrent):
    get_func(client, client_func)(torrent_hash=torrent_hash, file_ids=0, priority=7)
    check(lambda: torrent.files[0].priority, 7)


@pytest.mark.parametrize('new_name', (('new name', 'new_name'),))
def test_rename(client, torrent_hash, torrent, new_name):
    client.torrents_rename(torrent_hash=torrent_hash, new_torrent_name=new_name[0])
    check(lambda: torrent.info.name.replace('+', ' '), new_name[0])


@pytest.mark.parametrize('new_name', ('new name file 1', 'new_name_file_1'))
@pytest.mark.parametrize('client_func', ('torrents_rename_file', 'torrents_renameFile'))
def test_rename_file(client, api_version, torrent_hash, torrent, new_name, client_func):
    if is_version_less_than(api_version, '2.4.0', lteq=False):
        with pytest.raises(NotImplementedError):
            getattr(client, client_func)(torrent_hash=torrent_hash, file_id=0, new_file_name=new_name[0])
    else:
        getattr(client, client_func)(torrent_hash=torrent_hash, file_id=0, new_file_name=new_name[0])
        check(lambda: torrent.files[0].name.replace('+', ' '), new_name[0])


@pytest.mark.parametrize('client_func', ('torrents_info', 'torrents.info'))
def test_torrents_info(client, api_version, torrent_hash, client_func):
    assert isinstance(get_func(client, client_func)(), TorrentInfoList)
    if '.' in client_func:
        assert isinstance(get_func(client, client_func).all(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).downloading(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).completed(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).paused(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).active(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).inactive(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).resumed(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).stalled(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).stalled_uploading(), TorrentInfoList)
        assert isinstance(get_func(client, client_func).stalled_downloading(), TorrentInfoList)

    if is_version_less_than(api_version, '2.0.1', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(torrent_hashes=torrent_hash)


@pytest.mark.parametrize('client_func', (('torrents_pause', 'torrents_resume'),
                                         ('torrents.pause', 'torrents.resume')))
def test_pause_resume(client, torrent_hash, client_func):
    get_func(client, client_func[0])(torrent_hashes=torrent_hash)
    check(lambda: client.torrents_info(torrents_hashes=torrent_hash)[0].state, ('stalledDL', 'pausedDL'))

    get_func(client, client_func[1])(torrent_hashes=torrent_hash)
    check(lambda: client.torrents_info(torrents_hashes=torrent_hash)[0].state, ('pausedDL',), negate=True)


def test_action_for_all_torrents(client, test_torrent):
    client.torrents.pause.all()
    for torrent in client.torrents.info():
        check(lambda: client.torrents_info(torrents_hashes=torrent.hash)[0].state, ('stalledDL', 'pausedDL'))
    client.torrents.resume.all()
    for torrent in client.torrents.info():
        check(lambda: client.torrents_info(torrents_hashes=torrent.hash)[0].state, ('pausedDL',), negate=True)


@pytest.mark.parametrize('client_func', ('torrents_recheck', 'torrents.recheck'))
def test_recheck(client, torrent_hash, client_func):
    get_func(client, client_func)(torrent_hashes=torrent_hash)


@pytest.mark.parametrize('client_func', ('torrents_reannounce', 'torrents.reannounce'))
def test_reannounce(client, torrent_hash, client_func):
    sleep(2)
    get_func(client, client_func)(torrent_hashes=torrent_hash)


@pytest.mark.parametrize('client_func', (('torrents_increase_priority', 'torrents_decrease_priority', 'torrents_top_priority', 'torrents_bottom_priority'),
                                         ('torrents_increasePrio', 'torrents_decreasePrio', 'torrents_topPrio', 'torrents_bottomPrio')))
def test_priority(client, test_torrent, client_func):
    disable_queueing(client)

    with pytest.raises(Conflict409Error):
        get_func(client, client_func[0])(torrent_hashes=test_torrent.hash)
    with pytest.raises(Conflict409Error):
        get_func(client, client_func[1])(torrent_hashes=test_torrent.hash)
    with pytest.raises(Conflict409Error):
        get_func(client, client_func[2])(torrent_hashes=test_torrent.hash)
    with pytest.raises(Conflict409Error):
        get_func(client, client_func[3])(torrent_hashes=test_torrent.hash)

    enable_queueing(client)

    current_priority = test_torrent.info.priority
    get_func(client, client_func[0])(torrent_hashes=test_torrent.hash)
    check(lambda: test_torrent.info.priority < current_priority, True)

    current_priority = test_torrent.info.priority
    get_func(client, client_func[1])(torrent_hashes=test_torrent.hash)
    check(lambda: test_torrent.info.priority > current_priority, True)

    current_priority = test_torrent.info.priority
    get_func(client, client_func[2])(torrent_hashes=test_torrent.hash)
    check(lambda: test_torrent.info.priority < current_priority, True)

    current_priority = test_torrent.info.priority
    get_func(client, client_func[3])(torrent_hashes=test_torrent.hash)
    check(lambda: test_torrent.info.priority > current_priority, True)


@pytest.mark.parametrize('client_func', (('torrents_set_download_limit', 'torrents_download_limit'),
                                         ('torrents_setDownloadLimit', 'torrents_downloadLimit'),
                                         ('torrents.set_download_limit', 'torrents.download_limit'),
                                         ('torrents.setDownloadLimit', 'torrents.downloadLimit')))
def test_download_limit(client, client_func, test_torrent):
    get_func(client, client_func[0])(torrent_hashes=test_torrent.hash, limit=100)
    assert isinstance(get_func(client, client_func[1])(torrent_hashes=test_torrent.hash), TorrentLimitsDictionary)
    check(lambda: get_func(client, client_func[1])(torrent_hashes=test_torrent.hash)[test_torrent.hash], 100)


@pytest.mark.parametrize('client_func', (('torrents_set_upload_limit', 'torrents_upload_limit'),
                                         ('torrents_setUploadLimit', 'torrents_uploadLimit'),
                                         ('torrents.set_upload_limit', 'torrents.upload_limit'),
                                         ('torrents.setUploadLimit', 'torrents.uploadLimit')))
def test_upload_limit(client, client_func, test_torrent):
    get_func(client, client_func[0])(torrent_hashes=test_torrent.hash, limit=100)
    assert isinstance(get_func(client, client_func[1])(torrent_hashes=test_torrent.hash), TorrentLimitsDictionary)
    check(lambda: get_func(client, client_func[1])(torrent_hashes=test_torrent.hash)[test_torrent.hash], 100)


@pytest.mark.parametrize('client_func', ('torrents_set_share_limits', 'torrents_setShareLimits',
                                         'torrents.set_share_limits', 'torrents.setShareLimits'))
def test_set_share_limits(client, api_version, client_func, test_torrent):
    if is_version_less_than(api_version, '2.0.1', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(ratio_limit=2, seeding_time_limit=5, torrent_hashes=test_torrent.hash)
    else:
        get_func(client, client_func)(ratio_limit=2, seeding_time_limit=5, torrent_hashes=test_torrent.hash)
        check(lambda: test_torrent.info.max_ratio, 2)
        check(lambda: test_torrent.info.max_seeding_time, 5)


@pytest.mark.parametrize('client_func', ('torrents_set_location', 'torrents_setLocation',
                                         'torrents.set_location', 'torrents.setLocation'))
def test_set_location(client, api_version, client_func, test_torrent):
    if is_version_less_than('2.0.1', api_version, lteq=False):
        home = path.expanduser('~')
        # whether the location is writable is only checked after version 2.0.1
        if is_version_less_than('2.0.1', api_version, lteq=False):
            with pytest.raises(Forbidden403Error):
                get_func(client, client_func)(location='/etc/', torrent_hashes=test_torrent.hash)

        get_func(client, client_func)(location='%s/Downloads/1/' % home, torrent_hashes=test_torrent.hash)
        check(lambda: test_torrent.info.save_path, '%s/Downloads/1/' % home)


@pytest.mark.parametrize('client_func', ('torrents_set_category', 'torrents_setCategory',
                                         'torrents.set_category', 'torrents.setCategory'))
@pytest.mark.parametrize('name', ('awesome cat', 'awesome_cat'))
def test_set_category(client, client_func, name, test_torrent):
    with pytest.raises(Conflict409Error):
        get_func(client, client_func)(category='/!@#$%^&*(', torrent_hashes=test_torrent.hash)

    client.torrents_create_category(name=name)
    try:
        get_func(client, client_func)(category=name, torrent_hashes=test_torrent.hash)
        check(lambda: test_torrent.info.category.replace('+', ' '), name)
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize('client_func', ('torrents_set_auto_management', 'torrents_setAutoManagement',
                                         'torrents.set_auto_management', 'torrents.setAutoManagement'))
def test_torrents_set_auto_management(client, client_func, test_torrent):
    current_setting = test_torrent.info.auto_tmm
    get_func(client, client_func)(enable=(not current_setting), torrent_hashes=test_torrent.hash)
    check(lambda: test_torrent.info.auto_tmm, (not current_setting))


@pytest.mark.parametrize('client_func', ('torrents_toggle_sequential_download', 'torrents_toggleSequentialDownload',
                                         'torrents.toggle_sequential_download', 'torrents.toggleSequentialDownload'))
def test_toggle_sequential_download(client, client_func, test_torrent):
    current_setting = test_torrent.info.seq_dl
    get_func(client, client_func)(torrent_hashes=test_torrent.hash)
    check(lambda: test_torrent.info.seq_dl, not current_setting)


@pytest.mark.parametrize('client_func', ('torrents_toggle_first_last_piece_priority', 'torrents_toggleFirstLastPiecePrio',
                                         'torrents.toggle_first_last_piece_priority', 'torrents.toggleFirstLastPiecePrio'))
def test_toggle_first_last_piece_priority(client, api_version, client_func, test_torrent):
    if is_version_less_than('2.0.0', api_version, lteq=False):
        current_setting = test_torrent.info.f_l_piece_prio
        get_func(client, client_func)(torrent_hashes=test_torrent.hash)
        check(lambda: test_torrent.info.f_l_piece_prio, not current_setting)


@pytest.mark.parametrize('client_func', ('torrents_set_force_start', 'torrents_setForceStart',
                                         'torrents.set_force_start', 'torrents.setForceStart'))
def test_set_force_start(client, client_func, test_torrent):
    current_setting = test_torrent.info.force_start
    get_func(client, client_func)(enable=(not current_setting), torrent_hashes=test_torrent.hash)
    check(lambda: test_torrent.info.force_start, not current_setting)


@pytest.mark.parametrize('client_func', ('torrents_set_super_seeding', 'torrents_setSuperSeeding',
                                         'torrents.set_super_seeding', 'torrents.setSuperSeeding'))
def test_set_super_seeding(client, client_func, test_torrent):
    get_func(client, client_func)(enable=False, torrent_hashes=test_torrent.hash)
    check(lambda: test_torrent.info.force_start, False)


@pytest.mark.parametrize('client_func', ('torrents_add_peers', 'torrents_addPeers',
                                         'torrents.add_peers', 'torrents.addPeers'))
@pytest.mark.parametrize('peers', ('127.0.0.1:5000', ('127.0.0.1:5000', '127.0.0.2:5000'), '127.0.0.1'))
def test_torrents_add_peers(client, api_version, torrent_hash, client_func, peers, test_torrent):
    if is_version_less_than(api_version, '2.3.0', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(peers=peers, torrent_hashes=torrent_hash)
    else:
        if all(map(lambda p: ':' not in p, peers)):
            with pytest.raises(InvalidRequest400Error):
                get_func(client, client_func)(peers=peers, torrent_hashes=test_torrent.hash)
        else:
            p = get_func(client, client_func)(peers=peers, torrent_hashes=test_torrent.hash)
            # can only actually verify the peer was added if it's a valid peer
            # check(lambda: client.sync_torrent_peers(torrent_hash=test_torrent.hash)['peers'], peers, reverse=True)
            assert isinstance(p, TorrentsAddPeersDictionary)


def test_categories1(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_categories()
    else:
        assert isinstance(client.torrents_categories(), TorrentCategoriesDictionary)


def test_categories2(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrent_categories.categories
    else:
        name = 'new_category'
        client.torrent_categories.categories = {'name': name, 'savePath': '/tmp'}
        assert name in client.torrent_categories.categories
        client.torrent_categories.categories = {'name': name, 'savePath': '/tmp/new'}
        assert client.torrent_categories.categories[name]['savePath'] == '/tmp/new'
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize('client_func', ('torrents_create_category', 'torrents_createCategory',
                                         'torrent_categories.create_category', 'torrent_categories.createCategory'))
@pytest.mark.parametrize('save_path', (None, '', '/tmp/'))
@pytest.mark.parametrize('name', ('name', 'name 1'))
def test_create_categories(client, api_version, test_torrent, client_func, save_path, name):
    extra_kwargs = dict(save_path=save_path)
    if is_version_less_than(api_version, '2.1.0', lteq=False) and save_path is not None:
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(name=name, save_path=save_path)
        extra_kwargs = {}

    try:
        get_func(client, client_func)(name=name, **extra_kwargs)
        client.torrents_set_category(torrent_hashes=test_torrent.hash, category=name)
        check(lambda: test_torrent.info.category.replace('+', ' '), name)
        if is_version_less_than('2.1.1', api_version):
            check(lambda: [n.replace('+', ' ') for n in client.torrents_categories()], name, reverse=True)
            check(lambda: (cat.savePath for cat in client.torrents_categories().values()), save_path or '', reverse=True)
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize('client_func', ('torrents_edit_category', 'torrents_editCategory',
                                         'torrent_categories.edit_category', 'torrent_categories.editCategory'))
@pytest.mark.parametrize('save_path', ('', '/tmp/'))
@pytest.mark.parametrize('name', ('editcategory',))
def test_edit_category(client, api_version, client_func, save_path, name):
    if is_version_less_than(api_version, '2.1.0', lteq=False) and save_path is not None:
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(name=name, save_path=save_path)

    if is_version_less_than('2.1.1', api_version):
        try:
            client.torrents_create_category(name=name, save_path='/tmp/tmp')
            get_func(client, client_func)(name=name, save_path=save_path)
            check(lambda: [n.replace('+', ' ') for n in client.torrents_categories()], name, reverse=True)
            check(lambda: (cat.savePath for cat in client.torrents_categories().values()), save_path or '', reverse=True)
        finally:
            client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize('client_func', ('torrents_remove_categories', 'torrents_removeCategories',
                                         'torrent_categories.remove_categories', 'torrent_categories.removeCategories'))
@pytest.mark.parametrize('categories', (('category1',), ('category1', 'category 2')))
def test_remove_category(client, api_version, test_torrent, client_func, categories):
    for name in categories:
        client.torrents_create_category(name=name)
    test_torrent.set_category(category=categories[0])
    get_func(client, client_func)(categories=categories)
    if is_version_less_than('2.1.1', api_version):
        check(lambda: [n.replace('+', ' ') for n in client.torrents_categories()], categories, reverse=True, negate=True)
    check(lambda: test_torrent.info.category, categories[0], negate=True)


@pytest.mark.parametrize('client_func', ('torrents_tags', 'torrent_tags.tags',))
def test_tags(client, api_version, client_func):
    if is_version_less_than(api_version, '2.3.0', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)()
    else:
        try:
            assert isinstance(get_func(client, client_func)(), TagList)
        except:
            assert isinstance(get_func(client, client_func), TagList)


def test_add_tag_though_property(client, api_version):
    name = 'newtag'
    if is_version_less_than(api_version, '2.3.0', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrent_tags.tags = name
    else:
        client.torrent_tags.tags = name
        assert name in client.torrent_tags.tags
        client.torrent_tags.delete_tags(name)
        assert name not in client.torrent_tags.tags


@pytest.mark.parametrize('client_func', ('torrents_add_tags', 'torrents_addTags',
                                         'torrent_tags.add_tags', 'torrent_tags.addTags'))
@pytest.mark.parametrize('tags', (('tag1',), ('tag1', 'tag 2')))
def test_add_tags(client, api_version, test_torrent, client_func, tags):
    if is_version_less_than(api_version, '2.3.0', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(tags=tags, torrent_hashes=test_torrent.hash)
    else:
        try:
            get_func(client, client_func)(tags=tags, torrent_hashes=test_torrent.hash)
            check(lambda: test_torrent.info.tags, tags, reverse=True)
        finally:
            client.torrents_delete_tags(tags=tags)


@pytest.mark.parametrize('client_func', ('torrents_remove_tags', 'torrents_removeTags',
                                         'torrent_tags.remove_tags', 'torrent_tags.removeTags'))
@pytest.mark.parametrize('tags', (('tag1',), ('tag1', 'tag 2')))
def test_remove_tags(client, api_version, test_torrent, client_func, tags):
    if is_version_less_than(api_version, '2.3.0', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(tags=tags, torrent_hashes=test_torrent.hash)
    else:
        try:
            test_torrent.add_tags(tags=tags)
            get_func(client, client_func)(tags=tags, torrent_hashes=test_torrent.hash)
            check(lambda: test_torrent.info.tags, tags, reverse=True, negate=True)
        finally:
            client.torrents_delete_tags(tags=tags)


@pytest.mark.parametrize('client_func', ('torrents_create_tags', 'torrents_createTags',
                                         'torrent_tags.create_tags', 'torrent_tags.createTags'))
@pytest.mark.parametrize('tags', (('tag1',), ('tag1', 'tag 2')))
def test_create_tags(client, api_version, client_func, tags):
    if is_version_less_than(api_version, '2.3.0', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(tags=tags)
    else:
        try:
            get_func(client, client_func)(tags=tags)
            check(lambda: client.torrents_tags(), tags, reverse=True)
        finally:
            client.torrents_delete_tags(tags=tags)


@pytest.mark.parametrize('client_func', ('torrents_delete_tags', 'torrents_deleteTags',
                                         'torrent_tags.delete_tags', 'torrent_tags.deleteTags'))
@pytest.mark.parametrize('tags', (('tag1',), ('tag1', 'tag 2')))
def test_delete_tags(client, api_version, client_func, tags):
    if is_version_less_than(api_version, '2.3.0', lteq=False):
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(tags=tags)
    else:
        client.torrents_create_tags(tags=tags)
        get_func(client, client_func)(tags=tags)
        check(lambda: client.torrents_tags(), tags, reverse=True, negate=True)


