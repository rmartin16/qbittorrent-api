import glob
import os
from contextlib import contextmanager, suppress
from functools import partial
from os import environ, path
from pathlib import Path
from sys import path as sys_path
from time import sleep
from unittest.mock import MagicMock

import pytest

from qbittorrentapi import APIConnectionError, Client, Conflict409Error
from qbittorrentapi._version_support import (
    APP_VERSION_2_API_VERSION_MAP as api_version_map,
)
from qbittorrentapi._version_support import v
from tests.utils import (
    CHECK_SLEEP,
    add_torrent,
    eventually,
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

TORRENT1_FILENAME = "kubuntu-22.04.4-desktop-amd64.iso.torrent"
TORRENT1_URL = f"https://github.com/rmartin16/qbittorrent-api/raw/main/tests/_resources/{TORRENT1_FILENAME}"
TORRENT1_HASH = "27a92b32757893ac9eb898e32c952636a3cc7b24"
TORRENT1_FILE = Path(RESOURCES_PATH, TORRENT1_FILENAME).read_bytes()

TORRENT2_FILENAME = "xubuntu-22.04.4-desktop-amd64.iso.torrent"
TORRENT2_URL = f"https://github.com/rmartin16/qbittorrent-api/raw/main/tests/_resources/{TORRENT2_FILENAME}"
TORRENT2_HASH = "c7d77fc3ecb68344b59ada11a0508dd6d08f2dfd"

ROOT_FOLDER_TORRENT_FILENAME = "root_folder.torrent"
ROOT_FOLDER_TORRENT_HASH = "a14553bd936a6d496402082454a70ea7a9521adc"
ROOT_FOLDER_TORRENT_FILE = Path(RESOURCES_PATH, ROOT_FOLDER_TORRENT_FILENAME).read_bytes()  # noqa: E501
# fmt: on


@pytest.fixture(autouse=True)
def abort_if_qbittorrent_crashes(request):
    """Abort tests if qbittorrent seemingly disappears during testing."""
    if "offline" in request.keywords:
        # the test never talks to qBittorrent, so there is nothing to watch for
        return

    client = request.getfixturevalue("client")
    # a single failed request isn't proof qBittorrent is gone; it may just be busy
    # enough to stall its event loop. since this aborts the entire test session,
    # give it a chance to respond before giving up.
    for attempt in range(5):
        try:
            client.app_version()
        except APIConnectionError as e:
            print(f"qbittorrent unreachable (attempt {attempt + 1}): {e!r}")
            sleep(2)
        else:
            return
    pytest.exit("qBittorrent crashed :(")


@pytest.fixture(autouse=True)
def skip_if_not_implemented(request):
    """Skips test if `skipif_before_api_version` marker specifies min API version."""
    # the marker is checked before the version is looked up so that tests without
    # one never pull in the live client just to be told they are not skipped
    marker = request.node.get_closest_marker("skipif_before_api_version")
    if marker is None:
        return

    api_version = request.getfixturevalue("api_version")
    if v(api_version) < v(marker.args[0]):
        pytest.skip(f"testing {v(api_version)}; needs {marker.args[0]} or later")


@pytest.fixture(autouse=True)
def skip_if_implemented(request):
    """Skips test if `skipif_after_api_version` marker specifies max API version."""
    marker = request.node.get_closest_marker("skipif_after_api_version")
    if marker is None:
        return

    api_version = request.getfixturevalue("api_version")
    if v(api_version) >= v(marker.args[0]):
        pytest.skip(f"testing {v(api_version)}; needs before {marker.args[0]}")


@pytest.fixture(scope="session")
def client():
    """qBittorrent Client for testing session."""
    client = Client(
        # pin the scheme for this client. qBittorrent is always serving HTTP for
        # testing, but a transient connection failure can otherwise cause scheme
        # detection to permanently switch this client to HTTPS...which then fails
        # every subsequent request for the rest of the session.
        host=f"http://{environ['QBITTORRENTAPI_HOST']}",
        FORCE_SCHEME_FROM_HOST=True,
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


@pytest.fixture(scope="session")
def _orig_torrent(client):
    """Torrent that remains in qBittorrent for the entirety of the session."""
    torrent = get_torrent(client, torrent_hash=ORIG_TORRENT_HASH)
    torrent.func = staticmethod(partial(get_func, torrent))
    return torrent


@pytest.fixture
def orig_torrent(_orig_torrent):
    """Session-long torrent, re-synced so each test sees current values."""
    _orig_torrent.sync_local()
    return _orig_torrent


def wait_until_torrent_is_loaded(torrent):
    """
    Wait for qBittorrent to finish loading a newly added torrent.

    Requests for a torrent qBittorrent is still loading are liable to be discarded
    without any indication to the caller...for instance, adding a webseed is done in
    a worker thread that silently swallows any exception it encounters.
    """
    for attempt in eventually(timeout=30):
        with attempt:
            assert torrent.info.state not in (
                "checkingResumeData",
                "checkingDL",
                "checkingUP",
                "allocating",
                "metaDL",
            )


@contextmanager
def new_torrent_standalone(client, torrent_hash=TORRENT1_HASH, tmp_path=None, **kwargs):
    def add_test_torrent(torrent_hash_, **kw):
        check_limit = int(10 / CHECK_SLEEP)
        for attempt in range(check_limit):
            try:
                if kw:
                    client.torrents.add(**kw)
                elif tmp_path:
                    client.torrents.add(
                        torrent_files=TORRENT1_FILE,
                        save_path=mkpath(tmp_path, "test_dow2nload"),
                        category="test_category",
                        is_paused=True,
                        upload_limit=1024,
                        download_limit=2048,
                        is_sequential_download=True,
                        is_first_last_piece_priority=True,
                    )
                else:
                    raise Exception("invalid params")
            except Conflict409Error:
                # qBittorrent >= 5.2 returns 409 when adding a torrent that is
                # already present (e.g. it was added on a previous retry
                # iteration but hasn't shown up in torrents_info() yet). That is
                # the state we want, so fall through and locate it below.
                pass
            try:
                torrent = get_torrent(client, torrent_hash_)
            except Exception:
                if attempt >= check_limit - 1:
                    raise
                sleep(CHECK_SLEEP)
            else:
                torrent.func = staticmethod(partial(get_func, torrent))
                wait_until_torrent_is_loaded(torrent)
                return torrent

    @retry()
    def delete_test_torrent(client_, torrent_hash_):
        client_.torrents_delete(torrent_hashes=torrent_hash_, delete_files=True)
        # adding the torrent creates this category, and deleting the torrent
        # leaves it behind
        with suppress(Exception):
            client_.torrents_remove_categories(categories="test_category")
        for attempt in eventually():
            with attempt:
                assert torrent_hash_ not in [t.hash for t in client_.torrents_info()]

    try:
        try:
            torrent = add_test_torrent(torrent_hash, **kwargs)
        except Exception:
            # only adding the torrent is retried. yielding inside this handler
            # instead would yield a second time for a failure raised by the test
            # itself, and the RuntimeError that causes hides the real failure.
            delete_test_torrent(client, torrent_hash)
            sleep(1)
            torrent = add_test_torrent(torrent_hash, **kwargs)
        yield torrent
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


def _state_snapshot(client):
    """
    What qBittorrent is currently holding that a test could have left behind.

    Each piece is optional: the endpoints arrived in different Web API versions,
    and the client raises NotImplementedError for the ones this qBittorrent is
    too old to have.
    """
    snapshot = {}
    for name, read in (
        ("torrents", lambda: {t.hash for t in client.torrents_info()}),
        ("categories", lambda: set(client.torrents_categories())),
        ("tags", lambda: set(client.torrents_tags())),
        ("rss", lambda: set(client.rss_items())),
        ("preferences", lambda: dict(client.app.preferences)),
    ):
        try:
            snapshot[name] = read()
        except Exception:
            snapshot[name] = None
    return snapshot


@pytest.fixture(autouse=True)
def no_state_left_behind(request, client):
    """
    Fail a test that leaves torrents, categories, tags or RSS items behind, or
    that changes a preference without putting it back.

    Tests share one qBittorrent, so anything left over is inherited by whatever
    runs next. That is how an unlucky ordering turns into failures that look
    like real bugs somewhere else entirely. Mark a test ``no_sandbox`` if
    altering qBittorrent is the point of it.
    """
    if "offline" in request.keywords or "no_sandbox" in request.keywords:
        yield
        return

    before = _state_snapshot(client)
    yield
    after = _state_snapshot(client)

    leaked = {}
    for name, was in before.items():
        now = after.get(name)
        if was is None or now is None:
            continue
        if name == "preferences":
            changed = [
                key for key, value in was.items() if now.get(key, value) != value
            ]
            if changed:
                leaked[name] = sorted(changed)
        elif added := now - was:
            leaked[name] = sorted(added)
    assert not leaked, (
        f"test left state behind in qBittorrent: {leaked}. Clean up in a "
        f"finally block, or mark the test no_sandbox if that is the point of it."
    )


def pytest_sessionfinish(session, exitstatus):
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
