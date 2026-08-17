from os import environ

import pytest

from tests.utils import eventually


@pytest.mark.skipif(environ.get("CI") != "true", reason="not in CI")
def test_shutdown(client):
    client.app.shutdown()
    with pytest.raises(AssertionError, match="qBittorrent is unreachable"):
        for attempt in eventually():
            with attempt:
                assert client.app_version() == ""
