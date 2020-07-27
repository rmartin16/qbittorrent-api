from os import environ

import pytest
from qbittorrentapi import APIConnectionError
from tests.conftest import check


def test_shutdown(client):
    if 'TRAVIS' in environ:
        client.app.shutdown()
        with pytest.raises(APIConnectionError):
            check(check_func=client.app_version, value='')
