from time import sleep

import pytest

from qbittorrentapi.rss import RSSitemsDictionary
from tests.conftest import is_version_less_than, check, get_func

folder_one = "testFolderOne"
folder_two = "testFolderTwo"

item_one = "YTS1080p"
item_two = "YTS1080pNew"
url = "https://yts.mx/rss/"


def test_refresh_item(client, api_version, rss_feed):
    if is_version_less_than(api_version, "2.2", lteq=False):
        with pytest.raises(NotImplementedError):
            client.rss_refresh_item(item_path=rss_feed)
    else:
        # client.rss_refresh_item(item_path=rss_feed)
        check(
            lambda: client.rss_items(include_feed_data=True)[rss_feed]["lastBuildDate"],
            "",
            negate=True,
        )
        last_refresh = client.rss_items(include_feed_data=True)[rss_feed][
            "lastBuildDate"
        ]
        sleep(1)
        client.rss_refresh_item(item_path=rss_feed)
        check(
            lambda: client.rss_items(include_feed_data=True)[rss_feed]["lastBuildDate"],
            last_refresh,
            negate=True,
        )

    if is_version_less_than(api_version, "2.2", lteq=False):
        with pytest.raises(NotImplementedError):
            client.rss.refresh_item(item_path=rss_feed)
    else:
        client.rss.refresh_item(item_path=rss_feed)
        check(
            lambda: client.rss_items(include_feed_data=True)[rss_feed]["lastBuildDate"],
            "",
            negate=True,
        )
        last_refresh = client.rss_items(include_feed_data=True)[rss_feed][
            "lastBuildDate"
        ]
        sleep(1)
        client.rss.refresh_item(item_path=rss_feed)
        check(
            lambda: client.rss_items(include_feed_data=True)[rss_feed]["lastBuildDate"],
            last_refresh,
            negate=True,
        )


def test_items(client, rss_feed):
    check(lambda: client.rss_items(), rss_feed, reverse=True)
    check(lambda: client.rss_items(include_feed_data=True), rss_feed, reverse=True)
    check(
        lambda: client.rss_items(include_feed_data=True)[rss_feed],
        "articles",
        reverse=True,
    )

    check(lambda: client.rss.items(), rss_feed, reverse=True)
    check(lambda: client.rss.items.without_data, rss_feed, reverse=True)
    check(lambda: client.rss.items.with_data[rss_feed], "articles", reverse=True)


def test_add_feed(client, rss_feed):
    if rss_feed not in client.rss_items():
        raise Exception("rss feed not found", client.rss_items())


def test_remove_feed1(client, rss_feed):
    client.rss_remove_item(item_path=rss_feed)
    check(lambda: client.rss_items(), rss_feed, reverse=True, negate=True)


def test_remove_feed2(client, rss_feed):
    client.rss.remove_item(item_path=rss_feed)
    check(lambda: client.rss_items(), rss_feed, reverse=True, negate=True)


def test_add_remove_folder(client):
    name = "test_isos"

    client.rss_add_folder(folder_path=name)
    check(lambda: client.rss_items(), name, reverse=True)
    client.rss_remove_item(item_path=name)
    check(lambda: client.rss_items(), name, reverse=True, negate=True)

    client.rss.add_folder(folder_path=name)
    check(lambda: client.rss.items(), name, reverse=True)
    client.rss.remove_item(item_path=name)
    check(lambda: client.rss.items(), name, reverse=True, negate=True)


def test_move(client, rss_feed):
    new_name = "new_loc"

    client.rss_move_item(orig_item_path=rss_feed, new_item_path=new_name)
    check(lambda: client.rss_items(), new_name, reverse=True)

    client.rss.move_item(orig_item_path=new_name, new_item_path=rss_feed)
    check(lambda: client.rss.items(), rss_feed, reverse=True)


def test_mark_as_read(client, api_version, rss_feed):
    item_id = client.rss.items.with_data[rss_feed]["articles"][0]["id"]
    if is_version_less_than(api_version, "2.5.1", lteq=False):
        with pytest.raises(NotImplementedError):
            client.rss_mark_as_read(item_path=rss_feed, article_id=item_id)
    else:
        client.rss_mark_as_read(item_path=rss_feed, article_id=item_id)
        check(
            lambda: client.rss.items.with_data[rss_feed]["articles"][0],
            "isRead",
            reverse=True,
        )

    item_id = client.rss.items.with_data[rss_feed]["articles"][1]["id"]
    if is_version_less_than(api_version, "2.5.1", lteq=False):
        with pytest.raises(NotImplementedError):
            client.rss.mark_as_read(item_path=rss_feed, article_id=item_id)
    else:
        client.rss.mark_as_read(item_path=rss_feed, article_id=item_id)
        check(
            lambda: client.rss.items.with_data[rss_feed]["articles"][1],
            "isRead",
            reverse=True,
        )


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
            "rss.add_feed",
            "rss.set_rule",
            "rss.rules",
            "rss.rename_rule",
            "rss.matching_articles",
            "rss.remove_rule",
            "rss.remove_item",
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

    _ = rss_feed  # reference to avoid errors; needed to load RSS feed in to qbt
    rule_name = item_one + "Rule"
    rule_name_new = rule_name + "New"
    rule_def = {"enabled": True, "affectedFeeds": url, "addPaused": True}
    try:
        get_func(client, client_func[1])(
            rule_name=rule_name, rule_def=rule_def
        )  # rss_set_rule
        check_for_rule(rule_name)

        if is_version_less_than(
            "2.6", api_version, lteq=True
        ):  # rename was broken in qBittorrent for a period
            get_func(client, client_func[3])(
                orig_rule_name=rule_name, new_rule_name=rule_name_new
            )  # rss_rename_rule
            check_for_rule(rule_name_new)
        if is_version_less_than(api_version, "2.5.1", lteq=False):
            with pytest.raises(NotImplementedError):
                get_func(client, client_func[4])(
                    rule_name=rule_name
                )  # rss_matching_articles
        else:
            assert isinstance(
                get_func(client, client_func[4])(rule_name=rule_name),
                RSSitemsDictionary,
            )  # rss_matching_articles
    finally:
        get_func(client, client_func[5])(rule_name=rule_name)  # rss_remove_rule
        get_func(client, client_func[5])(rule_name=rule_name_new)  # rss_remove_rule
        check(lambda: client.rss_rules(), rule_name, reverse=True, negate=True)
        get_func(client, client_func[6])(item_path=item_one)  # rss_remove_item
        assert item_two not in client.rss_items()
        check(lambda: client.rss_items(), item_two, reverse=True, negate=True)
