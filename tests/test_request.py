import pytest

from qbittorrentapi import Client
from qbittorrentapi.exceptions import *
from qbittorrentapi.helpers import is_version_less_than
from qbittorrentapi.torrents import TorrentDictionary
from qbittorrentapi.torrents import TorrentInfoList


def test_log_in():
    client_good = Client()
    client_bad = Client(username='asdf', password='asdfasdf')

    assert client_good.auth_log_in() is None
    with pytest.raises(LoginFailed):
        client_bad.auth_log_in()


def test_log_out(client):
    client.auth_log_out()
    with pytest.raises(Forbidden403Error):
        # cannot call client.app.version directly since it will auto log back in
        client._get('app', 'version')
    client.auth_log_in()


def test_simple_response(client, torrent_hash):
    torrent = client.torrents.info(hashes=torrent_hash)[0]
    assert isinstance(torrent, TorrentDictionary)
    torrent = client.torrents.info(hashes=torrent_hash, SIMPLE_RESPONSE=True)[0]
    assert isinstance(torrent, dict)


def test_request_extra_params(client, torrent_hash):
    """ extra params can be sent directly to qBittorrent but there
    aren't any real use-cases so force it """
    json_response = client._post(_name='torrents', _method='info', hashes=torrent_hash).json()
    torrent = TorrentInfoList(json_response, client)[0]
    assert isinstance(torrent, TorrentDictionary)
    json_response = client._get(_name='torrents', _method='info', hashes=torrent_hash).json()
    torrent = TorrentInfoList(json_response, client)[0]
    assert isinstance(torrent, TorrentDictionary)


def test_api_connection_error():
    with pytest.raises(APIConnectionError):
        Client(host='localhost:8081').auth_log_in()


def test_request_http400(client, api_version, torrent_hash):
    with pytest.raises(MissingRequiredParameters400Error):
        client.torrents_file_priority(hash=torrent_hash)

    if is_version_less_than('4.1.5', api_version, lteq=False):
        with pytest.raises(InvalidRequest400Error):
            client.torrents_file_priority(hash=torrent_hash, file_ids='asdf', priority='asdf')


def test_http404(client):
    with pytest.raises(NotFound404Error):
        client.torrents_rename(hash='asdf', new_torrent_name='erty')


def test_http409(client, torrent_hash):
    with pytest.raises(Conflict409Error):
        client.torrents.increase_priority(hashes='asdf')


def test_http415(client):
    with pytest.raises(UnsupportedMediaType415Error):
        client.torrents.add(torrent_files='/etc/hosts')
