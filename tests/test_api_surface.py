"""
Tests for the shape of the client's API surface, derived from the catalog.

None of these talk to qBittorrent. They cover the facts that are true of the
library itself no matter which qBittorrent is running: that every spelling of an
endpoint reaches the same code, and that each endpoint's declared Web API
version range is enforced.

Those facts are currently also asserted per endpoint, over the network, by the
behavior tests. Deriving them from the catalog covers every endpoint instead of
the ones someone remembered to write a test for.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from qbittorrentapi import Client
from qbittorrentapi.torrents import TorrentDictionary
from tests.catalog import CATALOG, as_snapshot

pytestmark = pytest.mark.offline

SNAPSHOT_PATH = Path(__file__).parent / "api_surface.json"

ALIASED = [e for e in CATALOG if e.client_aliases]
INTRODUCED = [e for e in CATALOG if e.version_introduced]
REMOVED = [e for e in CATALOG if e.version_removed]
INTERFACE_ALIASED = [e for e in CATALOG if e.interface_aliases]
INTERFACE_INTRODUCED = [e for e in INTRODUCED if e.interface]
TORRENT_ALIASED = [e for e in CATALOG if e.torrent_method_aliases]
TORRENT_INTRODUCED = [e for e in INTRODUCED if e.torrent_method]


def by_primary(endpoint):
    return endpoint.primary


@pytest.fixture
def offline_client():
    """
    Client that never reaches qBittorrent.

    The version gate is checked before any request is sent, so these tests never
    need a running qBittorrent...only a client whose reported Web API version can
    be pinned.
    """
    return Client(
        host="localhost:1",
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    )


def pin_versions(client, monkeypatch, api_version, app_version):
    """
    Make the client believe which qBittorrent it is talking to.

    Both versions are pinned because a couple of endpoints gate on the
    application version rather than the Web API version: v4.3.2 and v4.3.3 both
    report Web API v2.7, so ``torrents_rename_folder`` has to tell them apart by
    application version.
    """
    monkeypatch.setattr(
        client, "app_web_api_version", MagicMock(return_value=api_version)
    )
    monkeypatch.setattr(client, "app_version", MagicMock(return_value=app_version))


def test_catalog_is_populated():
    """A catalog that silently derived nothing would make every test below vacuous."""
    assert len(CATALOG) > 100
    assert {e.namespace for e in CATALOG} >= {"app", "torrents", "rss", "transfer"}
    assert all(e.namespace for e in CATALOG)


@pytest.mark.parametrize("endpoint", ALIASED, ids=by_primary)
def test_client_aliases_are_the_same_callable(endpoint):
    """
    The camelCase spellings are assignments, not second implementations.

    ``torrents_addWebSeeds = torrents_add_webseeds`` binds one function object to
    two names, so asserting identity here covers what a live request through each
    spelling would.
    """
    primary = getattr(Client, endpoint.primary)

    for alias in endpoint.client_aliases:
        assert getattr(Client, alias) is primary, (
            f"{alias}() is not the same callable as {endpoint.primary}()"
        )


def reach_through_interface(client, endpoint):
    """
    Reach an endpoint by its interface spelling.

    Interfaces expose endpoints either as methods or as properties, and for a
    property the request is issued by the attribute access itself.
    """
    interface_name, short_name = endpoint.interface.split(".", 1)
    attribute = getattr(getattr(client, interface_name), short_name)

    if endpoint.interface_kind == "method":
        return attribute()
    return attribute


def resolve_without_invoking(interface, name):
    """
    Resolve an interface attribute without triggering it.

    Plain ``getattr`` is wrong twice over here: it builds a new bound method on
    every access, so identity never holds for methods, and it *executes*
    properties, which would issue a request.
    """
    if name in vars(interface):
        return vars(interface)[name]
    return inspect.getattr_static(type(interface), name)


@pytest.mark.parametrize("endpoint", INTERFACE_ALIASED, ids=by_primary)
def test_interface_aliases_are_the_same_object(endpoint):
    """As on the client, the interface's camelCase spellings are assignments."""
    interface_name, short_name = endpoint.interface.split(".", 1)
    interface = getattr(Client(host="localhost:1"), interface_name)
    primary = resolve_without_invoking(interface, short_name)

    for alias in endpoint.interface_aliases:
        alias_short = alias.split(".", 1)[1]
        assert resolve_without_invoking(interface, alias_short) is primary, (
            f"{alias} is not the same object as {endpoint.interface}"
        )


@pytest.mark.parametrize("endpoint", INTERFACE_INTRODUCED, ids=by_primary)
def test_interface_spelling_is_gated_before_introduction(
    offline_client, monkeypatch, endpoint
):
    """
    The gate must also fire when the endpoint is reached through its interface.

    This is the only coverage of the version gate on interface *properties* such
    as ``client.app.cookies``, where the request happens on attribute access.
    """
    pin_versions(offline_client, monkeypatch, api_version="0.0.1", app_version="v0.0.1")

    with pytest.raises(NotImplementedError, match="available starting in"):
        reach_through_interface(offline_client, endpoint)


def required_kwargs(func):
    """
    Placeholder arguments for whatever ``func`` requires.

    The version gate fires before the request is built, so the values are
    irrelevant...but a method with a required argument raises TypeError before
    reaching the gate if it is called with none.
    """
    kwargs = {}
    for name, param in inspect.signature(func).parameters.items():
        if name == "self" or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if param.default is inspect.Parameter.empty:
            kwargs[name] = None
    return kwargs


def reach_through_torrent(client, endpoint):
    """Reach an endpoint through a torrent object, as ``torrents_info()`` returns."""
    torrent = TorrentDictionary({"hash": "abc123"}, client=client)
    attribute = getattr(torrent, endpoint.torrent_method)

    if endpoint.torrent_method_kind == "method":
        return attribute(**required_kwargs(attribute))
    return attribute


@pytest.mark.parametrize("endpoint", TORRENT_ALIASED, ids=by_primary)
def test_torrent_method_aliases_are_the_same_object(endpoint):
    """The torrent object's camelCase spellings are assignments too."""
    primary = inspect.getattr_static(TorrentDictionary, endpoint.torrent_method)

    for alias in endpoint.torrent_method_aliases:
        assert inspect.getattr_static(TorrentDictionary, alias) is primary, (
            f"torrent.{alias} is not the same object "
            f"as torrent.{endpoint.torrent_method}"
        )


@pytest.mark.parametrize("endpoint", TORRENT_INTRODUCED, ids=by_primary)
def test_torrent_method_is_gated_before_introduction(
    offline_client, monkeypatch, endpoint
):
    """
    The gate must fire on torrent objects as well.

    These are a third way to reach the same endpoints, and the only thing that
    covered them was a handful of hand-written tests.
    """
    pin_versions(offline_client, monkeypatch, api_version="0.0.1", app_version="v0.0.1")

    with pytest.raises(NotImplementedError, match="available starting in"):
        reach_through_torrent(offline_client, endpoint)


@pytest.mark.parametrize("endpoint", INTRODUCED, ids=by_primary)
def test_endpoint_is_gated_before_it_was_introduced(
    offline_client, monkeypatch, endpoint
):
    pin_versions(offline_client, monkeypatch, api_version="0.0.1", app_version="v0.0.1")

    with pytest.raises(NotImplementedError, match="available starting in"):
        getattr(offline_client, endpoint.primary)()


@pytest.mark.parametrize("endpoint", REMOVED, ids=by_primary)
def test_endpoint_is_gated_after_it_was_removed(offline_client, monkeypatch, endpoint):
    pin_versions(
        offline_client, monkeypatch, api_version="99.0.0", app_version="v99.0.0"
    )

    with pytest.raises(NotImplementedError, match="was removed in"):
        getattr(offline_client, endpoint.primary)()


@pytest.mark.parametrize("endpoint", INTRODUCED, ids=by_primary)
def test_endpoint_is_not_gated_once_introduced(offline_client, monkeypatch, endpoint):
    """A gate that always fired would pass the tests above for the wrong reason."""
    if endpoint.version_removed:
        pytest.skip(f"{endpoint.primary} was removed in {endpoint.version_removed}")

    # the application version is pinned high so the handful of endpoints that
    # gate on it are not held back by it here
    pin_versions(
        offline_client,
        monkeypatch,
        api_version=endpoint.version_introduced,
        app_version="v99.0.0",
    )

    # the endpoint is supported at this version, so the request is attempted and
    # fails to connect...which is proof the version gate let it through
    with pytest.raises(Exception) as exc_info:
        getattr(offline_client, endpoint.primary)()
    assert not isinstance(exc_info.value, NotImplementedError)


def test_catalog_matches_snapshot():
    """
    Guards the declared Web API versions against accidental edits.

    Deriving the catalog from the source cannot, on its own, catch a version
    constant being changed by mistake, since the expectation would move with it.
    The snapshot is the second copy that makes such a change show up in review.

    Regenerate deliberately with::

        python -m tests.catalog > tests/api_surface.json
    """
    expected = SNAPSHOT_PATH.read_text()

    assert as_snapshot() == expected, (
        "API surface changed; if intended, regenerate with "
        "`python -m tests.catalog > tests/api_surface.json`"
    )
