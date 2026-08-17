from contextlib import suppress
from os import environ, path
from time import sleep

import pytest

from qbittorrentapi import (
    APIConnectionError,
    Client,
    Conflict409Error,
    HTTPError,
    TorrentDictionary,
)
from qbittorrentapi._version_support import (
    APP_VERSION_2_API_VERSION_MAP as api_version_map,
)

# Amount of time to attempt a check
CHECK_TIME = 10
# Amount of time to sleep between checks
CHECK_SLEEP = 0.25
# Webseed changes are handed to a qBittorrent thread pool that silently discards
# whatever it fails to apply, and under load it can discard a great many in a row.
# They need a much longer window than other checks, and re-sending on every retry
# only queues more work onto the pool that is already behind, so back off between
# attempts instead of hammering it.
WEBSEED_TIMEOUT = 60
WEBSEED_RESEND_EVERY = 8
# Errors that mean qBittorrent hasn't caught up yet, so the check should be retried.
# LookupError and AttributeError cover values qBittorrent hasn't populated yet, e.g.
# indexing into a list that is still empty. The last attempt raises regardless, so
# retrying these can only delay a genuine failure...never hide one.
RETRY_ERRORS = (AssertionError, AttributeError, LookupError)


def setup_environ():
    """Set up environment for testing; ensure qBittorrent is running."""
    environ.setdefault("QBITTORRENTAPI_HOST", "localhost:8080")
    environ.setdefault("QBITTORRENTAPI_USERNAME", "admin")
    environ.setdefault("QBITTORRENTAPI_PASSWORD", "adminadmin")
    try:
        environ.setdefault("QBT_VER", Client().app.version)
    except APIConnectionError as e:
        print(f"qbittorrent error: {e!r}")
        raise Exception("is qBittorrent running???")

    qbt_version = environ.get("QBT_VER", "")
    qbt_version = qbt_version if qbt_version.startswith("v") else f"v{qbt_version}"

    environ.setdefault("IS_QBT_DEV", "" if qbt_version in api_version_map else "1")
    is_qbt_dev = environ.get("IS_QBT_DEV", "false").lower() not in ["", "false"]

    return qbt_version, is_qbt_dev


def get_func(obj, method_name):
    """
    Retrieve a method from an object.

    For example, ``torrents_info`` or ``torrents.info``.
    """
    for attr in method_name.split("."):
        obj = getattr(obj, attr)
    return obj


def mkpath(*user_path):
    """Create the fully qualified path to an iterable of directories and/or file."""
    if any(user_path):
        return path.abspath(
            path.realpath(path.expanduser(path.join(*map(str, user_path))))
        )
    return ""


def retry(retries=3):
    """Decorator to retry a function if there's an exception."""

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


def get_torrent(client, torrent_hash) -> TorrentDictionary:
    """Retrieve a torrent from qBittorrent."""
    try:
        # not all versions of torrents_info() support passing a hash
        return [t for t in client.torrents_info() if t.hash == torrent_hash][0]
    except Exception:
        pytest.exit(f"Failed to find torrent for {torrent_hash}")


@retry(200)
def add_torrent(client, torrent_url, torrent_hash):
    with suppress(Conflict409Error):
        # qBittorrent >= 5.2 returns 409 when adding a torrent that is already
        # present (e.g. it was added on a previous retry iteration but hasn't
        # shown up in torrents_info() yet). That is the state we want, so fall
        # through and look for it below.
        client.torrents_add(urls=torrent_url, upload_limit=10, download_limit=10)
    if torrent_hash not in [t.hash for t in client.torrents_info()]:
        sleep(0.1)
        raise Exception("didn't find added torrent")


def check(
    check_func,
    value,
    reverse=False,
    negate=False,
    any=False,
    check_time=None,
    action=None,
    action_every=1,
):
    """
    Compare the return value of an arbitrary function to expected value with retries.
    Since some requests take some time to take effect in qBittorrent, the value is
    re-checked every ``CHECK_SLEEP`` seconds for ``CHECK_TIME`` seconds.

    :param check_func: callable to generate values to check
    :param value: str, int, or iterator of values to look for
    :param reverse: False: look for check_func return in value; True: look for value in
        check_func return
    :param negate: False: value must be found; True: value must not be found
    :param check_time: maximum number of seconds to spend checking
    :param any: False: all values must be (not) found; True: any value must be (not)
        found
    :param action: callable to re-send the request being checked before each retry;
        qBittorrent occasionally never applies a request (e.g. it decides its own,
        potentially stale, cached state already matches), and re-sending is the only
        way to recover. Only use for requests that are safe to send more than once.
    :param action_every: number of retries between each ``action`` call; raise it for
        requests qBittorrent handles on a worker thread, where re-sending on every
        retry just queues more work onto a pool that is already behind
    """

    # assertions are not rewritten by pytest in this module, so each
    # assertion needs to report the values that caused it to fail
    def _do_check(_check_func_val, _v, _negate, _reverse):
        if _negate:
            if _reverse:
                assert _v not in _check_func_val, f"found {_v!r} in {_check_func_val!r}"
            else:
                assert _check_func_val not in (_v,), f"{_check_func_val!r} is {_v!r}"
        else:
            if _reverse:
                assert _v in _check_func_val, f"{_v!r} not in {_check_func_val!r}"
            else:
                assert _check_func_val in (_v,), f"{_check_func_val!r} is not {_v!r}"

    if isinstance(value, (str, int)):
        value = (value,)

    check_limit = int((check_time or CHECK_TIME) / CHECK_SLEEP)

    try:
        for i in range(check_limit):
            try:
                exp = None
                for val in value:
                    # clear any previous exceptions if any=True
                    exp = None if any else exp

                    try:
                        # get val here so pytest includes value in failures
                        check_val = check_func()
                        _do_check(check_val, val, negate, reverse)
                    except RETRY_ERRORS as e:
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
                return

            except RETRY_ERRORS:
                # let the last failure fail the test so its details are reported
                if i >= check_limit - 1:
                    raise
                sleep(CHECK_SLEEP)
                if action is not None and (i + 1) % action_every == 0:
                    action()
    except HTTPError:
        # every HTTP error subclasses APIConnectionError, so let anything
        # qBittorrent actually responded with be reported as itself
        raise
    except APIConnectionError as e:
        raise AssertionError(f"qBittorrent is unreachable: {e!r}") from e


class _Attempt:
    """One try inside an :func:`eventually` loop."""

    def __init__(self, is_last):
        self.is_last = is_last
        self.failed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            return False
        if issubclass(exc_type, APIConnectionError) and not issubclass(
            exc_type, HTTPError
        ):
            raise AssertionError(f"qBittorrent is unreachable: {exc!r}") from exc
        if issubclass(exc_type, RETRY_ERRORS) and not self.is_last:
            self.failed = True
            return True  # swallow it and let the loop try again
        return False


def eventually(timeout=None, resend=None, resend_every=1):
    """
    Retry the assertions inside the loop until they pass or time out.

    qBittorrent applies many changes asynchronously, so an assertion made
    immediately after a request is liable to run before the change lands. Wrap it
    instead::

        for attempt in eventually():
            with attempt:
                assert torrent.info.category == "test_category"

    The assertions stay in the test module, so pytest rewrites them and reports
    the values that failed.

    :param timeout: seconds to keep retrying for
    :param resend: callable re-sending the request being waited on, for the
        requests qBittorrent silently drops. Only for requests that are safe to
        send more than once.
    :param resend_every: attempts between each ``resend`` call; raise it for
        requests handled on a worker thread, where re-sending constantly only
        queues more work onto a pool that is already behind
    """
    limit = int((timeout or CHECK_TIME) / CHECK_SLEEP)
    for i in range(limit):
        attempt = _Attempt(is_last=i == limit - 1)
        yield attempt
        if not attempt.failed:
            return
        sleep(CHECK_SLEEP)
        if resend is not None and (i + 1) % resend_every == 0:
            resend()
