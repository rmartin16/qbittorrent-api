import sys

import pytest

from qbittorrentapi import APINames, InvalidRequest400Error
from qbittorrentapi.clientdata import ClientDataDictionary


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    namespace = APINames.ClientData
    all_dotted_methods = set(dir(getattr(client, namespace)))

    for meth in [meth for meth in dir(client) if meth.startswith(f"{namespace}_")]:
        assert meth.removeprefix(f"{namespace}_") in all_dotted_methods


@pytest.mark.skipif_before_api_version("2.13.1")
@pytest.mark.parametrize("store_func", ["clientdata_store", "clientdata.store"])
@pytest.mark.parametrize("load_func", ["clientdata_load", "clientdata.load"])
def test_clientdata_round_trip(client, store_func, load_func):
    client.func(store_func)(data={"qbittorrent-api-test": {"key": "value"}})

    stored = client.func(load_func)()
    assert isinstance(stored, ClientDataDictionary)
    assert stored["qbittorrent-api-test"]["key"] == "value"

    subset = client.func(load_func)(keys=["qbittorrent-api-test"])
    assert isinstance(subset, ClientDataDictionary)
    assert subset["qbittorrent-api-test"]["key"] == "value"


@pytest.mark.skipif_before_api_version("2.13.1")
def test_clientdata_load_unknown_key(client):
    assert "no-such-key" not in client.clientdata_load(keys=["no-such-key"])


@pytest.mark.skipif_before_api_version("2.13.1")
def test_clientdata_load_bad_keys(client):
    # `keys` must be a JSON array of strings
    with pytest.raises(InvalidRequest400Error):
        client.clientdata_load(keys=[{"not": "a string"}])


@pytest.mark.skipif_after_api_version("2.13.1")
@pytest.mark.parametrize("load_func", ["clientdata_load", "clientdata.load"])
def test_clientdata_not_implemented(client, load_func):
    with pytest.raises(NotImplementedError):
        client.func(load_func)()
