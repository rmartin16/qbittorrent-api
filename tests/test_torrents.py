import errno
import platform
import sys
from contextlib import ExitStack, suppress
from time import sleep
from unittest.mock import MagicMock

import pytest
import requests

from qbittorrentapi import APINames
from qbittorrentapi._version_support import v
from qbittorrentapi.exceptions import (
    Conflict409Error,
    Forbidden403Error,
    InvalidRequest400Error,
    TorrentFileError,
    TorrentFileNotFoundError,
    TorrentFilePermissionError,
    UnsupportedMediaType415Error,
)
from qbittorrentapi.torrents import (
    TagList,
    TorrentCategoriesDictionary,
    TorrentFilesList,
    TorrentInfoList,
    TorrentLimitsDictionary,
    TorrentMetadataDictionary,
    TorrentMetadataList,
    TorrentPieceInfoList,
    TorrentPropertiesDictionary,
    TorrentsAddedMetadata,
    TorrentsAddPeersDictionary,
    TorrentSSLParametersDictionary,
    TrackersList,
    WebSeedsList,
)
from tests.conftest import (
    ROOT_FOLDER_TORRENT_FILE,
    ROOT_FOLDER_TORRENT_HASH,
    TORRENT1_FILE,
    TORRENT1_FILENAME,
    TORRENT1_HASH,
    TORRENT1_URL,
    TORRENT2_FILENAME,
    TORRENT2_HASH,
    TORRENT2_URL,
    new_torrent_standalone,
)
from tests.utils import (
    WEBSEED_RESEND_EVERY,
    WEBSEED_TIMEOUT,
    as_list,
    eventually,
    mkpath,
    retry,
)


def disable_queueing(client):
    if client.app.preferences.queueing_enabled:
        client.app.set_preferences(dict(queueing_enabled=False))


def enable_queueing(client):
    if not client.app.preferences.queueing_enabled:
        client.app.set_preferences(dict(queueing_enabled=True))


# Each endpoint is reachable as ``client.torrents_x()`` and ``client.torrents.x()``,
# both with a camelCase alias. These lists are shared by the tests for the endpoint
# and its "raises NotImplementedError on older API versions" counterpart, so the two
# can never drift apart.
ADD_WEBSEEDS_FUNCS = [
    "torrents_add_webseeds",
    "torrents_addWebSeeds",
    "torrents.add_webseeds",
    "torrents.addWebSeeds",
]
EDIT_WEBSEED_FUNCS = [
    "torrents_edit_webseed",
    "torrents_editWebSeed",
    "torrents.edit_webseed",
    "torrents.editWebSeed",
]
REMOVE_WEBSEEDS_FUNCS = [
    "torrents_remove_webseeds",
    "torrents_removeWebSeeds",
    "torrents.remove_webseeds",
    "torrents.removeWebSeeds",
]

# webseed endpoints accept either a single URL or a list of them
WEBSEED_URLS = [
    "http://example/webseedone",
    ["http://example/webseedone", "http://example/webseedtwo"],
]


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    all_dotted_methods = {
        meth
        for namespace in [APINames.Torrents, "torrent_tags", "torrent_categories"]
        for meth in dir(getattr(client, namespace))
    }

    for meth in [meth for meth in dir(client) if meth.startswith("torrents_")]:
        assert meth.removeprefix("torrents_") in all_dotted_methods


def download_torrent_file(url, dest=None):
    """
    Download a torrent file, retrying transient failures.

    Returns the raw bytes when ``dest`` is None; otherwise writes the file to
    ``dest`` and returns that path.
    """
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            with requests.get(url, timeout=30) as r:
                r.raise_for_status()
                if dest is None:
                    return r.content
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        f.write(chunk)
                return dest
        except Exception:
            if attempt >= max_attempts - 1:
                raise Exception(f"Download failed: {url}") from None


def downloaded_torrent_paths(tmp_path):
    """Both test torrents downloaded to ``tmp_path``."""
    return [
        download_torrent_file(TORRENT1_URL, mkpath(tmp_path, TORRENT1_FILENAME)),
        download_torrent_file(TORRENT2_URL, mkpath(tmp_path, TORRENT2_FILENAME)),
    ]


def build_add_kwargs(source, single, tmp_path, stack):
    """
    Build the ``torrents_add()`` kwargs supplying the test torrents via ``source``.

    ``stack`` is an :class:`~contextlib.ExitStack` used to close any opened files.
    """
    if source == "urls":
        urls = [TORRENT1_URL, TORRENT2_URL]
        return dict(urls=urls[0] if single else tuple(urls))

    if source == "paths":
        paths = downloaded_torrent_paths(tmp_path)
        return dict(torrent_files=paths[0] if single else tuple(paths))

    if source == "path_dict":
        paths = downloaded_torrent_paths(tmp_path)
        pairs = list(zip([TORRENT1_FILENAME, TORRENT2_FILENAME], paths))
        return dict(torrent_files=dict(pairs[:1] if single else pairs))

    if source == "filehandles":
        handles = [
            # the ExitStack closes these; ruff doesn't recognize enter_context()
            stack.enter_context(open(torrent_path, "rb"))  # noqa: SIM115
            for torrent_path in downloaded_torrent_paths(tmp_path)
        ]
        return dict(torrent_files=handles[0] if single else tuple(handles))

    if source == "bytes":
        blobs = [
            download_torrent_file(TORRENT1_URL),
            download_torrent_file(TORRENT2_URL),
        ]
        return dict(torrent_files=blobs[0] if single else tuple(blobs))

    raise ValueError(f"unknown torrent source: {source}")


# something was wrong with torrents_add on v2.0.0 (the initial version)
@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "add_func, delete_func",
    [("torrents_add", "torrents_delete"), ("torrents.add", "torrents.delete")],
)
@pytest.mark.parametrize(
    "source", ["urls", "paths", "path_dict", "filehandles", "bytes"]
)
@pytest.mark.parametrize("single", [True, False], ids=["single", "multiple"])
def test_add_delete(
    client, api_version, add_func, delete_func, source, single, tmp_path
):
    expected_hashes = [TORRENT1_HASH] if single else [TORRENT1_HASH, TORRENT2_HASH]

    def delete_test_torrents():
        """Delete through ``delete_func`` so both namespaces are exercised."""
        client.func(delete_func)(delete_files=True, torrent_hashes=TORRENT1_HASH)
        client.func(delete_func)(delete_files=True, torrent_hashes=TORRENT2_HASH)
        for attempt in eventually():
            with attempt:
                assert TORRENT2_HASH not in [t.hash for t in client.torrents_info()]

    @retry()
    def add_and_delete():
        # each attempt must start from a clean slate, so the torrents are always
        # removed again...whether the add succeeded, failed, or half-succeeded
        try:
            # Arrange
            with ExitStack() as stack:
                add_kwargs = build_add_kwargs(source, single, tmp_path, stack)

                # Act
                resp = client.func(add_func)(**add_kwargs)

            # Assert
            if source != "urls":
                # adding by URL returns nothing worth asserting on
                if v(api_version) >= v("2.14.0"):
                    assert isinstance(resp, TorrentsAddedMetadata)
                else:
                    assert resp == "Ok."

            for torrent_hash in expected_hashes:
                for attempt in eventually():
                    with attempt:
                        assert torrent_hash in [t.hash for t in client.torrents_info()]
        finally:
            delete_test_torrents()

    add_and_delete()


def test_add_torrent_file_fail(client, monkeypatch):
    with pytest.raises(TorrentFileNotFoundError):
        client.torrents_add(torrent_files="/tmp/asdfasdfasdfasdf")

    with pytest.raises(TorrentFilePermissionError):
        client.torrents_add(torrent_files="/etc/shadow")

    if platform.python_implementation() == "CPython":
        with pytest.raises(TorrentFileError):

            def fake_open(*arg, **kwargs):
                raise OSError(errno.ENODEV)

            with monkeypatch.context() as m:
                m.setitem(__builtins__, "open", fake_open)
                client.torrents_add(torrent_files="/etc/hosts")


def test_add_skip_checking_sends_both_names(client, monkeypatch):
    """``skip_checking`` was renamed to ``seedMode`` in Web API v2.16.0."""
    sent = {}

    def fake_post(*args, **kwargs):
        sent.update(kwargs["data"])
        return MagicMock(text="Ok.")

    monkeypatch.setattr(client, "_post", fake_post)
    client.torrents_add(urls=TORRENT1_URL, is_skip_checking=True)

    assert sent["skip_checking"] == (None, True)
    assert sent["seedMode"] == (None, True)


def test_add_file_priorities_and_downloader(client, monkeypatch):
    """``filePriorities`` (v2.11.9) and ``downloader`` (v2.13.1) on torrents/add."""
    sent = {}

    def fake_post(*args, **kwargs):
        sent.update(kwargs["data"])
        return MagicMock(text="Ok.")

    monkeypatch.setattr(client, "_post", fake_post)
    client.torrents_add(
        urls=TORRENT1_URL,
        file_priorities=[0, 1, 7],
        downloader="a-search-plugin",
    )

    assert sent["filePriorities"] == (None, "0,1,7")
    assert sent["downloader"] == (None, "a-search-plugin")


@pytest.mark.parametrize("keep_root_folder", [True, False, None])
@pytest.mark.parametrize(
    "content_layout", [None, "Original", "Subfolder", "NoSubfolder"]
)
def test_add_options(client, api_version, keep_root_folder, content_layout, tmp_path):
    @retry(3)
    def do_test():
        if v(api_version) >= v("2.3.0"):
            client.torrents_create_tags("option-tag")
        new_torrent = new_torrent_standalone(
            client=client,
            torrent_files=ROOT_FOLDER_TORRENT_FILE,
            torrent_hash=ROOT_FOLDER_TORRENT_HASH,
            save_path=mkpath(tmp_path, "test_download"),
            category="test_category",
            is_paused=True,
            upload_limit=1024,
            download_limit=2048,
            is_sequential_download=True,
            is_first_last_piece_priority=True,
            is_root_folder=keep_root_folder,
            rename="this is a new name for the torrent",
            use_auto_torrent_management=False,
            tags="option-tag",
            content_layout=content_layout,
            ratio_limit=2,
            seeding_time_limit=120,
        )

        with new_torrent as torrent:
            for attempt in eventually():
                with attempt:
                    assert torrent.info.category == "test_category"
            for attempt in eventually():
                with attempt:
                    assert torrent.info.state in ("pausedDL", "stoppedDL")
            for attempt in eventually():
                with attempt:
                    assert mkpath(torrent.info.save_path) == mkpath(
                        tmp_path, "test_download"
                    )
            for attempt in eventually():
                with attempt:
                    assert torrent.info.up_limit == 1024
            for attempt in eventually():
                with attempt:
                    assert torrent.info.dl_limit == 2048
            for attempt in eventually():
                with attempt:
                    assert torrent.info.seq_dl is True
            if v(api_version) >= v("2.0.1"):
                for attempt in eventually():
                    with attempt:
                        assert torrent.info.f_l_piece_prio is True
            if content_layout is None:
                for attempt in eventually():
                    with attempt:
                        assert torrent.files[0]["name"].startswith("root_folder") == (
                            keep_root_folder in {True, None}
                        )
            for attempt in eventually():
                with attempt:
                    assert torrent.info.name == "this is a new name for the torrent"
            for attempt in eventually():
                with attempt:
                    assert torrent.info.auto_tmm is False
            if v(api_version) >= v("2.6.2"):
                for attempt in eventually():
                    with attempt:
                        assert torrent.info.tags == "option-tag"

            if v(api_version) >= v("2.7"):
                # after web api v2.7...root dir is driven by content_layout
                if content_layout is None:
                    should_root_dir_exists = keep_root_folder in {None, True}
                else:
                    should_root_dir_exists = content_layout in {"Original", "Subfolder"}
            else:
                # before web api v2.7...it is driven by is_root_folder
                if content_layout is not None and keep_root_folder is None:
                    should_root_dir_exists = content_layout in {"Original", "Subfolder"}
                else:
                    should_root_dir_exists = keep_root_folder in {None, True}
            for attempt in eventually():
                with attempt:
                    assert (
                        any(f["name"].startswith("root_folder") for f in torrent.files)
                        == should_root_dir_exists
                    )

            if v(api_version) >= v("2.8.1"):
                for attempt in eventually():
                    with attempt:
                        assert torrent.info.ratio_limit == 2
                for attempt in eventually():
                    with attempt:
                        assert torrent.info.seeding_time_limit == 120

    try:
        do_test()
    finally:
        # created by do_test() and not removed with the torrent
        with suppress(Exception):
            client.torrents_delete_tags(tags="option-tag")


@pytest.mark.skipif_before_api_version("2.8.4")
@pytest.mark.parametrize("use_download_path", [None, True, False])
def test_torrents_add_download_path(client, use_download_path, tmp_path):
    client.torrents_delete(torrent_hashes=ROOT_FOLDER_TORRENT_HASH, delete_files=True)
    save_path = mkpath(tmp_path, "down_path_save_path_test")
    download_path = mkpath(tmp_path, "down_path_test")
    new_torrent = new_torrent_standalone(
        client=client,
        torrent_hash=ROOT_FOLDER_TORRENT_HASH,
        torrent_files=ROOT_FOLDER_TORRENT_FILE,
        download_path=download_path,
        use_download_path=use_download_path,
        test_download_limit=1024,
        save_path=save_path,
    )

    with new_torrent as torrent:
        if use_download_path is False:
            for attempt in eventually():
                with attempt:
                    assert mkpath(torrent.info.download_path) != download_path
        else:
            for attempt in eventually():
                with attempt:
                    assert mkpath(torrent.info.download_path) == download_path


@pytest.mark.skipif_before_api_version("2.9.3")
@pytest.mark.parametrize("count_func", ["torrents_count", "torrents.count"])
def test_count(client, count_func):
    assert client.func(count_func)() == 1


@pytest.mark.parametrize(
    "properties_func", ["torrents_properties", "torrents.properties"]
)
def test_properties(client, orig_torrent, properties_func):
    props = client.func(properties_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(props, TorrentPropertiesDictionary)


@pytest.mark.parametrize("trackers_func", ["torrents_trackers", "torrents.trackers"])
def test_trackers(client, orig_torrent, trackers_func):
    trackers = client.func(trackers_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(trackers, TrackersList)


@pytest.mark.parametrize("trackers_func", ["torrents_trackers", "torrents.trackers"])
def test_trackers_slice(client, orig_torrent, trackers_func):
    trackers = client.func(trackers_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(trackers[1:2], TrackersList)


@pytest.mark.parametrize("webseeds_func", ["torrents_webseeds", "torrents.webseeds"])
def test_webseeds(client, orig_torrent, webseeds_func):
    web_seeds = client.func(webseeds_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(web_seeds, WebSeedsList)


@pytest.mark.parametrize("webseeds_func", ["torrents_webseeds", "torrents.webseeds"])
def test_webseeds_slice(client, orig_torrent, webseeds_func):
    web_seeds = client.func(webseeds_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(web_seeds[1:2], WebSeedsList)


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize("add_webseeds_func", ADD_WEBSEEDS_FUNCS)
@pytest.mark.parametrize("webseeds", WEBSEED_URLS)
def test_add_webseeds(client, new_torrent, add_webseeds_func, webseeds):
    assert new_torrent.webseeds == WebSeedsList([])

    def add_webseeds():
        client.func(add_webseeds_func)(torrent_hash=new_torrent.hash, urls=webseeds)

    add_webseeds()
    for attempt in eventually(
        timeout=WEBSEED_TIMEOUT, resend=add_webseeds, resend_every=WEBSEED_RESEND_EVERY
    ):
        with attempt:
            assert set(as_list(webseeds)) <= {w.url for w in new_torrent.webseeds}


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize("edit_webseed_func", EDIT_WEBSEED_FUNCS)
def test_edit_webseeds(client, new_torrent, edit_webseed_func):
    assert new_torrent.webseeds == WebSeedsList([])
    orig_url, new_url = "http://example/asdf", "http://example/qwer"

    def urls():
        return [w.url for w in new_torrent.webseeds]

    def add_orig_url():
        new_torrent.add_webseeds(urls=orig_url)

    def edit_webseed():
        client.func(edit_webseed_func)(
            torrent_hash=new_torrent.hash, orig_url=orig_url, new_url=new_url
        )

    # see tests/test_torrent.py::test_edit_webseeds for why this is re-sent
    def redo_edit():
        current = urls()
        if orig_url in current:
            edit_webseed()
        elif new_url not in current:
            add_orig_url()

    add_orig_url()
    for attempt in eventually(
        timeout=WEBSEED_TIMEOUT, resend=add_orig_url, resend_every=WEBSEED_RESEND_EVERY
    ):
        with attempt:
            assert orig_url in urls()
    edit_webseed()
    for attempt in eventually(
        timeout=WEBSEED_TIMEOUT, resend=redo_edit, resend_every=WEBSEED_RESEND_EVERY
    ):
        with attempt:
            assert new_url in urls()
    for attempt in eventually(
        timeout=WEBSEED_TIMEOUT, resend=redo_edit, resend_every=WEBSEED_RESEND_EVERY
    ):
        with attempt:
            assert len(new_torrent.webseeds) == 1


@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.parametrize("remove_webseeds_func", REMOVE_WEBSEEDS_FUNCS)
@pytest.mark.parametrize("webseeds", WEBSEED_URLS)
def test_remove_webseeds(client, new_torrent, remove_webseeds_func, webseeds):
    assert new_torrent.webseeds == WebSeedsList([])
    all_webseeds = [
        "http://example/webseedone",
        "http://example/webseedtwo",
        "http://example/webseedthree",
    ]

    def add_webseeds():
        new_torrent.add_webseeds(urls=all_webseeds)

    def remove_webseeds():
        client.func(remove_webseeds_func)(torrent_hash=new_torrent.hash, urls=webseeds)

    add_webseeds()
    # removing before qBittorrent registers them would silently do nothing
    for attempt in eventually(
        timeout=WEBSEED_TIMEOUT, resend=add_webseeds, resend_every=WEBSEED_RESEND_EVERY
    ):
        with attempt:
            assert set(all_webseeds) <= {w.url for w in new_torrent.webseeds}
    remove_webseeds()
    for webseed in webseeds if isinstance(webseeds, list) else [webseeds]:
        for attempt in eventually(
            timeout=WEBSEED_TIMEOUT,
            resend=remove_webseeds,
            resend_every=WEBSEED_RESEND_EVERY,
        ):
            with attempt:
                assert webseed not in {w.url for w in new_torrent.webseeds}


@pytest.mark.parametrize("files_func", ["torrents_files", "torrents.files"])
def test_files(client, orig_torrent, files_func):
    files = client.func(files_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(files, TorrentFilesList)
    assert "availability" in files[0]
    assert all(file["id"] == file["index"] for file in files)


@pytest.mark.parametrize("files_func", ["torrents_files", "torrents.files"])
def test_files_slice(client, orig_torrent, files_func):
    files = client.func(files_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(files[1:2], TorrentFilesList)


@pytest.mark.parametrize(
    "piece_state_func", ["torrents_piece_states", "torrents.piece_states"]
)
def test_piece_states(client, orig_torrent, piece_state_func):
    piece_states = client.func(piece_state_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_states, TorrentPieceInfoList)


@pytest.mark.parametrize(
    "piece_state_func", ["torrents_piece_states", "torrents.piece_states"]
)
def test_piece_states_slice(client, orig_torrent, piece_state_func):
    piece_states = client.func(piece_state_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_states[1:2], TorrentPieceInfoList)


@pytest.mark.parametrize(
    "piece_hashes_func", ["torrents_piece_hashes", "torrents.piece_hashes"]
)
def test_piece_hashes(client, orig_torrent, piece_hashes_func):
    piece_hashes = client.func(piece_hashes_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_hashes, TorrentPieceInfoList)


@pytest.mark.skipif_before_api_version("2.15.1")
@pytest.mark.parametrize(
    "piece_availability_func",
    ["torrents_piece_availability", "torrents.piece_availability"],
)
def test_piece_availability(client, orig_torrent, piece_availability_func):
    availability = client.func(piece_availability_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(availability, TorrentPieceInfoList)
    assert isinstance(orig_torrent.piece_availability, TorrentPieceInfoList)


@pytest.mark.skipif_before_api_version("2.10.3")
@pytest.mark.parametrize(
    "ssl_params_func", ["torrents_ssl_parameters", "torrents.ssl_parameters"]
)
def test_ssl_parameters(client, orig_torrent, ssl_params_func):
    ssl_params = client.func(ssl_params_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(ssl_params, TorrentSSLParametersDictionary)
    # a non-SSL torrent reports empty parameters
    assert "ssl_certificate" in ssl_params
    assert isinstance(orig_torrent.ssl_parameters, TorrentSSLParametersDictionary)


@pytest.mark.skipif_before_api_version("2.10.3")
@pytest.mark.parametrize(
    "set_ssl_params_func",
    ["torrents_set_ssl_parameters", "torrents.set_ssl_parameters"],
)
def test_set_ssl_parameters(client, orig_torrent, set_ssl_params_func):
    # qBittorrent raises APIErrorType::BadData for SSL parameters that don't
    # parse, which it maps to HTTP 415 rather than 400
    with pytest.raises(UnsupportedMediaType415Error):
        client.func(set_ssl_params_func)(
            torrent_hash=orig_torrent.hash,
            ssl_certificate="not-a-certificate",
            ssl_private_key="not-a-key",
            ssl_dh_params="not-dh-params",
        )

    with pytest.raises(UnsupportedMediaType415Error):
        orig_torrent.set_ssl_parameters(
            ssl_certificate="not-a-certificate",
            ssl_private_key="not-a-key",
            ssl_dh_params="not-dh-params",
        )


@pytest.mark.skipif_before_api_version("2.11.9")
@pytest.mark.parametrize(
    "fetch_metadata_func", ["torrents_fetch_metadata", "torrents.fetch_metadata"]
)
def test_fetch_metadata(client, fetch_metadata_func):
    metadata = client.func(fetch_metadata_func)(source=TORRENT1_URL)
    assert isinstance(metadata, TorrentMetadataDictionary)


@pytest.mark.skipif_before_api_version("2.11.9")
@pytest.mark.parametrize(
    "fetch_metadata_func", ["torrents_fetch_metadata", "torrents.fetch_metadata"]
)
def test_fetch_metadata_invalid_source(client, fetch_metadata_func):
    with pytest.raises(InvalidRequest400Error):
        client.func(fetch_metadata_func)(source="not a torrent source")


@pytest.mark.skipif_before_api_version("2.11.9")
@pytest.mark.parametrize(
    "parse_metadata_func", ["torrents_parse_metadata", "torrents.parse_metadata"]
)
def test_parse_metadata(client, parse_metadata_func):
    metadata = client.func(parse_metadata_func)(torrent_files=TORRENT1_FILE)
    assert isinstance(metadata, TorrentMetadataList)
    assert len(metadata) == 1
    assert isinstance(metadata[0], TorrentMetadataDictionary)


@pytest.mark.skipif_before_api_version("2.11.9")
@pytest.mark.parametrize(
    "save_metadata_func", ["torrents_save_metadata", "torrents.save_metadata"]
)
def test_save_metadata(client, save_metadata_func):
    client.torrents_parse_metadata(torrent_files=TORRENT1_FILE)
    torrent_file = client.func(save_metadata_func)(source=TORRENT1_HASH)
    assert isinstance(torrent_file, bytes)
    assert torrent_file[:11] == b"d8:announce"


@pytest.mark.parametrize(
    "piece_hashes_func", ["torrents_piece_hashes", "torrents.piece_hashes"]
)
def test_piece_hashes_slice(client, orig_torrent, piece_hashes_func):
    piece_hashes = client.func(piece_hashes_func)(torrent_hash=orig_torrent.hash)
    assert isinstance(piece_hashes[1:2], TorrentPieceInfoList)


@pytest.mark.parametrize("trackers", ["127.0.0.1", ["127.0.0.2", "127.0.0.3"]])
@pytest.mark.parametrize(
    "add_trackers_func", ["torrents_add_trackers", "torrents.add_trackers"]
)
def test_add_trackers(client, trackers, new_torrent, add_trackers_func):
    client.func(add_trackers_func)(torrent_hash=new_torrent.hash, urls=trackers)
    for attempt in eventually():
        with attempt:
            assert set(as_list(trackers)) <= {t.url for t in new_torrent.trackers}


@pytest.mark.skipif_before_api_version("2.2.0")
@pytest.mark.parametrize(
    "edit_trackers_func", ["torrents_edit_tracker", "torrents.edit_tracker"]
)
def test_edit_tracker(client, orig_torrent, edit_trackers_func):
    orig_torrent.add_trackers("127.1.0.1")
    client.func(edit_trackers_func)(
        torrent_hash=orig_torrent.hash,
        original_url="127.1.0.1",
        new_url="127.1.0.2",
    )
    for attempt in eventually():
        with attempt:
            assert "127.1.0.2" in (t.url for t in orig_torrent.trackers)
    client.torrents_remove_trackers(torrent_hash=orig_torrent.hash, urls="127.1.0.2")


@pytest.mark.skipif_before_api_version("2.2.0")
@pytest.mark.parametrize(
    "trackers",
    [
        ["127.2.0.1"],
        ["127.2.0.2", "127.2.0.3"],
    ],
)
@pytest.mark.parametrize(
    "remove_trackers_func", ["torrents_remove_trackers", "torrents.remove_trackers"]
)
def test_remove_trackers(client, trackers, orig_torrent, remove_trackers_func):
    orig_torrent.add_trackers(trackers)
    client.func(remove_trackers_func)(torrent_hash=orig_torrent.hash, urls=trackers)
    for attempt in eventually():
        with attempt:
            assert set(as_list(trackers)).isdisjoint(
                {t.url for t in orig_torrent.trackers}
            )


@pytest.mark.parametrize(
    "file_prio_func", ["torrents_file_priority", "torrents.file_priority"]
)
def test_file_priority(client, orig_torrent, file_prio_func):
    client.func(file_prio_func)(torrent_hash=orig_torrent.hash, file_ids=0, priority=6)
    for attempt in eventually():
        with attempt:
            assert orig_torrent.files[0].priority == 6
    client.func(file_prio_func)(torrent_hash=orig_torrent.hash, file_ids=0, priority=7)
    for attempt in eventually():
        with attempt:
            assert orig_torrent.files[0].priority == 7


@pytest.mark.parametrize("new_name", ["new name 2", "new_name_2"])
@pytest.mark.parametrize("rename_func", ["torrents_rename", "torrents.rename"])
def test_rename(client, new_torrent, new_name, rename_func):
    client.func(rename_func)(torrent_hash=new_torrent.hash, new_torrent_name=new_name)
    for attempt in eventually():
        with attempt:
            assert new_torrent.info.name.replace("+", " ") == new_name


@pytest.mark.skipif_before_api_version("2.4.0")
@pytest.mark.parametrize("new_name", ["new name file 2", "new_name_file_2"])
@pytest.mark.parametrize(
    "rename_file_func", ["torrents_rename_file", "torrents.rename_file"]
)
def test_rename_file(
    client,
    new_torrent,
    new_name,
    rename_file_func,
):
    @retry()
    def test():
        # pre-v4.3.3 rename_file signature
        client.func(rename_file_func)(
            torrent_hash=new_torrent.hash, file_id=0, new_file_name=new_name
        )
        for attempt in eventually():
            with attempt:
                assert new_torrent.files[0].name.replace("+", " ") == new_name
        # test invalid file ID is rejected
        with pytest.raises(Conflict409Error):
            client.func(rename_file_func)(
                torrent_hash=new_torrent.hash, file_id=10, new_file_name=new_name
            )
        # post-v4.3.3 rename_file signature
        new_new_name = new_name + "NEW"
        client.func(rename_file_func)(
            torrent_hash=new_torrent.hash,
            old_path=new_torrent.files[0].name,
            new_path=new_new_name,
        )
        for attempt in eventually():
            with attempt:
                assert new_torrent.files[0].name.replace("+", " ") == new_new_name
        # test invalid old_path is rejected
        with pytest.raises(Conflict409Error):
            client.func(rename_file_func)(
                torrent_hash=new_torrent.hash, old_path="asdf", new_path="xcvb"
            )

    test()


@pytest.mark.skipif_before_api_version("2.7")
@pytest.mark.parametrize("new_name", ["asdf zxcv", "asdf_zxcv"])
@pytest.mark.parametrize(
    "rename_folder_func", ["torrents_rename_folder", "torrents.rename_folder"]
)
def test_rename_folder(client, app_version, new_torrent, new_name, rename_folder_func):
    @retry()
    def test():
        if v(app_version) >= v("v4.3.3"):
            # move the file in to a new folder
            orig_file_path = new_torrent.files[0].name
            new_folder = "qwer"
            client.torrents_rename_file(
                torrent_hash=new_torrent.hash,
                old_path=orig_file_path,
                new_path=new_folder + "/" + orig_file_path,
            )

            # wait for the folder to be renamed
            for attempt in eventually():
                with attempt:
                    assert new_folder in [
                        f.name.split("/")[0] for f in new_torrent.files
                    ]

            # test rename that new folder
            client.func(rename_folder_func)(
                torrent_hash=new_torrent.hash,
                old_path=new_folder,
                new_path=new_name,
            )
            for attempt in eventually():
                with attempt:
                    assert (
                        new_torrent.files[0].name.replace("+", " ")
                        == new_name + "/" + orig_file_path
                    )
        elif v(app_version) >= v("v4.3.2"):
            with pytest.raises(NotImplementedError):
                client.func(rename_folder_func)()

    test()


@pytest.mark.skipif_before_api_version("2.8.14")
@pytest.mark.parametrize("export_func", ["torrents_export", "torrents.export"])
def test_export(client, orig_torrent, export_func):
    assert isinstance(client.func(export_func)(torrent_hash=orig_torrent.hash), bytes)


@pytest.mark.skipif_before_api_version("2.16.0")
@pytest.mark.parametrize(
    "download_file_func", ["torrents_download_file", "torrents.download_file"]
)
def test_download_file(client, orig_torrent, download_file_func):
    # the test torrents are never actually downloaded, so qBittorrent refuses
    # to hand back a path for the file
    with pytest.raises(Conflict409Error):
        client.func(download_file_func)(torrent_hash=orig_torrent.hash, file=0)

    with pytest.raises(Conflict409Error):
        orig_torrent.download_file(file=0)


@pytest.mark.parametrize("info_func", ["torrents_info", "torrents.info"])
def test_torrents_info(client, info_func):
    assert isinstance(client.func(info_func)(), TorrentInfoList)
    if "." in info_func:
        assert isinstance(client.func(info_func).all(), TorrentInfoList)
        assert isinstance(client.func(info_func).downloading(), TorrentInfoList)
        assert isinstance(client.func(info_func).seeding(), TorrentInfoList)
        assert isinstance(client.func(info_func).completed(), TorrentInfoList)
        assert isinstance(client.func(info_func).paused(), TorrentInfoList)
        assert isinstance(client.func(info_func).active(), TorrentInfoList)
        assert isinstance(client.func(info_func).inactive(), TorrentInfoList)
        assert isinstance(client.func(info_func).resumed(), TorrentInfoList)
        assert isinstance(client.func(info_func).stalled(), TorrentInfoList)
        assert isinstance(client.func(info_func).stalled_uploading(), TorrentInfoList)
        assert isinstance(client.func(info_func).stalled_downloading(), TorrentInfoList)
        assert isinstance(client.func(info_func).checking(), TorrentInfoList)
        assert isinstance(client.func(info_func).moving(), TorrentInfoList)
        assert isinstance(client.func(info_func).errored(), TorrentInfoList)


def test_torrents_info_slice(client):
    assert isinstance(client.torrents_info()[1:2], TorrentInfoList)


@pytest.mark.skipif_before_api_version("2.8.3")
@pytest.mark.parametrize("info_func", ["torrents_info", "torrents.info"])
def test_torrents_info_tag(client, new_torrent, info_func):
    tag_name = "tag_filter_name"
    try:
        client.torrents_add_tags(tags=tag_name, torrent_hashes=new_torrent.hash)
        torrents = client.func(info_func)(torrent_hashes=new_torrent.hash, tag=tag_name)
        assert new_torrent.hash in {t.hash for t in torrents}
    finally:
        client.torrents_delete_tags(tags=tag_name)


# test fails on 4.1.0 release
@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "stop_func, start_func",
    [
        ("torrents_stop", "torrents_start"),
        ("torrents_pause", "torrents_resume"),
        ("torrents.stop", "torrents.start"),
        ("torrents.pause", "torrents.resume"),
    ],
)
def test_stop_start(client, new_torrent, stop_func, start_func):
    client.func(stop_func)(torrent_hashes=new_torrent.hash)
    for attempt in eventually():
        with attempt:
            assert (
                client.torrents_info(torrent_hashes=new_torrent.hash)[
                    0
                ].state_enum.is_paused
                is True
            )

    client.func(start_func)(torrent_hashes=new_torrent.hash)
    for attempt in eventually():
        with attempt:
            assert (
                client.torrents_info(torrent_hashes=new_torrent.hash)[
                    0
                ].state_enum.is_paused
                is False
            )


def test_action_for_all_torrents(client):
    client.torrents.resume.all()
    for torrent in client.torrents.info():
        for attempt in eventually():
            with attempt:
                assert client.torrents_info(torrent_hashes=torrent.hash)[
                    0
                ].state not in {"pausedDL", "stoppedDL"}
    client.torrents.pause.all()
    for torrent in client.torrents.info():
        for attempt in eventually():
            with attempt:
                assert client.torrents_info(torrent_hashes=torrent.hash)[0].state in {
                    "stalledDL",
                    "pausedDL",
                    "stoppedDL",
                }


@pytest.mark.parametrize("recheck_func", ["torrents_recheck", "torrents.recheck"])
def test_recheck(client, orig_torrent, recheck_func):
    client.func(recheck_func)(torrent_hashes=orig_torrent.hash)


@pytest.mark.skipif_before_api_version("2.0.2")
@pytest.mark.parametrize(
    "reannounce_func", ["torrents_reannounce", "torrents.reannounce"]
)
def test_reannounce(client, orig_torrent, reannounce_func):
    client.func(reannounce_func)(torrent_hashes=orig_torrent.hash)


def test_reannounce_urls(client, monkeypatch):
    """``urls`` limits the reannounce to specific trackers (Web API v2.11.10)."""
    sent = {}

    def fake_post(*args, **kwargs):
        sent.update(kwargs["data"])

    monkeypatch.setattr(client, "_post", fake_post)
    client.torrents_reannounce(
        torrent_hashes="hash1",
        urls=["http://one.example/announce", "http://two.example/announce"],
    )

    assert sent["hashes"] == "hash1"
    assert sent["urls"] == ("http://one.example/announce|http://two.example/announce")


# priority doesn't seem to work on v4.1.0
@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "inc_prio_func, dec_prio_func, top_prio_func, bottom_prio_func",
    [
        (
            "torrents_increase_priority",
            "torrents_decrease_priority",
            "torrents_top_priority",
            "torrents_bottom_priority",
        ),
        (
            "torrents_increasePrio",
            "torrents_decreasePrio",
            "torrents_topPrio",
            "torrents_bottomPrio",
        ),
    ],
)
def test_priority(
    client, new_torrent, inc_prio_func, dec_prio_func, top_prio_func, bottom_prio_func
):
    disable_queueing(client)

    with pytest.raises(Conflict409Error):
        client.func(inc_prio_func)(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        client.func(dec_prio_func)(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        client.func(top_prio_func)(torrent_hashes=new_torrent.hash)
    with pytest.raises(Conflict409Error):
        client.func(bottom_prio_func)(torrent_hashes=new_torrent.hash)

    enable_queueing(client)

    @retry()
    def test1(current_priority):
        client.func(inc_prio_func)(torrent_hashes=new_torrent.hash)
        for attempt in eventually():
            with attempt:
                assert new_torrent.info.priority < current_priority

    @retry()
    def test2(current_priority):
        client.func(dec_prio_func)(torrent_hashes=new_torrent.hash)
        for attempt in eventually():
            with attempt:
                assert new_torrent.info.priority > current_priority

    @retry()
    def test3(current_priority):
        client.func(top_prio_func)(torrent_hashes=new_torrent.hash)
        for attempt in eventually():
            with attempt:
                assert new_torrent.info.priority < current_priority

    @retry()
    def test4(current_priority):
        client.func(bottom_prio_func)(torrent_hashes=new_torrent.hash)
        for attempt in eventually():
            with attempt:
                assert new_torrent.info.priority > current_priority

    test1(current_priority=new_torrent.info.priority)
    test2(current_priority=new_torrent.info.priority)
    test3(current_priority=new_torrent.info.priority)
    test4(current_priority=new_torrent.info.priority)


@pytest.mark.parametrize(
    "set_down_limit_func, down_limit_func",
    [
        ("torrents_set_download_limit", "torrents_download_limit"),
        ("torrents_setDownloadLimit", "torrents_downloadLimit"),
        ("torrents.set_download_limit", "torrents.download_limit"),
        ("torrents.setDownloadLimit", "torrents.downloadLimit"),
    ],
)
def test_download_limit(client, orig_torrent, set_down_limit_func, down_limit_func):
    orig_download_limit = client.func(down_limit_func)(
        torrent_hashes=orig_torrent.hash
    )[orig_torrent.hash]

    client.func(set_down_limit_func)(torrent_hashes=orig_torrent.hash, limit=100)
    assert isinstance(
        client.func(down_limit_func)(torrent_hashes=orig_torrent.hash),
        TorrentLimitsDictionary,
    )
    for attempt in eventually():
        with attempt:
            assert (
                client.func(down_limit_func)(torrent_hashes=orig_torrent.hash)[
                    orig_torrent.hash
                ]
                == 100
            )

    # reset download limit
    client.func(set_down_limit_func)(
        torrent_hashes=orig_torrent.hash, limit=orig_download_limit
    )
    for attempt in eventually():
        with attempt:
            assert (
                client.func(down_limit_func)(torrent_hashes=orig_torrent.hash)[
                    orig_torrent.hash
                ]
                == orig_download_limit
            )


@pytest.mark.parametrize(
    "set_up_limit_func, up_limit_func",
    [
        ("torrents_set_upload_limit", "torrents_upload_limit"),
        ("torrents_setUploadLimit", "torrents_uploadLimit"),
        ("torrents.set_upload_limit", "torrents.upload_limit"),
        ("torrents.setUploadLimit", "torrents.uploadLimit"),
    ],
)
def test_upload_limit(client, orig_torrent, set_up_limit_func, up_limit_func):
    orig_upload_limit = client.func(up_limit_func)(torrent_hashes=orig_torrent.hash)[
        orig_torrent.hash
    ]

    client.func(set_up_limit_func)(torrent_hashes=orig_torrent.hash, limit=100)
    assert isinstance(
        client.func(up_limit_func)(torrent_hashes=orig_torrent.hash),
        TorrentLimitsDictionary,
    )
    for attempt in eventually():
        with attempt:
            assert (
                client.func(up_limit_func)(torrent_hashes=orig_torrent.hash)[
                    orig_torrent.hash
                ]
                == 100
            )

    # reset upload limit
    client.func(set_up_limit_func)(
        torrent_hashes=orig_torrent.hash, limit=orig_upload_limit
    )
    for attempt in eventually():
        with attempt:
            assert (
                client.func(up_limit_func)(torrent_hashes=orig_torrent.hash)[
                    orig_torrent.hash
                ]
                == orig_upload_limit
            )


@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "set_share_limits_func",
    [
        "torrents_set_share_limits",
        "torrents_setShareLimits",
        "torrents.set_share_limits",
        "torrents.setShareLimits",
    ],
)
def test_set_share_limits(client, orig_torrent, set_share_limits_func):
    client.func(set_share_limits_func)(
        ratio_limit=2,
        seeding_time_limit=5,
        inactive_seeding_time_limit=8,
        share_limit_action="Stop",
        share_limits_mode="MatchAny",
        torrent_hashes=orig_torrent.hash,
    )
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.max_ratio == 2
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.max_seeding_time == 5
    if "share_limit_action" in orig_torrent.info:
        for attempt in eventually():
            with attempt:
                assert orig_torrent.info.share_limit_action == "Stop"
    if "share_limits_mode" in orig_torrent.info:
        for attempt in eventually():
            with attempt:
                assert orig_torrent.info.share_limits_mode == "MatchAny"
    if "max_inactive_seeding_time" in orig_torrent.info:
        for attempt in eventually():
            with attempt:
                assert orig_torrent.info.max_inactive_seeding_time == 8

    client.func(set_share_limits_func)(
        ratio_limit=3,
        seeding_time_limit=6,
        inactive_seeding_time_limit=9,
        share_limit_action="Remove",
        share_limits_mode="MatchAll",
        torrent_hashes=orig_torrent.hash,
    )
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.max_ratio == 3
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.max_seeding_time == 6
    if "share_limit_action" in orig_torrent.info:
        for attempt in eventually():
            with attempt:
                assert orig_torrent.info.share_limit_action == "Remove"
    if "share_limits_mode" in orig_torrent.info:
        for attempt in eventually():
            with attempt:
                assert orig_torrent.info.share_limits_mode == "MatchAll"
    if "max_inactive_seeding_time" in orig_torrent.info:
        for attempt in eventually():
            with attempt:
                assert orig_torrent.info.max_inactive_seeding_time == 9


@pytest.mark.skipif_before_api_version("2.0.2")
@pytest.mark.parametrize(
    "set_loc_func",
    [
        "torrents_set_location",
        "torrents_setLocation",
        "torrents.set_location",
        "torrents.setLocation",
    ],
)
def test_set_location(client, app_version, new_torrent, set_loc_func, tmp_path):
    # stopped erroring when the write check was removed for API
    if v(app_version) < v("v4.5.2"):
        with pytest.raises(Forbidden403Error):
            client.func(set_loc_func)(location="/etc/", torrent_hashes=new_torrent.hash)

    sleep(0.5)
    loc = mkpath(tmp_path, "1")
    client.func(set_loc_func)(location=loc, torrent_hashes=new_torrent.hash)
    # qBittorrent may return trailing separators depending on version....
    for attempt in eventually():
        with attempt:
            assert mkpath(new_torrent.info.save_path) == loc


@pytest.mark.skipif_before_api_version("2.8.4")
@pytest.mark.parametrize(
    "set_save_path_func",
    [
        "torrents_set_save_path",
        "torrents_setSavePath",
        "torrents.set_save_path",
        "torrents.setSavePath",
    ],
)
def test_set_save_path(client, new_torrent, set_save_path_func, tmp_path):
    with pytest.raises(Forbidden403Error):
        client.func(set_save_path_func)(
            save_path="/etc/", torrent_hashes=new_torrent.hash
        )
    with pytest.raises(Conflict409Error):
        client.func(set_save_path_func)(
            save_path="/etc/asdf", torrent_hashes=new_torrent.hash
        )

    loc = mkpath(tmp_path, "savepath1")
    client.func(set_save_path_func)(save_path=loc, torrent_hashes=new_torrent.hash)
    # qBittorrent may return trailing separators depending on version....
    for attempt in eventually():
        with attempt:
            assert mkpath(new_torrent.info.save_path) == loc


@pytest.mark.skipif_before_api_version("2.8.4")
@pytest.mark.parametrize(
    "set_down_path_func",
    [
        "torrents_set_download_path",
        "torrents_setDownloadPath",
        "torrents.set_download_path",
        "torrents.setDownloadPath",
    ],
)
def test_set_download_path(client, new_torrent, set_down_path_func, tmp_path):
    with pytest.raises(Forbidden403Error):
        client.func(set_down_path_func)(
            download_path="/etc/", torrent_hashes=new_torrent.hash
        )
    with pytest.raises(Conflict409Error):
        client.func(set_down_path_func)(
            download_path="/etc/asdf", torrent_hashes=new_torrent.hash
        )

    loc = mkpath(tmp_path, "savepath1")
    client.func(set_down_path_func)(download_path=loc, torrent_hashes=new_torrent.hash)
    # qBittorrent may return trailing separators depending on version....
    for attempt in eventually():
        with attempt:
            assert mkpath(new_torrent.info.download_path) == loc


@pytest.mark.parametrize(
    "set_cat_func",
    [
        "torrents_set_category",
        "torrents_setCategory",
        "torrents.set_category",
        "torrents.setCategory",
    ],
)
@pytest.mark.parametrize("name", ["awesome cat", "awesome_cat"])
def test_set_category(client, orig_torrent, set_cat_func, name):
    with pytest.raises(Conflict409Error):
        client.func(set_cat_func)(
            category="/!@#$%^&*(", torrent_hashes=orig_torrent.hash
        )

    client.torrents_create_category(name=name)
    try:
        client.func(set_cat_func)(category=name, torrent_hashes=orig_torrent.hash)
        for attempt in eventually():
            with attempt:
                assert orig_torrent.info.category.replace("+", " ") == name
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize(
    "set_auto_mgmt_func",
    [
        "torrents_set_auto_management",
        "torrents_setAutoManagement",
        "torrents.set_auto_management",
        "torrents.setAutoManagement",
    ],
)
def test_torrents_set_auto_management(client, orig_torrent, set_auto_mgmt_func):
    current_setting = orig_torrent.info.auto_tmm
    client.func(set_auto_mgmt_func)(
        enable=(not current_setting), torrent_hashes=orig_torrent.hash
    )
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.auto_tmm == (not current_setting)
    client.func(set_auto_mgmt_func)(
        enable=False, torrent_hashes=orig_torrent.hash
    )  # leave on False


@pytest.mark.parametrize(
    "set_comment_func",
    [
        "torrents_set_comment",
        "torrents_setComment",
        "torrents.set_comment",
        "torrents.setComment",
    ],
)
@pytest.mark.skipif_before_api_version("2.12.1")
def test_torrents_set_comment(client, orig_torrent, set_comment_func):
    client.func(set_comment_func)(
        comment="new comment", torrent_hashes=orig_torrent.hash
    )
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.comment == "new comment"
    client.func(set_comment_func)(comment="", torrent_hashes=orig_torrent.hash)
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.comment == ""


@pytest.mark.parametrize(
    "toggle_seq_down_func",
    [
        "torrents_toggle_sequential_download",
        "torrents_toggleSequentialDownload",
        "torrents.toggle_sequential_download",
        "torrents.toggleSequentialDownload",
    ],
)
def test_toggle_sequential_download(client, orig_torrent, toggle_seq_down_func):
    current_setting = orig_torrent.info.seq_dl
    client.func(toggle_seq_down_func)(torrent_hashes=orig_torrent.hash)
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.seq_dl == (not current_setting)


@pytest.mark.skipif_before_api_version("2.0.1")
@pytest.mark.parametrize(
    "toggle_piece_prio_func",
    [
        "torrents_toggle_first_last_piece_priority",
        "torrents_toggleFirstLastPiecePrio",
        "torrents.toggle_first_last_piece_priority",
        "torrents.toggleFirstLastPiecePrio",
    ],
)
def test_toggle_first_last_piece_priority(client, new_torrent, toggle_piece_prio_func):
    current_setting = new_torrent.info.f_l_piece_prio
    client.func(toggle_piece_prio_func)(torrent_hashes=new_torrent.hash)
    for attempt in eventually():
        with attempt:
            assert new_torrent.info.f_l_piece_prio == (not current_setting)


@pytest.mark.parametrize(
    "set_force_start_func",
    [
        "torrents_set_force_start",
        "torrents_setForceStart",
        "torrents.set_force_start",
        "torrents.setForceStart",
    ],
)
def test_set_force_start(client, orig_torrent, set_force_start_func):
    current_setting = orig_torrent.info.force_start
    client.func(set_force_start_func)(
        enable=(not current_setting), torrent_hashes=orig_torrent.hash
    )
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.force_start == (not current_setting)


@pytest.mark.parametrize(
    "set_super_seeding_func",
    [
        "torrents_set_super_seeding",
        "torrents_setSuperSeeding",
        "torrents.set_super_seeding",
        "torrents.setSuperSeeding",
    ],
)
def test_set_super_seeding(client, orig_torrent, set_super_seeding_func):
    # see tests/test_torrent.py::test_set_super_seeding for why the resulting
    # super seeding state isn't asserted here
    client.func(set_super_seeding_func)(enable=False, torrent_hashes=orig_torrent.hash)


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "add_peers_func",
    [
        "torrents_add_peers",
        "torrents_addPeers",
        "torrents.add_peers",
        "torrents.addPeers",
    ],
)
@pytest.mark.parametrize(
    "peers", ["127.0.0.1:5000", ["127.0.0.1:5000", "127.0.0.2:5000"], "127.0.0.1"]
)
def test_torrents_add_peers(client, orig_torrent, add_peers_func, peers):
    if all(":" not in p for p in peers):
        with pytest.raises(InvalidRequest400Error):
            client.func(add_peers_func)(peers=peers, torrent_hashes=orig_torrent.hash)
    else:
        p = client.func(add_peers_func)(peers=peers, torrent_hashes=orig_torrent.hash)
        assert isinstance(p, TorrentsAddPeersDictionary)


def _categories_save_path_key(api_version):
    """With qBittorrent 4.4.0 (Web API 2.8.4), the key in the category definition
    returned changed from savePath to save_path...."""
    if v(api_version) == v("2.8.4"):
        return "save_path"
    return "savePath"


@pytest.mark.skipif_before_api_version("2.1.1")
def test_categories1(client):
    assert isinstance(client.torrents_categories(), TorrentCategoriesDictionary)


@pytest.mark.skipif_before_api_version("2.1.1")
def test_categories2(client, api_version, tmp_path):
    save_path_key = _categories_save_path_key(api_version)
    name = "new_category"
    client.torrent_categories.categories = {"name": name, save_path_key: tmp_path}
    assert name in client.torrent_categories.categories
    client.torrent_categories.categories = {
        "name": name,
        save_path_key: mkpath(tmp_path, "new"),
    }
    assert mkpath(client.torrent_categories.categories[name][save_path_key]) == mkpath(
        tmp_path, "new"
    )
    client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize(
    "create_cat_func",
    ["torrents_create_category", "torrent_categories.create_category"],
)
@pytest.mark.parametrize("filepath", [None, "", "/tmp/"])
@pytest.mark.parametrize("name", ["name", "name 1"])
@pytest.mark.parametrize("enable_download_path", [None, True, False])
def test_create_categories(
    client,
    api_version,
    orig_torrent,
    create_cat_func,
    filepath,
    name,
    enable_download_path,
):
    save_path = download_path = filepath
    if filepath:
        save_path += "save"
        download_path += "download"

    try:
        client.func(create_cat_func)(
            name=name,
            save_path=save_path,
            download_path=download_path,
            enable_download_path=enable_download_path,
        )
        client.torrents_set_category(torrent_hashes=orig_torrent.hash, category=name)
        for attempt in eventually():
            with attempt:
                assert orig_torrent.info.category.replace("+", " ") == name
        if v(api_version) >= v("2.2"):
            for attempt in eventually():
                with attempt:
                    assert name in [
                        n.replace("+", " ") for n in client.torrents_categories()
                    ]
            save_path_key = _categories_save_path_key(api_version)
            for attempt in eventually():
                with attempt:
                    assert (mkpath(save_path) or "") in [
                        mkpath(cat[save_path_key])
                        for cat in client.torrents_categories().values()
                    ]
        if v(api_version) >= v("2.8.4") and enable_download_path is not False:
            for attempt in eventually():
                with attempt:
                    assert (mkpath(download_path) or "") in [
                        mkpath(cat.get("download_path", ""))
                        for cat in client.torrents_categories().values()
                    ]
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.skipif_before_api_version("2.1.0")
@pytest.mark.parametrize(
    "edit_cat_func", ["torrents_edit_category", "torrent_categories.edit_category"]
)
@pytest.mark.parametrize("filepath", ["", "/tmp/"])
@pytest.mark.parametrize("name", ["editcategory"])
@pytest.mark.parametrize("enable_download_path", [None, True, False])
def test_edit_category(
    client, api_version, edit_cat_func, filepath, name, enable_download_path
):
    try:
        client.torrents_create_category(
            name=name, save_path="/tmp/savetmp", download_path="/tmp/savetmp"
        )
        save_path = mkpath(filepath + "save/")
        download_path = mkpath(filepath + "down/")
        client.func(edit_cat_func)(
            name=name,
            save_path=save_path,
            download_path=download_path,
            enable_download_path=enable_download_path,
        )
        for attempt in eventually():
            with attempt:
                assert name in [
                    n.replace("+", " ") for n in client.torrents_categories()
                ]
        save_path_key = _categories_save_path_key(api_version)
        for attempt in eventually():
            with attempt:
                assert (mkpath(save_path) or "") in (
                    mkpath(cat[save_path_key])
                    for cat in client.torrents_categories().values()
                )
        if v(api_version) >= v("2.8.4") and enable_download_path is not False:
            for attempt in eventually():
                with attempt:
                    assert (mkpath(download_path) or "") in [
                        mkpath(cat.get("download_path", ""))
                        for cat in client.torrents_categories().values()
                    ]
    finally:
        client.torrents_remove_categories(categories=name)


@pytest.mark.parametrize(
    "remove_cat_func",
    ["torrents_remove_categories", "torrent_categories.remove_categories"],
)
@pytest.mark.parametrize("categories", [["category1"], ["category1", "category 2"]])
def test_remove_category(
    client, api_version, orig_torrent, remove_cat_func, categories
):
    for name in categories:
        client.torrents_create_category(name=name)
    orig_torrent.set_category(category=categories[0])
    client.func(remove_cat_func)(categories=categories)
    if v(api_version) >= v("2.2"):
        for attempt in eventually():
            with attempt:
                assert set(categories).isdisjoint(
                    {n.replace("+", " ") for n in client.torrents_categories()}
                )
    for attempt in eventually():
        with attempt:
            assert orig_torrent.info.category != categories[0]


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "tags_func",
    [
        "torrents_tags",
        "torrent_tags.tags",
    ],
)
def test_tags(client, tags_func):
    try:
        assert isinstance(client.func(tags_func)(), TagList)
    except TypeError:
        assert isinstance(client.func(tags_func), TagList)


@pytest.mark.skipif_before_api_version("2.3.0")
def test_tags_slice(client):
    assert isinstance(client.torrents_tags()[1:2], TagList)


@pytest.mark.skipif_before_api_version("2.3.0")
def test_add_tag_though_property(client):
    name = "newtag"
    client.torrent_tags.tags = name
    assert name in client.torrent_tags.tags
    client.torrent_tags.delete_tags(name)
    assert name not in client.torrent_tags.tags


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "add_tags_func", ["torrents_add_tags", "torrent_tags.add_tags"]
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_add_tags(client, orig_torrent, add_tags_func, tags):
    try:
        client.func(add_tags_func)(tags=tags, torrent_hashes=orig_torrent.hash)
        for attempt in eventually():
            with attempt:
                assert all(tag in orig_torrent.info.tags for tag in tags)
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_before_api_version("2.11.4")
@pytest.mark.parametrize(
    "set_tags_func", ["torrents_set_tags", "torrent_tags.set_tags"]
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_set_tags(client, orig_torrent, set_tags_func, tags):
    try:
        client.torrents_add_tags(tags="extra-tag", torrent_hashes=orig_torrent.hash)
        client.func(set_tags_func)(tags=tags, torrent_hashes=orig_torrent.hash)
        for attempt in eventually():
            with attempt:
                assert all(tag in orig_torrent.info.tags for tag in tags)
    finally:
        client.torrents_delete_tags(tags=[*tags, "extra-tag"])


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "remove_tags_func", ["torrents_remove_tags", "torrent_tags.remove_tags"]
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_remove_tags(client, orig_torrent, remove_tags_func, tags):
    try:
        orig_torrent.add_tags(tags=tags)
        client.func(remove_tags_func)(tags=tags, torrent_hashes=orig_torrent.hash)
        for attempt in eventually():
            with attempt:
                assert all(tag not in orig_torrent.info.tags for tag in tags)
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "create_tags_func", ["torrents_create_tags", "torrent_tags.create_tags"]
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_create_tags(client, create_tags_func, tags):
    try:
        client.func(create_tags_func)(tags=tags)
        for attempt in eventually():
            with attempt:
                assert set(tags) <= set(client.torrents_tags())
    finally:
        client.torrents_delete_tags(tags=tags)


@pytest.mark.skipif_before_api_version("2.3.0")
@pytest.mark.parametrize(
    "delete_tags_func", ["torrents_delete_tags", "torrent_tags.delete_tags"]
)
@pytest.mark.parametrize("tags", [["tag1"], ["tag1", "tag 2"]])
def test_delete_tags(client, delete_tags_func, tags):
    client.torrents_create_tags(tags=tags)
    client.func(delete_tags_func)(tags=tags)
    for attempt in eventually():
        with attempt:
            assert set(tags).isdisjoint(client.torrents_tags())
