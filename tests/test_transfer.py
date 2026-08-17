import sys

import pytest

from qbittorrentapi import APINames
from qbittorrentapi.transfer import (
    TransferInfoDictionary,
    TransferSpeedLimitsDictionary,
)


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    namespace = APINames.Transfer
    all_dotted_methods = set(dir(getattr(client, namespace)))

    for meth in [meth for meth in dir(client) if meth.startswith(f"{namespace}_")]:
        assert meth.removeprefix(f"{namespace}_") in all_dotted_methods


def test_info(client):
    info = client.transfer_info()
    assert isinstance(info, TransferInfoDictionary)
    assert "connection_status" in info
    info = client.transfer.info
    assert isinstance(info, TransferInfoDictionary)
    assert "connection_status" in info


def test_speed_limits_mode(client):
    assert client.transfer_speed_limits_mode() in {"0", "1"}
    assert client.transfer.speed_limits_mode in {"0", "1"}

    original_mode = client.transfer.speed_limits_mode
    client.transfer_set_speed_limits_mode()
    assert client.transfer.speed_limits_mode != original_mode
    original_mode = client.transfer.speed_limits_mode
    client.transfer.set_speed_limits_mode()
    assert client.transfer.speed_limits_mode != original_mode

    original_mode = client.transfer.speed_limits_mode
    client.transfer_toggle_speed_limits_mode()
    assert client.transfer.speed_limits_mode != original_mode
    client.transfer_toggle_speed_limits_mode()
    assert client.transfer.speed_limits_mode == original_mode
    original_mode = client.transfer.speed_limits_mode
    client.transfer.toggle_speed_limits_mode()
    assert client.transfer.speed_limits_mode != original_mode
    client.transfer.toggle_speed_limits_mode()
    assert client.transfer.speed_limits_mode == original_mode

    client.transfer_set_speed_limits_mode(intended_state=True)
    assert client.transfer.speed_limits_mode != "0"
    client.transfer_setSpeedLimitsMode(intended_state=False)
    assert client.transfer.speed_limits_mode != "1"

    client.transfer_toggle_speed_limits_mode(intended_state=True)
    assert client.transfer.speed_limits_mode != "0"
    client.transfer_toggle_speed_limits_mode(intended_state=False)
    assert client.transfer.speed_limits_mode != "1"

    client.transfer.speed_limits_mode = True
    assert client.transfer.speed_limits_mode != "0"
    client.transfer.speed_limits_mode = False
    assert client.transfer.speed_limits_mode != "1"

    client.transfer.speedLimitsMode = True
    assert client.transfer.speedLimitsMode != "0"
    client.transfer.speedLimitsMode = False
    assert client.transfer.speedLimitsMode != "1"


def test_download_limit(client):
    original = client.transfer_download_limit()
    client.transfer_set_download_limit(limit=2048)
    assert client.transfer_download_limit() == 2048
    client.transfer_setDownloadLimit(limit=3072)
    assert client.transfer_downloadLimit() == 3072

    client.transfer.download_limit = 4096
    assert client.transfer.download_limit == 4096
    client.transfer.downloadLimit = 5120
    assert client.transfer.downloadLimit == 5120

    client.transfer_set_download_limit(limit=original)


def test_upload_limit(client):
    original = client.transfer_upload_limit()
    client.transfer_set_upload_limit(limit=2048)
    assert client.transfer_upload_limit() == 2048
    client.transfer_setUploadLimit(limit=3072)
    assert client.transfer_uploadLimit() == 3072

    client.transfer.upload_limit = 4096
    assert client.transfer.upload_limit == 4096
    client.transfer.uploadLimit = 5120
    assert client.transfer.uploadLimit == 5120

    client.transfer_set_upload_limit(limit=original)


@pytest.mark.skipif_before_api_version("2.3")
def test_ban_peers(client):
    original_bans = client.app.preferences.banned_IPs
    client.transfer_ban_peers(peers="1.1.1.1:8080")
    assert "1.1.1.1" in client.app.preferences.banned_IPs
    client.transfer.ban_peers(peers="1.1.1.2:8080")
    assert "1.1.1.2" in client.app.preferences.banned_IPs

    client.transfer_ban_peers(peers=["1.1.1.3:8080", "1.1.1.4:8080"])
    assert "1.1.1.3" in client.app.preferences.banned_IPs
    assert "1.1.1.4" in client.app.preferences.banned_IPs
    client.transfer.ban_peers(peers=["1.1.1.5:8080", "1.1.1.6:8080"])
    assert "1.1.1.5" in client.app.preferences.banned_IPs
    assert "1.1.1.6" in client.app.preferences.banned_IPs

    # banned_IPs is global and nothing else clears it
    client.app.set_preferences(dict(banned_IPs=original_bans))


@pytest.mark.skipif_before_api_version("2.16.0")
@pytest.mark.parametrize("speed_limits_func", ["transfer_speed_limits"])
def test_speed_limits(client, speed_limits_func):
    keys = ("up_limit", "dl_limit", "alt_up_limit", "alt_dl_limit")

    limits = client.func(speed_limits_func)()
    assert isinstance(limits, TransferSpeedLimitsDictionary)
    for key in keys:
        assert key in limits

    # the interface exposes this as a property rather than a method
    limits = client.transfer.speed_limits
    assert isinstance(limits, TransferSpeedLimitsDictionary)
    for key in keys:
        assert key in limits


@pytest.mark.skipif_before_api_version("2.16.0")
@pytest.mark.parametrize(
    "set_speed_limits_func", ["transfer_set_speed_limits", "transfer.set_speed_limits"]
)
def test_set_speed_limits(client, set_speed_limits_func):
    original = client.transfer_speed_limits()
    try:
        client.func(set_speed_limits_func)(
            upload_limit=2048000,
            download_limit=3072000,
            alt_upload_limit=1024000,
            alt_download_limit=512000,
        )
        limits = client.transfer_speed_limits()
        assert limits["up_limit"] == 2048000
        assert limits["dl_limit"] == 3072000
        assert limits["alt_up_limit"] == 1024000
        assert limits["alt_dl_limit"] == 512000
    finally:
        client.transfer_set_speed_limits(
            upload_limit=original["up_limit"],
            download_limit=original["dl_limit"],
            alt_upload_limit=original["alt_up_limit"],
            alt_download_limit=original["alt_dl_limit"],
        )
