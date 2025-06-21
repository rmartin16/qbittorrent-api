import sys

import pytest

from qbittorrentapi import APINames, NotFound404Error
from qbittorrentapi.search import (
    SearchCategoriesList,
    SearchJobDictionary,
    SearchPluginsList,
    SearchResultsDictionary,
    SearchStatusesList,
)
from tests.conftest import TORRENT2_HASH, TORRENT2_URL
from tests.utils import check, retry

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
def test_update_plugins(client, update_func):
    @retry()
    def do_test():
        client.func(update_func)()
        check(
            lambda: any(
                entry.message.startswith("Updating plugin ")
                or entry.message == "All plugins are already up to date."
                or entry.message.endswith("content was not found at the server (404)")
                for entry in reversed(client.log.main())
            ),
            True,
        )

    do_test()


@pytest.mark.skipif_after_api_version("2.1.1")
@pytest.mark.parametrize(
    "update_func", ["search_update_plugins", "search.update_plugins"]
)
def test_update_plugins_not_implemented(client, update_func):
    with pytest.raises(NotImplementedError):
        client.func(update_func)()


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
        check(
            lambda: (p["enabled"] for p in get_plugins()),
            True,
            reverse=True,
            negate=True,
        )
        client.func(enable_func)(
            plugins=(p["name"] for p in get_plugins()), enable=True
        )
        check(
            lambda: (p["enabled"] for p in get_plugins()),
            False,
            reverse=True,
            negate=True,
        )

    enable_plugin()


@pytest.mark.skipif_before_api_version("2.1.1")
def test_plugins_slice(client):
    assert isinstance(client.search_plugins()[1:2], SearchPluginsList)


@pytest.mark.skipif_after_api_version("2.1.1")
@pytest.mark.parametrize(
    "enable_func", ["search_enable_plugin", "search.enable_plugin"]
)
def test_enable_plugin_not_implemented(client, enable_func):
    with pytest.raises(NotImplementedError):
        client.func(enable_func)()


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
        check(
            lambda: (p.name for p in client.search.plugins),
            PLUGIN_NAME,
            reverse=True,
        )

    @retry()
    def uninstall_plugin():
        client.func(uninstall_func)(names=PLUGIN_NAME)
        check(
            lambda: (p.name for p in client.search.plugins),
            PLUGIN_NAME,
            reverse=True,
            negate=True,
        )

    install_plugin()
    uninstall_plugin()


@pytest.mark.skipif_after_api_version("2.1.1")
@pytest.mark.parametrize(
    "install_func, uninstall_func",
    (
        ["search_install_plugin", "search_uninstall_plugin"],
        ["search.install_plugin", "search.uninstall_plugin"],
    ),
)
def test_install_uninstall_plugin_not_implemented(client, install_func, uninstall_func):
    with pytest.raises(NotImplementedError):
        client.func(install_func)()
    with pytest.raises(NotImplementedError):
        client.func(uninstall_func)()


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.skipif_after_api_version("2.6")
@pytest.mark.parametrize("categories_func", ["search_categories", "search.categories"])
def test_categories(client, categories_func):
    assert isinstance(client.func(categories_func)(), SearchCategoriesList)
    assert isinstance(client.func(categories_func)()[1:2], SearchCategoriesList)
    check(lambda: client.func(categories_func)(), "All categories", reverse=True)


@pytest.mark.skipif_after_api_version("2.1.1")
@pytest.mark.parametrize("categories_func", ["search_categories", "search.categories"])
def test_categories_not_implemented(client, categories_func):
    with pytest.raises(NotImplementedError):
        client.func(categories_func)()


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
        check(
            lambda: client.func(status_func)(search_id=job["id"])[0]["status"],
            "Stopped",
        )

        client.func(delete_stop)(search_id=job["id"])
        statuses = client.func(status_func)()
        assert not statuses

    do_test()


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.parametrize("status_func", ["search_status", "search.status"])
def test_statuses_slice(client, status_func):
    assert isinstance(client.func(status_func)()[1:2], SearchStatusesList)


@pytest.mark.skipif_after_api_version("2.1.1")
@pytest.mark.parametrize(
    "client_func",
    [
        "search_start",
        "search_status",
        "search_results",
        "search_stop",
        "search_delete",
        "search.start",
        "search.status",
        "search.results",
        "search.stop",
        "search.delete",
    ],
)
def test_search_not_implemented(client, client_func):
    with pytest.raises(NotImplementedError):
        client.func(client_func)()


@pytest.mark.skipif_before_api_version("2.1.1")
@pytest.mark.parametrize(
    "stop_func, start_func",
    [("search_stop", "search_start"), ("search.stop", "search.start")],
)
def test_stop(client, stop_func, start_func):
    job = client.func(start_func)(pattern="Ubuntu", plugins="enabled", category="all")
    check(lambda: client.search.status(search_id=job["id"])[0]["status"], "Running")

    client.func(stop_func)(search_id=job.id)
    check(lambda: client.search.status(search_id=job["id"])[0]["status"], "Stopped")

    job = client.func(start_func)(pattern="Ubuntu", plugins="enabled", category="all")
    check(lambda: client.search.status(search_id=job["id"])[0]["status"], "Running")
    job.stop()
    check(lambda: client.search.status(search_id=job["id"])[0]["status"], "Stopped")


@pytest.mark.skipif_after_api_version("2.1.1")
@pytest.mark.parametrize(
    "client_func", ["search_stop", "search_start", "search.stop", "search.start"]
)
def test_stop_not_implemented(client, client_func):
    with pytest.raises(NotImplementedError):
        client.func(client_func)()


@pytest.mark.skipif_before_api_version("2.1.1")
def test_delete(client):
    job = client.search_start(pattern="Ubuntu", plugins="enabled", category="all")
    job.delete()
    with pytest.raises(NotFound404Error):
        job.status()


@pytest.mark.skipif_after_api_version("2.1.1")
def test_delete_not_implemented(client):
    with pytest.raises(NotImplementedError):
        client.search_stop(search_id=100)


@pytest.mark.skipif_before_api_version("2.11")
@pytest.mark.parametrize(
    "client_func",
    [
        "search_download_torrent",
        "search_downloadTorrent",
        "search.download_torrent",
        "search.downloadTorrent",
    ],
)
def test_download_torrent(client, client_func):
    # run update to ensure plugins are loaded
    client.search.update_plugins()
    check(
        lambda: [p.name for p in client.search.plugins],
        "eztv",
        reverse=True,
    )
    try:
        client.func(client_func)(url=TORRENT2_URL, plugin="eztv")
        check(
            lambda: [t.hash for t in client.torrents_info()],
            TORRENT2_HASH,
            reverse=True,
        )
    finally:
        client.torrents.delete(torrent_hashes=TORRENT2_HASH)
        check(
            lambda: [t.hash for t in client.torrents_info()],
            TORRENT2_HASH,
            reverse=True,
            negate=True,
        )


@pytest.mark.skipif_after_api_version("2.11")
def test_download_torrent_not_implemented(client):
    with pytest.raises(NotImplementedError):
        client.search_download_torrent(search_id=100)
