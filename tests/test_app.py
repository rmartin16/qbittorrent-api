import os

import pytest

from tests.conftest import is_version_less_than


def test_version(client, app_version):
    assert client.app_version() == app_version
    assert client.app.version == app_version
    assert client.application.version == app_version


def test_web_api_version(client, api_version):
    assert client.app_web_api_version() == api_version
    assert client.app.web_api_version == api_version
    assert client.application.web_api_version == api_version


def test_build_info(client, api_version):
    def run_tests():
        assert "libtorrent" in client.app_build_info()
        assert "libtorrent" in client.app.build_info

    if is_version_less_than(api_version, "2.3", lteq=False):
        with pytest.raises(NotImplementedError):
            run_tests()
    else:
        run_tests()


def test_preferences(client):
    prefs = client.app_preferences()
    assert "dht" in prefs
    assert "dht" in client.app.preferences
    dht = prefs["dht"]
    client.app.preferences = dict(dht=(not dht))
    assert dht is not client.app.preferences.dht
    client.app_set_preferences(prefs=dict(dht=dht))
    assert dht is client.app.preferences.dht


def test_default_save_path(client):
    assert os.path.isdir(client.app_default_save_path())
    assert os.path.isdir(client.app.default_save_path)
