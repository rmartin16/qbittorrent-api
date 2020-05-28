import pytest

from qbittorrentapi.sync import SyncMainDataDictionary, SyncTorrentPeersDictionary


@pytest.mark.parametrize('rid', (None, 0, 1, 100000))
def test_maindata1(client, rid):
    assert isinstance(client.sync_maindata(rid=rid), SyncMainDataDictionary)


@pytest.mark.parametrize('rid', (None, 0, 1, 100000))
def test_maindata2(client, rid):
    assert isinstance(client.sync.maindata(rid=rid), SyncMainDataDictionary)
    assert isinstance(client.sync.maindata.delta(), SyncMainDataDictionary)
    assert isinstance(client.sync.maindata.delta(), SyncMainDataDictionary)


def test_maindata3(client):
    _ = client.sync.maindata()
    assert client.sync.maindata._rid != 0
    client.sync.maindata.reset_rid()
    assert client.sync.maindata._rid == 0


'''@pytest.mark.parametrize('rid', (None, 0, 1, 100000))
def test_torrent_peers1(client, rid):
    assert isinstance(client.sync_torrent_peers(rid=rid), SyncTorrentPeersDictionary)


@pytest.mark.parametrize('rid', (None, 0, 1, 100000))
def test_torrent_peers2(client, rid):
    assert isinstance(client.sync.maindata(rid=rid), SyncTorrentPeersDictionary)
    assert isinstance(client.sync.maindata.delta(), SyncTorrentPeersDictionary)
    assert isinstance(client.sync.maindata.delta(), SyncTorrentPeersDictionary)


def test_torrent_peers3(client):
    _ = client.sync.maindata()
    assert client.sync.maindata._rid != 0
    client.sync.maindata.reset_rid()
    assert client.sync.maindata._rid == 0'''
