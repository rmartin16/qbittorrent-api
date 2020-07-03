from os import environ

import pytest
from qbittorrentapi import APIConnectionError


def test_shutdown(client):
    if 'TRAVIS' in environ:
        client.app.shutdown()
        with pytest.raises(APIConnectionError):
            _ = client.app.version
