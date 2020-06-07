from os import environ

import pytest

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
    return client.torrents_info(torrent_hashes=torrent_hash)[0]


@pytest.fixture(scope='session')
def app_version():
    return qbt_version


@pytest.fixture(scope='session')
def api_version():
    return api_version_map[qbt_version]


def pytest_sessionfinish(session, exitstatus):
    client = Client()
    client.torrents_delete(delete_files=True, torrent_hashes='c6df3faa31ff9a73a3687bf5522b2035e561ac41')
