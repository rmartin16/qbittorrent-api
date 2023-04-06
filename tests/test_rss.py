from time import sleep

import pytest

from qbittorrentapi._version_support import v
from qbittorrentapi.exceptions import APIError
from qbittorrentapi.rss import RSSitemsDictionary
from tests.conftest import check
from tests.conftest import get_func

folder_one = "testFolderOne"
folder_two = "testFolderTwo"

item_one = "YTS"
item_two = "YTSNew"
url = "https://yts.mx/rss/0/all/all/0/en"


@pytest.mark.parametrize(
    "client_func",
    ["rss_refresh_item", "rss_refreshItem", "rss.refresh_item", "rss.refreshItem"],
)
def test_refresh_item(client, api_version, rss_feed, client_func):
    if v(api_version) >= v("2.2"):
        get_func(client, client_func)(item_path=rss_feed)
        check(
            lambda: client.rss_items(include_feed_data=True)[rss_feed]["lastBuildDate"],
            "",
            negate=True,
            check_limit=20,
        )
        last_refresh = client.rss_items(include_feed_data=True)[rss_feed][
            "lastBuildDate"
        ]
        sleep(1)
        get_func(client, client_func)(item_path=rss_feed)
        check(
            lambda: client.rss_items(include_feed_data=True)[rss_feed]["lastBuildDate"],
            last_refresh,
            negate=True,
            check_limit=20,
        )
    else:
        with pytest.raises(NotImplementedError):
            client.rss_refresh_item(item_path=rss_feed)


@pytest.mark.parametrize("client_func", ["rss_items", "rss.items"])
def test_items(client, api_version, rss_feed, client_func):
    if v(api_version) >= v("2.2"):
        check(lambda: get_func(client, client_func)(), rss_feed, reverse=True)
        check(
            lambda: get_func(client, client_func)(include_feed_data=True),
            rss_feed,
            reverse=True,
        )
        check(
            lambda: get_func(client, client_func)(include_feed_data=True)[rss_feed],
            "articles",
            reverse=True,
        )

        if "." in client_func:
            check(
                lambda: get_func(client, client_func).without_data,
                rss_feed,
                reverse=True,
            )
            check(
                lambda: get_func(client, client_func).with_data[rss_feed],
                "articles",
                reverse=True,
            )


@pytest.mark.parametrize("client_func", ["rss_items", "rss.items"])
def test_add_feed(client, api_version, rss_feed, client_func):
    if v(api_version) >= v("2.2"):
        assert rss_feed in get_func(client, client_func)()


@pytest.mark.parametrize(
    "client_func",
    ["rss_set_feed_url", "rss_setFeedURL", "rss.set_feed_url", "rss.setFeedURL"],
)
def test_set_feed_url(client, api_version, rss_feed, client_func):
    if v(api_version) >= v("2.9.1"):
        curr_feed_url = client.rss_items()[rss_feed].url
        new_feed_url = curr_feed_url + "asdf"
        get_func(client, client_func)(url=new_feed_url, item_path=rss_feed)
        assert new_feed_url == client.rss_items()[rss_feed].url
    else:
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)()


@pytest.mark.parametrize(
    "client_func",
    ["rss_remove_item", "rss_removeItem", "rss.remove_item", "rss.removeItem"],
)
def test_remove_feed(client, api_version, rss_feed, client_func):
    if v(api_version) >= v("2.2"):
        get_func(client, client_func)(item_path=rss_feed)
        check(lambda: client.rss_items(), rss_feed, reverse=True, negate=True)


@pytest.mark.parametrize(
    "client_func",
    [
        ("rss_add_folder", "rss_remove_item"),
        ("rss_addFolder", "rss_removeItem"),
        ("rss.add_folder", "rss.remove_item"),
        ("rss.addFolder", "rss.removeItem"),
    ],
)
def test_add_remove_folder(client, api_version, client_func):
    name = "test_isos"

    get_func(client, client_func[0])(folder_path=name)  # add_folder
    check(lambda: client.rss_items(), name, reverse=True)
    get_func(client, client_func[1])(item_path=name)  # remove_folder
    check(lambda: client.rss_items(), name, reverse=True, negate=True)


@pytest.mark.parametrize(
    "client_func", ["rss_move_item", "rss_moveItem", "rss.move_item", "rss.moveItem"]
)
def test_move(client, api_version, rss_feed, client_func):
    if v(api_version) >= v("2.2"):
        try:
            new_name = "new_loc"
            get_func(client, client_func)(
                orig_item_path=rss_feed, new_item_path=new_name
            )
            check(lambda: client.rss_items(), new_name, reverse=True)
        finally:
            try:
                client.rss_remove_item(item_path=new_name)
            except APIError:
                pass


@pytest.mark.parametrize(
    "client_func",
    ["rss_mark_as_read", "rss_markAsRead", "rss.mark_as_read", "rss.markAsRead"],
)
def test_mark_as_read(client, api_version, rss_feed, client_func):
    if v(api_version) >= v("2.5.1"):
        item_id = client.rss.items.with_data[rss_feed]["articles"][0]["id"]
        get_func(client, client_func)(item_path=rss_feed, article_id=item_id)
        check(
            lambda: client.rss.items.with_data[rss_feed]["articles"][0],
            "isRead",
            reverse=True,
        )
    else:
        with pytest.raises(NotImplementedError):
            get_func(client, client_func)(item_path=rss_feed, article_id=1)


@pytest.mark.parametrize(
    "client_func",
    (
        (
            "rss_add_feed",
            "rss_set_rule",
            "rss_rules",
            "rss_rename_rule",
            "rss_matching_articles",
            "rss_remove_rule",
            "rss_remove_item",
        ),
        (
            "rss_addFeed",
            "rss_setRule",
            "rss_rules",
            "rss_renameRule",
            "rss_matchingArticles",
            "rss_removeRule",
            "rss_removeItem",
        ),
        (
            "rss.add_feed",
            "rss.set_rule",
            "rss.rules",
            "rss.rename_rule",
            "rss.matching_articles",
            "rss.remove_rule",
            "rss.remove_item",
        ),
        (
            "rss.addFeed",
            "rss.setRule",
            "rss.rules",
            "rss.renameRule",
            "rss.matchingArticles",
            "rss.removeRule",
            "rss.removeItem",
        ),
    ),
)
def test_rules(client, api_version, client_func, rss_feed):
    def check_for_rule(name):
        try:
            get_func(client, client_func[2])()  # rss_rules
            check(
                lambda: get_func(client, client_func[2])(), name, reverse=True
            )  # rss_rules
        except TypeError:
            check(
                lambda: get_func(client, client_func[2]), name, reverse=True
            )  # rss_rules

    if v(api_version) >= v("2.2"):
        _ = rss_feed  # reference to avoid errors; needed to load RSS feed in to qbt
        rule_name = item_one + "Rule"
        rule_name_new = rule_name + "New"
        rule_def = {"enabled": True, "affectedFeeds": url, "addPaused": True}
        try:
            # rss_set_rule
            get_func(client, client_func[1])(rule_name=rule_name, rule_def=rule_def)
            check_for_rule(rule_name)

            if v(api_version) >= v("2.6"):  # rename was broken for a bit
                get_func(client, client_func[3])(
                    orig_rule_name=rule_name, new_rule_name=rule_name_new
                )  # rss_rename_rule
                check_for_rule(rule_name_new)
            if v(api_version) >= v("2.5.1"):
                assert isinstance(
                    get_func(client, client_func[4])(rule_name=rule_name),
                    RSSitemsDictionary,
                )  # rss_matching_articles
            else:
                with pytest.raises(NotImplementedError):
                    get_func(client, client_func[4])(
                        rule_name=rule_name
                    )  # rss_matching_articles
        finally:
            get_func(client, client_func[5])(rule_name=rule_name)  # rss_remove_rule
            get_func(client, client_func[5])(rule_name=rule_name_new)  # rss_remove_rule
            check(lambda: client.rss_rules(), rule_name, reverse=True, negate=True)
            get_func(client, client_func[6])(item_path=item_one)  # rss_remove_item
            assert item_two not in client.rss_items()
            check(lambda: client.rss_items(), item_two, reverse=True, negate=True)
    else:
        with pytest.raises(NotImplementedError):
            get_func(client, client_func[4])()  # matching_articles
