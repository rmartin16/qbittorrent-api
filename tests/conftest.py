import os
from sys import path as sys_path
from time import sleep

import pytest
import six

from qbittorrentapi import APIConnectionError
from qbittorrentapi import Client
from qbittorrentapi._version_support import (
    APP_VERSION_2_API_VERSION_MAP as api_version_map,
)

qbt_version = "v" + os.environ.get("QBT_VER", "")
IS_QBT_DEV = bool(os.environ.get("IS_QBT_DEV", False))

BASE_PATH = sys_path[0]
_check_limit = 10

_orig_torrent_url = (
    "https://releases.ubuntu.com/21.04/ubuntu-21.04-desktop-amd64.iso.torrent"
)
_orig_torrent_hash = "64a980abe6e448226bb930ba061592e44c3781a1"

with open(
    os.path.join(
        BASE_PATH, "tests", "resources", "kubuntu-22.04.1-desktop-amd64.iso.torrent"
    ),
    mode="rb",
) as f:
    torrent1_file = f.read()
torrent1_url = "https://cdimage.ubuntu.com/kubuntu/releases/22.04/release/kubuntu-22.04.1-desktop-amd64.iso.torrent"
torrent1_filename = torrent1_url.split("/")[-1]
torrent1_hash = "8e905ea8e925c3a7fda9eb2e964a0e5c97cc2ce0"

torrent2_url = "https://cdimage.ubuntu.com/xubuntu/releases/22.04/release/xubuntu-22.04.1-desktop-amd64.iso.torrent"
torrent2_filename = torrent2_url.split("/")[-1]
torrent2_hash = "b813f485c0e6d17f6877c8d6942b3bdc7c227176"

with open(
    os.path.join(BASE_PATH, "tests", "resources", "root_folder.torrent"), mode="rb"
) as f:
    root_folder_torrent_file = f.read()
root_folder_torrent_hash = "a14553bd936a6d496402082454a70ea7a9521adc"


def get_func(client, func_str):
    func = client
    for attr in func_str.split("."):
        func = getattr(func, attr)
    return func


def mkpath(user_path):
    if user_path:
        return os.path.abspath(os.path.realpath(os.path.expanduser(user_path)))
    return ""


def check(
    check_func, value, reverse=False, negate=False, any=False, check_limit=_check_limit
):
    """
    Compare the return value of an arbitrary function to expected value with
    retries. Since some requests take some time to take effect in qBittorrent,
    the retries every second for 10 seconds.

    :param check_func: callable to generate values to check
    :param value: str, int, or iterator of values to look for
    :param reverse: False: look for check_func return in value; True: look for value in check_func return
    :param negate: False: value must be found; True: value must not be found
    :param check_limit: seconds to spend checking
    :param any: False: all values must be (not) found; True: any value must be (not) found
    """

    def _do_check(_check_func_val, _v, _negate, _reverse):
        if _negate:
            if _reverse:
                assert _v not in _check_func_val
            else:
                assert _check_func_val not in (_v,)
        else:
            if _reverse:
                assert _v in _check_func_val
            else:
                assert _check_func_val in (_v,)

    if isinstance(value, (six.string_types, int)):
        value = (value,)

    try:
        for i in range(_check_limit):
            try:
                exp = None
                for v in value:
                    # clear any previous exceptions if any=True
                    exp = None if any else exp

                    try:
                        # get val here so pytest includes value in failures
                        check_val = check_func()
                        _do_check(check_val, v, negate, reverse)
                    except AssertionError as e:
                        exp = e

                    # fail the test on first failure if any=False
                    if not any and exp:
                        break
                    # this value passed so test succeeded if any=True
                    if any and not exp:
                        break

                # raise caught inner exception for handling
                if exp:
                    raise exp

                # test succeeded!!!!
                break

            except AssertionError:
                if i >= check_limit - 1:
                    raise
                sleep(1)
    except APIConnectionError:
        raise AssertionError("qBittrorrent crashed...")


def retry(retries=3):
    """decorator to retry a function if there's an exception."""

    def inner(f):
        def wrapper(*args, **kwargs):
            for retry_count in range(retries):
                try:
                    return f(*args, **kwargs)
                except Exception:
                    if retry_count >= (retries - 1):
                        raise

        return wrapper

    return inner


@pytest.fixture(autouse=True)
def abort_if_qbittorrent_crashes(client):
    """Abort tests if qbittorrent disappears during testing."""
    try:
        _ = client.app.version
        yield
    except APIConnectionError:
        pytest.exit("qBittorrent crashed :(")


@pytest.fixture(scope="session")
def client():
    """qBittorrent Client for testing session."""
    try:
        client = Client(
            RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
            VERBOSE_RESPONSE_LOGGING=True,
            VERIFY_WEBUI_CERTIFICATE=False,
        )
        client.auth_log_in()
        # add orig_torrent to qBittorrent
        client.torrents_add(urls=_orig_torrent_url, upload_limit=10, download_limit=10)
        # enable RSS fetching
        client.app.preferences = dict(rss_processing_enabled=True)
        return client
    except APIConnectionError as e:
        pytest.exit("qBittorrent was not running when tests started: %s" % repr(e))


@pytest.fixture(scope="session")
def orig_torrent_hash():
    """Torrent hash for the Xubuntu torrent loaded for testing."""
    return _orig_torrent_hash


@pytest.fixture(scope="function")
def orig_torrent(client, orig_torrent_hash):
    """Torrent to remain in qBittorrent for entirety of session."""
    try:
        check(
            lambda: len(
                [t for t in client.torrents_info() if t.hash == orig_torrent_hash]
            ),
            value=1,
        )
        return [t for t in client.torrents_info() if t.hash == orig_torrent_hash][0]
    except APIConnectionError:
        pytest.exit('Failed to find "orig_torrent"')


@pytest.fixture
def new_torrent(client):
    """Torrent that is added on demand to qBittorrent and then removed."""
    yield next(new_torrent_standalone(client))


def new_torrent_standalone(client, torrent_hash=torrent1_hash, **kwargs):
    def add_test_torrent(client):
        for attempt in range(_check_limit):
            if kwargs:
                client.torrents.add(**kwargs)
            else:
                client.torrents.add(
                    torrent_files=torrent1_file,
                    save_path=os.path.expanduser("~/test_download/"),
                    category="test_category",
                    is_paused=True,
                    upload_limit=1024,
                    download_limit=2048,
                    is_sequential_download=True,
                    is_first_last_piece_priority=True,
                )
            try:
                # not all versions of torrents_info() support passing a hash
                return list(
                    filter(lambda t: t.hash == torrent_hash, client.torrents_info())
                )[0]
            except Exception:
                if attempt >= _check_limit - 1:
                    raise
                sleep(1)

    @retry
    def delete_test_torrent(torrent):
        torrent.delete(delete_files=True)
        check(
            lambda: [t.hash for t in torrent._client.torrents_info()],
            torrent.hash,
            reverse=True,
            negate=True,
        )

    try:
        torrent = add_test_torrent(client)
    except APIConnectionError:
        yield None  # if qBittorrent crashed, it'll get caught in abort fixture
    else:
        yield torrent
        try:
            delete_test_torrent(torrent)
        except APIConnectionError:
            pass  # if qBittorrent crashed, it'll get caught in abort fixture


@pytest.fixture(scope="session")
def app_version(client):
    """qBittorrent App Version being used for testing."""
    if qbt_version != "v":
        return qbt_version
    return client.app_version()


@pytest.fixture(scope="session")
def api_version(client):
    """qBittorrent App API Version being used for testing."""
    try:
        return api_version_map[qbt_version]
    except KeyError as exp:
        if IS_QBT_DEV:
            return client.app.web_api_version
        raise exp


@pytest.fixture(scope="function")
def rss_feed(client):
    def delete_feed():
        try:
            client.rss_remove_item(item_path=name)
            check(lambda: client.rss_items(), name, reverse=True, negate=True)
        except Exception:
            pass

    name = "YTS1080p"
    url = "https://yts.mx/rss/"
    # refreshing the feed is finicky...so try several times if necessary
    done = False
    for i in range(30):
        delete_feed()
        client.rss.add_feed(url=url, item_path=name)
        # wait until the rss feed exists and is refreshed
        check(lambda: client.rss_items(), name, reverse=True)
        # wait until feed is refreshed
        for j in range(10):
            if client.rss.items.with_data[name]["articles"]:
                done = True
                yield name
                delete_feed()
                break
            sleep(0.5)
        if done:
            break
    else:
        raise Exception("RSS Feed '%s' did not refresh..." % name)


def pytest_sessionfinish(session, exitstatus):
    try:
        if os.environ.get("CI") != "true":
            client = Client()
            # remove all torrents
            for torrent in client.torrents_info():
                client.torrents_delete(delete_files=True, torrent_hashes=torrent.hash)
    except Exception:
        pass
