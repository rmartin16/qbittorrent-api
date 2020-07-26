from os import environ
from os import path
from time import sleep

import pytest
import six

from qbittorrentapi import Client

qbt_version = 'v' + environ['QBT_VER']

api_version_map = {
    'v4.1.0': '2.0',
    'v4.1.1': '2.0.1',
    'v4.1.2': '2.0.2',
    'v4.1.3': '2.1',
    'v4.1.4': '2.1.1',
    'v4.1.5': '2.2',
    'v4.1.6': '2.2',
    'v4.1.7': '2.2',
    'v4.1.8': '2.2',
    'v4.1.9': '2.2.1',
    'v4.1.9.1': '2.2.1',
    'v4.2.0': '2.3',
    'v4.2.1': '2.4',
    'v4.2.2': '2.4.1',
    'v4.2.3': '2.4.1',
    'v4.2.4': '2.5',
    'v4.2.5': '2.5.1',
}

check_limit = 10

url1 = 'http://releases.ubuntu.com/18.04/ubuntu-18.04.4-desktop-amd64.iso.torrent'
filename1 = url1.split('/')[-1]
hash1 = '286d2e5b4f8369855328336ac1263ae02a7a60d5'

url2 = 'https://releases.ubuntu.com/20.04/ubuntu-20.04-desktop-amd64.iso.torrent'
filename2 = url2.split('/')[-1]
hash2 = '9fc20b9e98ea98b4a35e6223041a5ef94ea27809'


def check(check_func, value, reverse=False, negate=False):
    """Compare function return to expected value with retries"""
    if isinstance(value, (six.string_types, int)):
        value = (value,)
    for i in range(check_limit):
        try:
            if reverse:
                for v in value:
                    if negate:
                        assert v not in check_func()
                    else:
                        assert v in check_func()
            else:
                if negate:
                    assert check_func() not in value
                else:
                    assert check_func() in value
            break
        except AssertionError:
            if i >= check_limit - 1:
                raise
            sleep(1)


@pytest.fixture(scope='session')
def client():
    """ qBittorrent Client for testing session """
    client = Client(RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True)
    client.auth_log_in()
    client.torrents_add(urls='https://torrent.ubuntu.com/xubuntu/releases/focal/release/desktop/xubuntu-20.04-desktop-amd64.iso.torrent',
                        upload_limit=10, download_limit=10)
    return client


@pytest.fixture(scope='session')
def torrent_hash():
    """ Torrent hash for the Xubuntu torrent loaded for testing """
    return 'c6df3faa31ff9a73a3687bf5522b2035e561ac41'


@pytest.fixture(scope='session')
def torrent(client, torrent_hash):
    check(lambda: len([t for t in client.torrents_info() if t.hash == torrent_hash]), value=1)
    return [t for t in client.torrents_info() if t.hash == torrent_hash][0]


def add_test_torrent(client):
    client.torrents.add(urls=url1,
                        save_path=path.expanduser('~/test_download/'),
                        category='test_category', is_paused=True,
                        upload_limit=1024, download_limit=2048,
                        is_sequential_download=True, is_first_last_piece_priority=True)
    for attempt in range(check_limit):
        try:
            # not all versions of torrents_info() support passing a hash
            torrent = list(filter(lambda t: t.hash == hash1, client.torrents_info()))[0]
            break
        except:
            if attempt >= check_limit - 1:
                raise
            sleep(1)
    return torrent


def delete_test_torrent(torrent):
    torrent.delete(delete_files=True)
    check(lambda: [t.hash for t in torrent._client.torrents_info()], torrent.hash, reverse=True, negate=True)


@pytest.fixture
def test_torrent(client):
    torrent = add_test_torrent(client)
    yield torrent
    delete_test_torrent(torrent)


@pytest.fixture(scope='session')
def app_version():
    return qbt_version


@pytest.fixture(scope='session')
def api_version():
    return api_version_map[qbt_version]


def pytest_sessionfinish(session, exitstatus):
    if 'TRAVIS' not in environ:
        client = Client()
        client.torrents_delete(delete_files=True, torrent_hashes='c6df3faa31ff9a73a3687bf5522b2035e561ac41')
