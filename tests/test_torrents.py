from os import path
from time import sleep

import pytest
import requests

from qbittorrentapi.exceptions import Forbidden403Error
from qbittorrentapi.exceptions import Conflict409Error
from qbittorrentapi.helpers import is_version_less_than
from qbittorrentapi.torrents import TorrentPropertiesDictionary
from qbittorrentapi.torrents import TrackersList
from qbittorrentapi.torrents import WebSeedsList
from qbittorrentapi.torrents import TorrentFilesList
from qbittorrentapi.torrents import TorrentPieceInfoList
from qbittorrentapi.torrents import TorrentInfoList
from qbittorrentapi.torrents import TorrentLimitsDictionary

check_limit = 10

url1 = 'http://releases.ubuntu.com/18.04/ubuntu-18.04.4-desktop-amd64.iso.torrent'
filename1 = url1.split('/')[-1]
hash1 = '286d2e5b4f8369855328336ac1263ae02a7a60d5'

url2 = 'https://releases.ubuntu.com/20.04/ubuntu-20.04-desktop-amd64.iso.torrent'
filename2 = url2.split('/')[-1]
hash2 = '9fc20b9e98ea98b4a35e6223041a5ef94ea27809'


def test_add_delete(client):
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
        client.torrents_delete(delete_files=True, torrent_hashes=hash1)
        client.torrents_delete(delete_files=True, torrent_hashes=hash2)
        for i in range(check_limit):
            try:
                torrent_hashes = [t.hash for t in client.torrents_info()]
                assert hash1 not in torrent_hashes
                assert hash2 not in torrent_hashes
                break
            except:
                if i >= check_limit-1:
                    raise
                sleep(1)  # wait for torrents to fully load

    def check_torrents_added():
        try:
            for i in range(check_limit):
                try:
                    torrent_hashes = [t.hash for t in client.torrents_info()]
                    assert hash1 in torrent_hashes
                    assert hash2 in torrent_hashes
                    break
                except:
                    if i >= check_limit - 1:
                        raise
                    sleep(1)  # wait for torrents to fully load
        finally:
            delete()

    def add_by_file():
        download_file(url=url1, filename=filename1)
        download_file(url=url2, filename=filename2)
        assert client.torrents_add(torrent_files=('~/%s' % filename1, '~/%s' % filename2)) == 'Ok.'

    def add_by_url():
        client.torrents_add(urls=(url1, url2))

    add_by_file()
    sleep(1)
    check_torrents_added()
    sleep(1)
    add_by_url()
    sleep(1)
    check_torrents_added()


def test_add_options(client):
    client.torrents.add(urls=url1,
                        save_path=path.expanduser('~/test_download/'),
                        category='test_category', is_paused=True,
                        upload_limit=1024, download_limit=2048,
                        is_sequential_download=True, is_first_last_piece_priority=True)

    for i in range(check_limit):
        try:
            torrent = client.torrents_info(torrent_hashes=hash1)[0]
            assert torrent.category == 'test_category'
            assert torrent.state == 'pausedDL'
            assert torrent.save_path == path.expanduser('~/test_download/')
            assert torrent.up_limit == 1024
            assert torrent.dl_limit == 2048
            assert torrent.seq_dl is True
            assert torrent.f_l_piece_prio is True
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)

    torrent.delete(delete_files=True)


def test_properties(client, torrent_hash):
    props = client.torrents_properties(torrent_hash=torrent_hash)
    assert isinstance(props, TorrentPropertiesDictionary)
    assert 'save_path' in props


def test_trackers(client, torrent_hash):
    trackers = client.torrents_trackers(torrent_hash=torrent_hash)
    assert isinstance(trackers, TrackersList)
    assert 'num_peers' in trackers[0]


def test_webseeds(client, torrent_hash):
    web_seeds = client.torrents_webseeds(torrent_hash=torrent_hash)
    assert isinstance(web_seeds, WebSeedsList)


def test_files(client, torrent_hash):
    files = client.torrents_files(torrent_hash=torrent_hash)
    assert isinstance(files, TorrentFilesList)
    assert 'availability' in files[0]


def test_piece_states(client, torrent_hash):
    piece_states = client.torrents_piece_states(torrent_hash=torrent_hash)
    assert isinstance(piece_states, TorrentPieceInfoList)

    piece_states = client.torrents_pieceStates(torrent_hash=torrent_hash)
    assert isinstance(piece_states, TorrentPieceInfoList)


def test_piece_hashes(client, torrent_hash):
    piece_hashes = client.torrents_piece_hashes(torrent_hash=torrent_hash)
    assert isinstance(piece_hashes, TorrentPieceInfoList)

    piece_hashes = client.torrents_pieceHashes(torrent_hash=torrent_hash)
    assert isinstance(piece_hashes, TorrentPieceInfoList)


def test_add_trackers(client, torrent, torrent_hash):
    client.torrents_add_trackers(torrent_hash=torrent_hash, urls='127.0.0.1')
    assert '127.0.0.1' in (t.url for t in torrent.trackers)
    client.torrents_add_trackers(torrent_hash=torrent_hash, urls=('127.0.0.2', '127.0.0.3'))
    assert '127.0.0.2' in (t.url for t in torrent.trackers)
    assert '127.0.0.3' in (t.url for t in torrent.trackers)

    client.torrents_addTrackers(torrent_hash=torrent_hash, urls='127.0.1.1')
    assert '127.0.1.1' in (t.url for t in torrent.trackers)
    client.torrents_addTrackers(torrent_hash=torrent_hash, urls=('127.0.1.2', '127.0.1.3'))
    assert '127.0.1.2' in (t.url for t in torrent.trackers)
    assert '127.0.1.3' in (t.url for t in torrent.trackers)


def test_edit_tracker(client, api_version, torrent, torrent_hash):
    if is_version_less_than(api_version, '2.2.0', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_edit_tracker(torrent_hash=torrent_hash, original_url='127.1.0.1', new_url='127.1.0.2')
    else:
        torrent.add_trackers('127.1.0.1')
        client.torrents_edit_tracker(torrent_hash=torrent_hash, original_url='127.1.0.1', new_url='127.1.0.2')
        assert '127.1.0.2' in (t.url for t in torrent.trackers)

    if is_version_less_than(api_version, '2.2.0', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_editTracker(torrent_hash=torrent_hash, original_url='127.1.1.1', new_url='127.1.0.2')
    else:
        torrent.add_trackers('127.1.1.1')
        client.torrents_editTracker(torrent_hash=torrent_hash, original_url='127.1.1.1', new_url='127.1.1.2')
        assert '127.1.1.2' in (t.url for t in torrent.trackers)


def test_remove_trackers(client, api_version, torrent, torrent_hash):
    if is_version_less_than(api_version, '2.2.0', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_remove_trackers(torrent_hash=torrent_hash, urls='127.2.0.1')
    else:
        torrent.add_trackers('127.2.0.1')
        client.torrents_remove_trackers(torrent_hash=torrent_hash, urls='127.2.0.1')
        assert '127.2.0.1' not in (t.url for t in torrent.trackers)
        torrent.add_trackers(('127.2.0.1', '127.2.0.2'))
        client.torrents_remove_trackers(torrent_hash=torrent_hash, urls=('127.2.0.1', '127.2.0.2'))
        assert '127.2.0.1' not in (t.url for t in torrent.trackers)
        assert '127.2.0.2' not in (t.url for t in torrent.trackers)

    if is_version_less_than(api_version, '2.2.0', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_remove_trackers(torrent_hash=torrent_hash, urls='127.2.0.1')
    else:
        torrent.add_trackers('127.2.0.1')
        client.torrents_removeTrackers(torrent_hash=torrent_hash, urls='127.2.0.1')
        assert '127.2.0.1' not in (t.url for t in torrent.trackers)
        torrent.add_trackers(('127.2.0.1', '127.2.0.2'))
        client.torrents_removeTrackers(torrent_hash=torrent_hash, urls=('127.2.0.1', '127.2.0.2'))
        assert '127.2.0.1' not in (t.url for t in torrent.trackers)
        assert '127.2.0.2' not in (t.url for t in torrent.trackers)


def test_file_priority(client, torrent, torrent_hash):
    client.torrents_file_priority(torrent_hash=torrent_hash, file_ids=0, priority=7)
    for i in range(check_limit):
        try:
            assert torrent.files[0].priority == 7
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)  # wait for the change to take effect
    client.torrents_filePrio(torrent_hash=torrent_hash, file_ids=0, priority=6)
    for i in range(check_limit):
        try:
            assert torrent.files[0].priority == 6
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)  # wait for the change to take effect


def test_rename(client, torrent_hash, torrent):
    new_name = 'new name'
    client.torrents_rename(torrent_hash=torrent_hash, new_torrent_name=new_name)
    assert torrent.info.name == new_name


def test_rename_file(client, api_version, torrent_hash, torrent):
    if is_version_less_than(api_version, '2.4.0', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_rename_file(torrent_hash=torrent_hash, file_id=0, new_file_name='new name 1')
    else:
        client.torrents_rename_file(torrent_hash=torrent_hash, file_id=0, new_file_name='new name 1')
        for i in range(check_limit):
            try:
                assert torrent.files[0].name == 'new name 1'
            except:
                if i >= check_limit - 1:
                    raise
                sleep(1)

    if is_version_less_than(api_version, '2.4.0', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_rename_file(torrent_hash=torrent_hash, file_id=0, new_file_name='new name 1')
    else:
        client.torrents_renameFile(torrent_hash=torrent_hash, file_id=0, new_file_name='new name 1')
        for i in range(check_limit):
            try:
                assert torrent.files[0].name == 'new name 1'
            except:
                if i >= check_limit - 1:
                    raise
                sleep(1)


def test_torrents_info(client, api_version, torrent_hash):
    torrents = client.torrents_info()
    assert isinstance(torrents, TorrentInfoList)

    if is_version_less_than(api_version, '2.0.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_info(torrent_hashes=torrent_hash)


def test_pause_resume(client, torrent_hash):
    client.torrents_pause(torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert client.torrents_info(torrents_hashes=torrent_hash)[0].state in ('stalledDL', 'pausedDL')
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)

    client.torrents_resume(torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert client.torrents_info(torrents_hashes=torrent_hash)[0].state not in ('pausedDL',)
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)


def test_recheck(client, torrent_hash):
    pass # this test isn't reliable...
    # client.torrents_recheck(torrent_hashes=torrent_hash)
    # assert client.torrents_info(torrents_hashes=torrent_hash)[0].state in ('checkingUP', 'checkingDL')


def test_download_limit(client, torrent_hash):
    client.torrents_set_download_limit(torrent_hashes=torrent_hash, limit=100)
    assert isinstance(client.torrents_download_limit(torrent_hashes=torrent_hash), TorrentLimitsDictionary)
    assert client.torrents_download_limit(torrent_hashes=torrent_hash)[torrent_hash] == 100
    client.torrents_setDownloadLimit(torrent_hashes=torrent_hash, limit=100)
    assert isinstance(client.torrents_download_limit(torrent_hashes=torrent_hash), TorrentLimitsDictionary)
    assert client.torrents_downloadLimit(torrent_hashes=torrent_hash)[torrent_hash] == 100


def test_upload_limit(client, torrent_hash):
    client.torrents_set_upload_limit(torrent_hashes=torrent_hash, limit=100)
    assert isinstance(client.torrents_download_limit(torrent_hashes=torrent_hash), TorrentLimitsDictionary)
    assert client.torrents_upload_limit(torrent_hashes=torrent_hash)[torrent_hash] == 100
    client.torrents_setUploadLimit(torrent_hashes=torrent_hash, limit=100)
    assert isinstance(client.torrents_download_limit(torrent_hashes=torrent_hash), TorrentLimitsDictionary)
    assert client.torrents_uploadLimit(torrent_hashes=torrent_hash)[torrent_hash] == 100


def test_set_share_limits(client, api_version, torrent_hash, torrent):
    if is_version_less_than(api_version, '2.0.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_set_share_limits(ratio_limit=2, seeding_time_limit=5, torrent_hashes=torrent_hash)
    else:
        client.torrents_set_share_limits(ratio_limit=2, seeding_time_limit=5, torrent_hashes=torrent_hash)
        assert torrent.info.max_ratio == 2
        assert torrent.info.max_seeding_time == 5

    if is_version_less_than(api_version, '2.0.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.torrents_setShareLimits(ratio_limit=2, seeding_time_limit=5, torrent_hashes=torrent_hash)
    else:
        client.torrents_setShareLimits(ratio_limit=3, seeding_time_limit=6, torrent_hashes=torrent_hash)
        assert torrent.info.max_ratio == 3
        assert torrent.info.max_seeding_time == 6


def test_set_location(client, torrent_hash, torrent):
    home = path.expanduser('~')
    with pytest.raises(Forbidden403Error):
        client.torrents_set_location(location='/etc/', torrent_hashes=torrent_hash)
    with pytest.raises(Forbidden403Error):
        client.torrents_set_location(location='/etc/', torrent_hashes=torrent_hash)

    client.torrents_set_location(location='%s/Downloads/1/' % home, torrent_hashes=torrent_hash)
    assert torrent.info.save_path == '%s/Downloads/1/' % home
    client.torrents_setLocation(location='%s/Downloads/2/' % home, torrent_hashes=torrent_hash)
    assert torrent.info.save_path == '%s/Downloads/2/' % home


def test_set_category(client, torrent_hash, torrent):
    with pytest.raises(Conflict409Error):
        client.torrents_set_category(category='!@#$%^&*(', torrent_hashes=torrent_hash)
    with pytest.raises(Conflict409Error):
        client.torrents_setCategory(category='!@#$%^&*(', torrent_hashes=torrent_hash)

    client.torrents_create_category(name='awesome cat 1')
    client.torrents_create_category(name='awesome cat 2')
    try:
        client.torrents_set_category(category='awesome cat 1', torrent_hashes=torrent_hash)
        assert torrent.info.category == 'awesome cat 1'
        client.torrents_setCategory(category='awesome cat 2', torrent_hashes=torrent_hash)
        assert torrent.info.category == 'awesome cat 2'
    finally:
        client.torrents_remove_categories(categories=('awesome cat 1', 'awesome cat 2'))


def test_torrents_set_auto_management(client, torrent_hash, torrent):
    current_setting = torrent.info.auto_tmm
    client.torrents_set_auto_management(enable=(not current_setting), torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert torrent.info.auto_tmm == (not current_setting)
            break
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)

    current_setting = torrent.info.auto_tmm
    client.torrents_setAutoManagement(enable=(not current_setting), torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert torrent.info.auto_tmm == (not current_setting)
            break
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)


def test_toggle_sequential_download(client, torrent_hash, torrent):
    current_setting = torrent.info.seq_dl
    client.torrents_toggle_sequential_download(torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert torrent.info.seq_dl == (not current_setting)
            break
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)

    current_setting = torrent.info.seq_dl
    client.torrents_toggleSequentialDownload(torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert torrent.info.seq_dl == (not current_setting)
            break
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)


def test_toggle_first_last_piece_priority(client, torrent_hash, torrent):
    current_setting = torrent.info.f_l_piece_prio
    client.torrents_toggle_first_last_piece_priority(torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert torrent.info.f_l_piece_prio == (not current_setting)
            break
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)

    current_setting = torrent.info.f_l_piece_prio
    client.torrents_toggleFirstLastPiecePrio(torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert torrent.info.f_l_piece_prio == (not current_setting)
            break
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)


def test_set_force_start(client, torrent_hash, torrent):
    current_setting = torrent.info.force_start
    client.torrents_set_force_start(enable=(not current_setting), torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert torrent.info.force_start == (not current_setting)
            break
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)

    current_setting = torrent.info.force_start
    client.torrents_setForceStart(enable=(not current_setting), torrent_hashes=torrent_hash)
    for i in range(check_limit):
        try:
            assert torrent.info.force_start == (not current_setting)
            break
        except:
            if i >= check_limit - 1:
                raise
            sleep(1)


def test_set_super_seeding(client, torrent_hash, torrent):
    pass
