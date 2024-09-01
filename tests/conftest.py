import glob
import os
from contextlib import contextmanager, suppress
from functools import partial
from os import environ, path
from sys import path as sys_path
from time import sleep
from unittest.mock import MagicMock

import pytest

from qbittorrentapi import APIConnectionError, Client
from qbittorrentapi._version_support import (
    APP_VERSION_2_API_VERSION_MAP as api_version_map,
)
from qbittorrentapi._version_support import v
from tests.utils import (
    CHECK_SLEEP,
    add_torrent,
    check,
    get_func,
    get_torrent,
    mkpath,
    retry,
    setup_environ,
)


class staticmethod:
    """Override staticmethod since it only become callable in 3.10."""

    def __init__(self, _func):
        self.f = _func

    def __call__(self, *a, **k):
        return self.f(*a, **k)


QBT_VERSION, IS_QBT_DEV = setup_environ()

BASE_PATH = sys_path[0]
RESOURCES_PATH = path.join(BASE_PATH, "tests", "_resources")
assert BASE_PATH.split("/")[-1] == "qbittorrent-api"

# fmt: off
ORIG_TORRENT_FILENAME = "ubuntu-22.04.1-desktop-amd64.iso.torrent"
ORIG_TORRENT_URL = f"https://github.com/rmartin16/qbittorrent-api/raw/main/tests/_resources/{ORIG_TORRENT_FILENAME}"
ORIG_TORRENT_HASH = "3b245504cf5f11bbdbe1201cea6a6bf45aee1bc0"
ORIG_TORRENT = None

TORRENT1_FILENAME = "kubuntu-22.04.4-desktop-amd64.iso.torrent"
TORRENT1_URL = f"https://github.com/rmartin16/qbittorrent-api/raw/main/tests/_resources/{TORRENT1_FILENAME}"
TORRENT1_HASH = "27a92b32757893ac9eb898e32c952636a3cc7b24"
TORRENT1_FILE_HANDLE = open(path.join(RESOURCES_PATH, TORRENT1_FILENAME), mode="rb")  # noqa: SIM115
TORRENT1_FILE = TORRENT1_FILE_HANDLE.read()

TORRENT2_FILENAME = "xubuntu-22.04.4-desktop-amd64.iso.torrent"
TORRENT2_URL = f"https://github.com/rmartin16/qbittorrent-api/raw/main/tests/_resources/{TORRENT2_FILENAME}"
TORRENT2_HASH = "c7d77fc3ecb68344b59ada11a0508dd6d08f2dfd"

ROOT_FOLDER_TORRENT_FILENAME = "root_folder.torrent"
ROOT_FOLDER_TORRENT_HASH = "a14553bd936a6d496402082454a70ea7a9521adc"
ROOT_FOLDER_TORRENT_FILE_HANDLE = open(path.join(RESOURCES_PATH, ROOT_FOLDER_TORRENT_FILENAME), mode="rb")  # noqa: E501, SIM115
ROOT_FOLDER_TORRENT_FILE = ROOT_FOLDER_TORRENT_FILE_HANDLE.read()
# fmt: on


@pytest.fixture(autouse=True)
def abort_if_qbittorrent_crashes(client):
    """Abort tests if qbittorrent seemingly disappears during testing."""
    try:
        client.app_version()
    except APIConnectionError:
        pytest.exit("qBittorrent crashed :(")


@pytest.fixture(autouse=True)
def skip_if_not_implemented(request, api_version):
    """Skips test if `skipif_before_api_version` marker specifies min API version."""
    if request.node.get_closest_marker("skipif_before_api_version"):
        version = request.node.get_closest_marker("skipif_before_api_version").args[0]
        if v(api_version) < v(version):
            pytest.skip(f"testing {v(api_version)}; needs {version} or later")


@pytest.fixture(autouse=True)
def skip_if_implemented(request, api_version):
    """Skips test if `skipif_after_api_version` marker specifies max API version."""
    if request.node.get_closest_marker("skipif_after_api_version"):
        version = request.node.get_closest_marker("skipif_after_api_version").args[0]
        if v(api_version) >= v(version):
            pytest.skip(f"testing {v(api_version)}; needs before {version}")


@pytest.fixture(scope="session")
def client():
    """qBittorrent Client for testing session."""
    client = Client(
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERBOSE_RESPONSE_LOGGING=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    client.auth_log_in()
    client.app.preferences = dict(
        # enable RSS fetching
        rss_processing_enabled=True,
        # prevent banning IPs
        web_ui_max_auth_fail_count=1000,
        web_ui_ban_duration=1,
    )
    client.func = staticmethod(partial(get_func, client))
    try:
        add_torrent(client, ORIG_TORRENT_URL, ORIG_TORRENT_HASH)
    except Exception:
        pytest.exit("failed to add orig_torrent during setup")
    return client


@pytest.fixture
def client_mock(client):
    """qBittorrent Client for testing with request mocks."""
    client._get = MagicMock(wraps=client._get)
    client._get_cast = MagicMock(wraps=client._get_cast)
    client._post = MagicMock(wraps=client._post)
    client._post_cast = MagicMock(wraps=client._post_cast)
    try:
        yield client
    finally:
        client._get = client._get
        client._get_cast = client._get_cast
        client._post = client._post
        client._post_cast = client._post_cast


@pytest.fixture
def orig_torrent(client):
    """Torrent to remain in qBittorrent for entirety of session."""
    global ORIG_TORRENT
    if ORIG_TORRENT is None:
        ORIG_TORRENT = get_torrent(client, torrent_hash=ORIG_TORRENT_HASH)
        ORIG_TORRENT.func = staticmethod(partial(get_func, ORIG_TORRENT))
    ORIG_TORRENT.sync_local()  # ensure torrent is up-to-date
    return ORIG_TORRENT


@contextmanager
def new_torrent_standalone(client, torrent_hash=TORRENT1_HASH, tmp_path=None, **kwargs):
    def add_test_torrent(torrent_hash_, **kw):
        check_limit = int(10 / CHECK_SLEEP)
        for attempt in range(check_limit):
            if kw:
                client.torrents.add(**kw)
            elif tmp_path:
                client.torrents.add(
                    torrent_files=TORRENT1_FILE,
                    save_path=mkpath(tmp_path, "test_download"),
                    category="test_category",
                    is_paused=True,
                    upload_limit=1024,
                    download_limit=2048,
                    is_sequential_download=True,
                    is_first_last_piece_priority=True,
                )
            else:
                raise Exception("invalid params")
            try:
                torrent = get_torrent(client, torrent_hash_)
            except Exception:
                if attempt >= check_limit - 1:
                    raise
                sleep(CHECK_SLEEP)
            else:
                torrent.func = staticmethod(partial(get_func, torrent))
                return torrent

    @retry()
    def delete_test_torrent(client_, torrent_hash_):
        client_.torrents_delete(torrent_hashes=torrent_hash_, delete_files=True)
        check(
            lambda: [t.hash for t in client_.torrents_info()],
            torrent_hash_,
            reverse=True,
            negate=True,
        )

    try:
        yield add_test_torrent(torrent_hash, **kwargs)
    finally:
        delete_test_torrent(client, torrent_hash)


@pytest.fixture
def new_torrent(client, tmp_path):
    """Torrent that is added on demand to qBittorrent and then removed."""
    with new_torrent_standalone(client, tmp_path=tmp_path) as torrent:
        yield torrent


@pytest.fixture
def app_version(client):
    """qBittorrent Version being used for testing."""
    if IS_QBT_DEV:
        return client.app.version
    return QBT_VERSION


@pytest.fixture
def api_version(client):
    """qBittorrent Web API Version being used for testing."""
    if IS_QBT_DEV:
        return client.app.web_api_version
    return api_version_map[QBT_VERSION]


def pytest_sessionfinish(session, exitstatus):
    for fh in [TORRENT1_FILE_HANDLE, ROOT_FOLDER_TORRENT_FILE_HANDLE]:
        with suppress(Exception):
            fh.close()
    if environ.get("CI") != "true":
        client = Client()
        with suppress(Exception):
            # remove all torrents
            for torrent in client.torrents_info():
                torrent.delete(delete_files=True)
        # delete coverage files if not in CI
        for file in glob.iglob(path.join(BASE_PATH, ".coverage*")):
            os.unlink(file)
        # delete downloaded files if not in CI
        for filename in [TORRENT1_FILENAME, TORRENT2_FILENAME]:
            with suppress(Exception):
                os.unlink(mkpath("~", filename))
