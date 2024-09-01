import sys
from contextlib import suppress
from time import sleep

import pytest

from qbittorrentapi import APINames
from qbittorrentapi._version_support import v
from qbittorrentapi.exceptions import APIError, Conflict409Error
from qbittorrentapi.rss import RSSitemsDictionary
from tests.utils import check, retry

FOLDER_ONE = "testFolderOne"
FOLDER_TWO = "testFolderTwo"

ITEM_ONE = "RSSOne"
ITEM_TWO = "RSSTwo"
RSS_NAME = "DistroWatch - Torrents"
RSS_URL = (
    "https://gist.githubusercontent.com/rmartin16/"
    "d615e1066f54186b44e8018d31af18f1/raw/b59cdc878fedfaf08efe6fc4321d18e8ded01e09/rss.xml"
)


@retry(3)
def delete_feed(client, name):
    with suppress(Conflict409Error):
        client.rss_remove_item(item_path=name)
        check(lambda: client.rss_items(), name, reverse=True, negate=True)


@pytest.fixture(scope="function", autouse=True)
def rss_feed(client, api_version):
    if v(api_version) >= v("2.2"):
        try:
            client.app.preferences = dict(rss_auto_downloading_enabled=False)
            # refreshing the feed is finicky...so try several times if necessary
            done = False
            for i in range(5):
                delete_feed(client, ITEM_ONE)
                delete_feed(client, RSS_NAME)
                client.rss.add_feed(url=RSS_URL, item_path=ITEM_ONE)
                check(lambda: client.rss_items(), ITEM_ONE, reverse=True)
                # wait until feed is refreshed
                for j in range(20):
                    if client.rss.items.with_data[ITEM_ONE]["articles"]:
                        done = True
                        yield ITEM_ONE
                        break
                    sleep(0.25)
                if done:
                    break
            else:
                raise Exception(f"RSS Feed '{ITEM_ONE}' did not refresh...")
        finally:
            delete_feed(client, ITEM_ONE)
            delete_feed(client, RSS_NAME)
    else:
        yield ""


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    namespace = APINames.RSS
    all_dotted_methods = set(dir(getattr(client, namespace)))

    for meth in [meth for meth in dir(client) if meth.startswith(f"{namespace}_")]:
        assert meth.removeprefix(f"{namespace}_") in all_dotted_methods


@pytest.mark.skipif_before_api_version("2.2.1")
@pytest.mark.parametrize(
    "refresh_item_func",
    ["rss_refresh_item", "rss_refreshItem", "rss.refresh_item", "rss.refreshItem"],
)
def test_rss_refresh_item(client, rss_feed, refresh_item_func):
    last_log_id = client.log.main()[-1].id

    client.func(refresh_item_func)(item_path=rss_feed)

    check(
        lambda: [e.message for e in client.log.main(last_known_id=last_log_id)],
        f"RSS feed at '{RSS_URL}' updated. Added 0 new articles.",
        reverse=True,
    )


# inconsistent behavior with endpoint for API version 2.2
@pytest.mark.skipif_after_api_version("2.2")
@pytest.mark.parametrize(
    "refresh_item_func",
    ["rss_refresh_item", "rss_refreshItem", "rss.refresh_item", "rss.refreshItem"],
)
def test_rss_refresh_item_not_implemented(client, refresh_item_func):
    with pytest.raises(NotImplementedError):
        client.func(refresh_item_func)()


@pytest.mark.skipif_before_api_version("2.2")
@pytest.mark.parametrize("items_func", ["rss_items", "rss.items"])
def test_rss_items(client, rss_feed, items_func):
    check(lambda: client.func(items_func)(), rss_feed, reverse=True)
    check(
        lambda: client.func(items_func)(include_feed_data=True),
        rss_feed,
        reverse=True,
    )
    check(
        lambda: client.func(items_func)(include_feed_data=True)[rss_feed],
        "articles",
        reverse=True,
    )

    if "." in items_func:
        check(
            lambda: client.func(items_func).without_data,
            rss_feed,
            reverse=True,
        )
        check(
            lambda: client.func(items_func).with_data[rss_feed],
            "articles",
            reverse=True,
        )


# disabling as failures are too common...
# @pytest.mark.skipif_before_api_version("2.2")
# @pytest.mark.parametrize(
#     "add_feed_func", ["rss_add_feed", "rss_addFeed", "rss.add_feed", "rss.addFeed"]
# )
# @pytest.mark.parametrize(
#     "feed_url, path", [(RSS_URL, "/path/my-feed"), (RSS_URL, "")]
# )
# def test_rss_add_feed(client, add_feed_func, feed_url, path):
#     @retry(5)
#     def run_test():
#         delete_feed(client, ITEM_ONE)
#         delete_feed(client, RSS_NAME)
#
#         try:
#             client.func(add_feed_func)(url=feed_url, item_path=path)
#             check(lambda: client.rss_items(), path or feed_url, reverse=True)
#         finally:
#             delete_feed(client, path or feed_url)
#             delete_feed(client, RSS_NAME)
#
#     run_test()


@pytest.mark.skipif_before_api_version("2.9.1")
@pytest.mark.parametrize(
    "set_feed_func",
    ["rss_set_feed_url", "rss_setFeedURL", "rss.set_feed_url", "rss.setFeedURL"],
)
def test_rss_set_feed_url(client, rss_feed, set_feed_func):
    curr_feed_url = client.rss_items()[rss_feed].url
    new_feed_url = curr_feed_url + "asdf"
    client.func(set_feed_func)(url=new_feed_url, item_path=rss_feed)
    assert new_feed_url == client.rss_items()[rss_feed].url


@pytest.mark.skipif_after_api_version("2.9.1")
@pytest.mark.parametrize(
    "set_feed_func",
    ["rss_set_feed_url", "rss_setFeedURL", "rss.set_feed_url", "rss.setFeedURL"],
)
def test_rss_set_feed_url_not_implemented(client, set_feed_func):
    with pytest.raises(NotImplementedError):
        client.func(set_feed_func)()


@pytest.mark.skipif_before_api_version("2.2")
@pytest.mark.parametrize(
    "remove_item_func",
    ["rss_remove_item", "rss_removeItem", "rss.remove_item", "rss.removeItem"],
)
def test_rss_remove_feed(client, rss_feed, remove_item_func):
    client.func(remove_item_func)(item_path=rss_feed)
    check(lambda: client.rss_items(), rss_feed, reverse=True, negate=True)


@pytest.mark.parametrize(
    "add_folder_func, remove_item_func",
    [
        ("rss_add_folder", "rss_remove_item"),
        ("rss_addFolder", "rss_removeItem"),
        ("rss.add_folder", "rss.remove_item"),
        ("rss.addFolder", "rss.removeItem"),
    ],
)
def test_rss_add_remove_folder(client, add_folder_func, remove_item_func):
    name = "test_isos"

    client.func(add_folder_func)(folder_path=name)
    check(lambda: client.rss_items(), name, reverse=True)
    client.func(remove_item_func)(item_path=name)
    check(lambda: client.rss_items(), name, reverse=True, negate=True)


@pytest.mark.skipif_before_api_version("2.2")
@pytest.mark.parametrize(
    "move_func", ["rss_move_item", "rss_moveItem", "rss.move_item", "rss.moveItem"]
)
def test_rss_move(client, rss_feed, move_func):
    new_name = "new_loc"
    try:
        client.func(move_func)(orig_item_path=rss_feed, new_item_path=new_name)
        check(lambda: client.rss_items(), new_name, reverse=True)
    finally:
        with suppress(APIError):
            client.rss_remove_item(item_path=new_name)


@pytest.mark.skipif_before_api_version("2.5.1")
@pytest.mark.parametrize(
    "mark_read_func",
    ["rss_mark_as_read", "rss_markAsRead", "rss.mark_as_read", "rss.markAsRead"],
)
def test_rss_mark_as_read(client, rss_feed, mark_read_func):
    item_id = client.rss.items.with_data[rss_feed]["articles"][0]["id"]
    client.func(mark_read_func)(item_path=rss_feed, article_id=item_id)
    check(
        lambda: client.rss.items.with_data[rss_feed]["articles"][0],
        "isRead",
        reverse=True,
    )


@pytest.mark.skipif_after_api_version("2.5.1")
@pytest.mark.parametrize(
    "mark_read_func",
    ["rss_mark_as_read", "rss_markAsRead", "rss.mark_as_read", "rss.markAsRead"],
)
def test_rss_mark_as_read_not_implemented(client, mark_read_func):
    with pytest.raises(NotImplementedError):
        client.func(mark_read_func)()


@pytest.mark.skipif_before_api_version("2.2")
@pytest.mark.parametrize(
    "set_rule_func, rules_func, rename_rule_func, "
    "matching_func, remove_rule_func, remove_item_func",
    (
        (
            "rss_set_rule",
            "rss_rules",
            "rss_rename_rule",
            "rss_matching_articles",
            "rss_remove_rule",
            "rss_remove_item",
        ),
        (
            "rss_setRule",
            "rss_rules",
            "rss_renameRule",
            "rss_matchingArticles",
            "rss_removeRule",
            "rss_removeItem",
        ),
        (
            "rss.set_rule",
            "rss.rules",
            "rss.rename_rule",
            "rss.matching_articles",
            "rss.remove_rule",
            "rss.remove_item",
        ),
        (
            "rss.setRule",
            "rss.rules",
            "rss.renameRule",
            "rss.matchingArticles",
            "rss.removeRule",
            "rss.removeItem",
        ),
    ),
)
def test_rss_rules(
    client,
    api_version,
    set_rule_func,
    rules_func,
    rename_rule_func,
    matching_func,
    remove_rule_func,
    remove_item_func,
):
    def check_for_rule(name):
        try:
            client.func(rules_func)()
            check(lambda: client.func(rules_func)(), name, reverse=True)
        except TypeError:
            check(lambda: client.func(rules_func), name, reverse=True)

    rule_name = ITEM_ONE + "Rule"
    rule_name_new = rule_name + "New"
    rule_def = {"enabled": True, "affectedFeeds": RSS_URL, "addPaused": True}
    try:
        client.func(set_rule_func)(rule_name=rule_name, rule_def=rule_def)
        check_for_rule(rule_name)

        if v(api_version) >= v("2.6"):  # rename was broken for a bit
            client.func(rename_rule_func)(
                orig_rule_name=rule_name, new_rule_name=rule_name_new
            )
            check_for_rule(rule_name_new)
        if v(api_version) >= v("2.5.1"):
            assert isinstance(
                client.func(matching_func)(rule_name=rule_name), RSSitemsDictionary
            )
        else:
            with pytest.raises(NotImplementedError):
                client.func(matching_func)(rule_name=rule_name)
    finally:
        client.func(remove_rule_func)(rule_name=rule_name)
        client.func(remove_rule_func)(rule_name=rule_name_new)
        check(lambda: client.rss_rules(), rule_name, reverse=True, negate=True)
        client.func(remove_item_func)(item_path=ITEM_ONE)
        assert ITEM_TWO not in client.rss_items()
        check(lambda: client.rss_items(), ITEM_TWO, reverse=True, negate=True)


@pytest.mark.skipif_after_api_version("2.2")
@pytest.mark.parametrize(
    "matching_func",
    [
        "rss_matching_articles",
        "rss_matchingArticles",
        "rss.matching_articles",
        "rss.matchingArticles",
    ],
)
def test_rss_rules_not_implemented(client, matching_func):
    with pytest.raises(NotImplementedError):
        client.func(matching_func)()
