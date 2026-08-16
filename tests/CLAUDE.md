# Working on this test suite

This suite tests a client for qBittorrent's Web API. Most of it runs against a
real qBittorrent, which shapes nearly every rule below. Read this before adding
or changing tests.

## You need a running qBittorrent

Start the same container CI uses:

```bash
docker run --rm -d --name qbt-tox-testing --publish 8080:8080 \
  --volume "$PWD/tests/_resources:/tmp/_resources" \
  ghcr.io/rmartin16/qbittorrent-nox:master-debug
```

Then run the suite:

```bash
python -m pytest                      # everything
python -m pytest tests/test_torrents.py -k webseed   # a slice
tox -e py                             # starts and stops the container for you
```

This is not optional, even for tests that never make a request: `setup_environ()`
in `tests/utils.py` contacts qBittorrent while `conftest.py` is being imported,
so *collection* fails without it.

**Never run two pytest sessions against one qBittorrent.** The session fixture
rewrites application preferences and adds torrents; two sessions will corrupt
each other's state and produce failures that look like real bugs.

## Two kinds of test

**Offline** — `tests/test_api_surface.py`, derived from `tests/catalog.py`. These
inspect the library itself and never talk to qBittorrent. They carry the
`offline` marker, are generated from all 128 endpoints in the catalog, and
finish in well under a second.

**Live** — everything else. These make real requests and assert on what
qBittorrent actually did.

Put a new test in the offline layer if it asserts something true regardless of
which qBittorrent is running: which names an endpoint is reachable under, what
version range it declares, what type it returns. Put it in the live layer if it
asserts that a request *changed something*.

## If you add or change an endpoint, regenerate the snapshot

```bash
python -m tests.catalog > tests/api_surface.json
```

`tests/api_surface.json` is a checked-in snapshot of the API surface, and
`test_catalog_matches_snapshot` fails until it is regenerated. This is
intentional, not an obstacle: the catalog is derived from the source, so it
cannot by itself notice a `version_introduced` constant being changed by
mistake — the expectation would move along with the change. The snapshot is the
second copy that makes such an edit visible in review. Regenerate it
deliberately and check the diff is what you meant.

## Do not mock qBittorrent in live tests

The point of the live layer is that qBittorrent really behaves this way.
Replacing requests with `unittest.mock` deletes the only thing those tests
verify. If a live test is hard to write, fix the fixture, do not mock it.

Pinning versions *is* allowed in the offline layer, where the subject is the
library's own logic:

```python
monkeypatch.setattr(client, "app_web_api_version", MagicMock(return_value="0.0.1"))
```

## qBittorrent applies changes asynchronously

A request that returns 200 has not necessarily taken effect yet, so a bare
assert immediately after a mutation is a flake waiting to happen. Use `check()`
from `tests/utils.py`, which re-reads the value until it matches or the timeout
expires.

Worse, qBittorrent sometimes drops a request entirely — webseed changes run in
worker threads that swallow every exception, and some setters return early when
qBittorrent's own cached state already looks correct. For those, pass
`action=`, which re-sends the request between attempts:

```python
def add_webseeds():
    torrent.add_webseeds(urls=urls)

add_webseeds()
check(lambda: [w.url for w in torrent.webseeds], urls, reverse=True,
      action=add_webseeds)
```

Only use `action=` for requests that are safe to send more than once.

Note that `check()` lives outside a test module, so pytest does **not** rewrite
its assertions. Any new assertion helper there must put the offending values in
its own failure message, or failures will be undebuggable.

## Tests share one qBittorrent, so clean up

Anything a test creates — torrents, categories, tags, RSS feeds — outlives it
and will confuse whatever runs next. Use the existing fixtures rather than
hand-rolling setup:

- `client` — session-scoped, authenticated
- `orig_torrent` — a torrent present for the whole session; re-synced per test
- `new_torrent` — added for one test, removed afterwards
- `new_torrent_standalone()` — same, as a context manager, when you need options

Clean up in a `finally` block so a mid-test failure still tidies up.

## Version gating

Endpoints exist only in some Web API versions. Skip accordingly:

```python
@pytest.mark.skipif_before_api_version("2.11.3")
@pytest.mark.skipif_after_api_version("2.11.3")
```

CI runs the suite against qBittorrent versions back to v4.1.0, so a test without
the right marker will fail there even though it passes locally against master.

**Do not write a `*_not_implemented` test for a new endpoint.** The offline layer
already asserts, for every gated endpoint, that it raises `NotImplementedError`
below the version it was introduced in — through the client method *and* its
interface spelling — and that it stops raising at that version. Writing one by
hand adds a live request that proves something already proven.

The `*_not_implemented` tests that remain cover methods on torrent objects, such
as `torrent.set_comment()`. That surface is not in the catalog yet, so those are
still carrying their own weight.

## Gotchas that have cost real time

- **camelCase spellings are the same function object.** `torrents_addWebSeeds`
  *is* `torrents_add_webseeds`, assigned, not reimplemented. 92 of the 128
  endpoints have at least one alias, 94 alias bindings in all. Do not add live
  tests per spelling; the offline layer asserts the identity for every endpoint
  already.
- **`torrents_rename_folder` gates on the application version**, not the Web API
  version, because v4.3.2 and v4.3.3 both report Web API v2.7. Pin both versions
  when writing generic tests over endpoints.
- **`--doctest-modules` is enabled**, so every module under `tests/` is imported
  and its docstrings are executed as doctests. Do not write a docstring example
  that looks like a doctest unless you mean it.
- **Some tests fail against master dev builds.** Before assuming you broke
  something, stash your change and confirm whether the failure is already there.
  The RSS fixture in particular fetches a feed over the network and errors when
  that fetch or the refresh is slow.
- **The Release Tests workflow sets `continue-on-error`**, so a run's overall
  conclusion can be "success" while test jobs failed. Check the job
  conclusions, not the run's.
