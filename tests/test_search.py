import sys

import pytest

from qbittorrentapi import APINames, NotFound404Error
from qbittorrentapi._version_support import v
from qbittorrentapi.search import (
    SearchCategoriesList,
    SearchJobDictionary,
    SearchPluginsList,
    SearchResultsDictionary,
    SearchStatusesList,
)
from tests.conftest import TORRENT2_HASH, TORRENT2_URL
from tests.utils import eventually, retry

PLUGIN_NAME = "therarbg"
PLUGIN_URL = "https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/refs/heads/main/therarbg.py"


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    namespace = APINames.Search
    all_dotted_methods = set(dir(getattr(client, namespace)))

    for meth in [meth for meth in dir(client) if meth.startswith(f"{namespace}_")]:
        assert meth.removeprefix(f"{namespace}_") in all_dotted_methods


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.parametrize(
    "update_func", ["search_update_plugins", "search.update_plugins"]
)
def test_update_plugins(client, update_func, app_version):
    if v(app_version) <= v("v5.0.5"):
        pytest.xfail("older qbittorrent requests are rejected now")

    @retry()
    def do_test():
        client.func(update_func)()
        for attempt in eventually():
            with attempt:
                assert any(
                    entry.message.startswith("Updating plugin ")
                    or entry.message == "All plugins are already up to date."
                    or entry.message.endswith(
                        "content was not found at the server (404)"
                    )
                    for entry in reversed(client.log.main())
                )

    do_test()


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.parametrize(
    "search_func, enable_func",
    (
        ["search_plugins", "search_enable_plugin"],
        ["search.plugins", "search.enable_plugin"],
    ),
)
def test_enable_plugin(client, search_func, enable_func):
    def get_plugins():
        try:
            return client.func(search_func)()
        except TypeError:
            return client.func(search_func)

    @retry()
    def enable_plugin():
        assert isinstance(get_plugins(), SearchPluginsList)
        client.func(enable_func)(
            plugins=(p["name"] for p in get_plugins()), enable=False
        )
        for attempt in eventually():
            with attempt:
                assert True not in [p["enabled"] for p in get_plugins()]
        client.func(enable_func)(
            plugins=(p["name"] for p in get_plugins()), enable=True
        )
        for attempt in eventually():
            with attempt:
                assert False not in [p["enabled"] for p in get_plugins()]

    enable_plugin()


@pytest.mark.skipif_before_api_version("2.1.1")
def test_plugins_slice(client):
    assert isinstance(client.search_plugins()[1:2], SearchPluginsList)


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.parametrize(
    "install_func, uninstall_func",
    (
        ["search_install_plugin", "search_uninstall_plugin"],
        ["search.install_plugin", "search.uninstall_plugin"],
    ),
)
def test_install_uninstall_plugin(client, install_func, uninstall_func):
    @retry()
    def install_plugin():
        client.func(install_func)(sources=PLUGIN_URL)
        for attempt in eventually():
            with attempt:
                assert PLUGIN_NAME in [p.name for p in client.search.plugins]

    @retry()
    def uninstall_plugin():
        client.func(uninstall_func)(names=PLUGIN_NAME)
        for attempt in eventually():
            with attempt:
                assert PLUGIN_NAME not in [p.name for p in client.search.plugins]

    install_plugin()
    uninstall_plugin()


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.skipif_after_api_version("2.6")
@pytest.mark.parametrize("categories_func", ["search_categories", "search.categories"])
def test_categories(client, categories_func):
    assert isinstance(client.func(categories_func)(), SearchCategoriesList)
    assert isinstance(client.func(categories_func)()[1:2], SearchCategoriesList)
    for attempt in eventually():
        with attempt:
            assert "All categories" in client.func(categories_func)()


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.parametrize(
    "start_func, status_func, results_func, stop_func, delete_stop",
    [
        (
            "search_start",
            "search_status",
            "search_results",
            "search_stop",
            "search_delete",
        ),
        (
            "search.start",
            "search.status",
            "search.results",
            "search.stop",
            "search.delete",
        ),
    ],
)
def test_search(client, start_func, status_func, results_func, stop_func, delete_stop):
    @retry()
    def do_test():
        job = client.func(start_func)(
            pattern="Ubuntu", plugins="enabled", category="all"
        )

        statuses = client.func(status_func)(search_id=job["id"])
        assert statuses[0]["status"] == "Running"
        assert isinstance(job, SearchJobDictionary)
        assert isinstance(statuses, SearchStatusesList)

        results = client.func(results_func)(search_id=job["id"], limit=1)
        assert isinstance(results, SearchResultsDictionary)
        results = job.results()
        assert isinstance(results, SearchResultsDictionary)

        client.func(stop_func)(search_id=job["id"])
        for attempt in eventually():
            with attempt:
                assert (
                    client.func(status_func)(search_id=job["id"])[0]["status"]
                    == "Stopped"
                )

        client.func(delete_stop)(search_id=job["id"])
        statuses = client.func(status_func)()
        assert not statuses

    do_test()


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.parametrize("status_func", ["search_status", "search.status"])
def test_statuses_slice(client, status_func):
    assert isinstance(client.func(status_func)()[1:2], SearchStatusesList)


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.parametrize(
    "stop_func, start_func",
    [("search_stop", "search_start"), ("search.stop", "search.start")],
)
def test_stop(client, stop_func, start_func):
    job = client.func(start_func)(pattern="Ubuntu", plugins="enabled", category="all")
    for attempt in eventually():
        with attempt:
            assert client.search.status(search_id=job["id"])[0]["status"] == "Running"

    client.func(stop_func)(search_id=job.id)
    for attempt in eventually():
        with attempt:
            assert client.search.status(search_id=job["id"])[0]["status"] == "Stopped"

    job = client.func(start_func)(pattern="Ubuntu", plugins="enabled", category="all")
    for attempt in eventually():
        with attempt:
            assert client.search.status(search_id=job["id"])[0]["status"] == "Running"
    job.stop()
    for attempt in eventually():
        with attempt:
            assert client.search.status(search_id=job["id"])[0]["status"] == "Stopped"


@pytest.mark.skipif_before_api_version("2.1.1")
def test_delete(client):
    job = client.search_start(pattern="Ubuntu", plugins="enabled", category="all")
    job.delete()
    with pytest.raises(NotFound404Error):
        job.status()


@pytest.mark.skipif_before_api_version("2.11")
@pytest.mark.parametrize(
    "client_func", ["search_download_torrent", "search.download_torrent"]
)
def test_download_torrent(client, client_func, app_version):
    if v(app_version) <= v("v5.0.5"):
        pytest.xfail("older qbittorrent requests are rejected now")

    # run update to ensure plugins are loaded
    client.search.update_plugins()
    for attempt in eventually():
        with attempt:
            assert "eztv" in [p.name for p in client.search.plugins]
    try:
        client.func(client_func)(url=TORRENT2_URL, plugin="eztv")
        # qBittorrent must download the torrent file from GitHub before it
        # shows up, so allow for the internet being slow
        for attempt in eventually(timeout=60):
            with attempt:
                assert TORRENT2_HASH in [t.hash for t in client.torrents_info()]
    finally:
        client.torrents.delete(torrent_hashes=TORRENT2_HASH)
        for attempt in eventually():
            with attempt:
                assert TORRENT2_HASH not in [t.hash for t in client.torrents_info()]
