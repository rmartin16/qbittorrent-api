import sys

import pytest

from qbittorrentapi.definitions import APINames
from qbittorrentapi.log import LogMainList, LogPeersList


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    namespace = APINames.Log
    all_dotted_methods = set(dir(getattr(client, namespace)))

    for meth in [meth for meth in dir(client) if meth.startswith(f"{namespace}_")]:
        assert meth.removeprefix(f"{namespace}_") in all_dotted_methods


@pytest.mark.parametrize("main_func", ["log_main", "log.main"])
@pytest.mark.parametrize("last_known_id", (None, 0))
def test_log_main_id(client, main_func, last_known_id):
    log_main = client.func(main_func)(last_known_id=last_known_id)
    assert isinstance(log_main, LogMainList)

    last_id = log_main[-1].id if log_main else 0
    log_main = client.func(main_func)(last_known_id=last_id)
    assert isinstance(log_main, LogMainList)
    assert not log_main or log_main[-1].id != last_id


@pytest.mark.parametrize("main_func", ["log_main", "log.main"])
def test_log_main_large_id(client, main_func):
    assert client.func(main_func)(last_known_id=99999999) == []


@pytest.mark.parametrize("main_func", ["log_main", "log.main"])
def test_log_main_slice(client, main_func):
    assert isinstance(client.func(main_func)()[1:2], LogMainList)


def test_log_main_info(client_mock):
    assert isinstance(client_mock.log.main.info(), LogMainList)
    client_mock._get_cast.assert_called_with(
        _name=APINames.Log,
        _method="main",
        params={
            "info": None,
            "normal": None,
            "warning": None,
            "critical": None,
            "last_known_id": None,
        },
        response_class=LogMainList,
    )


def test_log_main_normal(client_mock):
    assert isinstance(client_mock.log.main.normal(), LogMainList)
    client_mock._get_cast.assert_called_with(
        _name=APINames.Log,
        _method="main",
        params={
            "info": False,
            "normal": None,
            "warning": None,
            "critical": None,
            "last_known_id": None,
        },
        response_class=LogMainList,
    )


def test_log_main_warning(client_mock):
    assert isinstance(client_mock.log.main.warning(), LogMainList)
    client_mock._get_cast.assert_called_with(
        _name=APINames.Log,
        _method="main",
        params={
            "info": False,
            "normal": False,
            "warning": None,
            "critical": None,
            "last_known_id": None,
        },
        response_class=LogMainList,
    )


def test_log_main_critical(client_mock):
    assert isinstance(client_mock.log.main.critical(), LogMainList)
    client_mock._get_cast.assert_called_with(
        _name=APINames.Log,
        _method="main",
        params={
            "info": False,
            "normal": False,
            "warning": False,
            "critical": None,
            "last_known_id": None,
        },
        response_class=LogMainList,
    )


@pytest.mark.parametrize("main_func", ["log_main", "log.main"])
@pytest.mark.parametrize("include_level", (True, False, None, 1, 0))
def test_log_main_levels(client_mock, main_func, include_level):
    client_mock.func(main_func)(
        normal=include_level,
        info=include_level,
        warning=include_level,
        critical=include_level,
    )

    actual_include = None if include_level is None else bool(include_level)
    client_mock._get_cast.assert_called_with(
        _name=APINames.Log,
        _method="main",
        params={
            "normal": actual_include,
            "info": actual_include,
            "warning": actual_include,
            "critical": actual_include,
            "last_known_id": None,
        },
        response_class=LogMainList,
    )


@pytest.mark.parametrize("peers_func", ["log_peers", "log.peers"])
@pytest.mark.parametrize("last_known_id", (None, 0))
def test_log_peers_id(client, peers_func, last_known_id):
    log_peers = client.func(peers_func)(last_known_id=last_known_id)
    assert isinstance(log_peers, LogPeersList)

    last_id = log_peers[-1].id if log_peers else 0
    log_peers = client.func(peers_func)(last_known_id=last_id)
    assert isinstance(log_peers, LogPeersList)
    assert not log_peers or log_peers[-1].id != last_id


@pytest.mark.parametrize("peers_func", ["log_peers", "log.peers"])
def test_log_peers(client, peers_func):
    assert client.func(peers_func)(last_known_id=99999999) == []
    assert client.func(peers_func)(last_known_id=99999999) == []


@pytest.mark.parametrize("peers_func", ["log_peers", "log.peers"])
def test_log_peers_slice(client, peers_func):
    assert isinstance(client.func(peers_func)()[1:2], LogPeersList)
