from time import sleep

import pytest

from qbittorrentapi.helpers import is_version_less_than
from qbittorrentapi.rss import RSSitemsDictionary

folder_one = 'testFolderOne'
folder_two = 'testFolderTwo'

item_one = 'YTS1080p'
item_two = 'YTS1080pNew'
url = 'https://yts.mx/rss/0/1080p/all/0'


def test_add_remove_folder(client):
    client.rss_add_folder(folder_path=folder_one)
    assert folder_one in client.rss_items()
    client.rss_remove_item(item_path=folder_one)
    assert folder_one not in client.rss_items()

    client.rss.add_folder(folder_path=folder_two)
    assert folder_two in client.rss.items()
    client.rss.remove_item(item_path=folder_two)
    assert folder_two not in client.rss.items()


def test_add_move_refresh_remove_feed(client, api_version):
    try:
        client.rss_add_feed(item_path=item_one, url=url)
        sleep(1)
        assert item_one in client.rss_items()
        client.rss_move_item(orig_item_path=item_one, new_item_path=item_two)
        sleep(1)
        assert item_two in client.rss_items()
        if is_version_less_than(api_version, '2.2', lteq=False):
            with pytest.raises(NotImplementedError):
                client.rss_refresh_item(item_path=item_two)
        else:
            client.rss_refresh_item(item_path=item_two)
            sleep(2)
        items = client.rss_items(include_feed_data=True)
        assert isinstance(items, RSSitemsDictionary)
        if is_version_less_than(api_version, '2.5.1', lteq=False):
            with pytest.raises(NotImplementedError):
                client.rss_mark_as_read()
        else:
            if items[item_two]['articles']:
                client.rss_mark_as_read(item_path=item_two, article_id=items[item_two]['articles'][0])
    finally:
        client.rss_remove_item(item_path=item_two)
        sleep(1)
        assert item_two not in client.rss_items()

    try:
        client.rss.add_feed(item_path=item_one, url=url)
        sleep(1)
        assert item_one in client.rss.items()
        client.rss.move_item(orig_item_path=item_one, new_item_path=item_two)
        sleep(1)
        assert item_two in client.rss.items()
        if is_version_less_than(api_version, '2.2', lteq=False):
            with pytest.raises(NotImplementedError):
                client.rss.refresh_item(item_path=item_two)
        else:
            client.rss.refresh_item(item_path=item_two)
            sleep(2)
            items = client.rss.items(include_feed_data=False)
            assert isinstance(items, RSSitemsDictionary)
            items = client.rss.items.without_data
            assert isinstance(items, RSSitemsDictionary)
            items = client.rss.items.with_data
            if is_version_less_than(api_version, '2.5.1', lteq=False):
                with pytest.raises(NotImplementedError):
                    client.rss.mark_as_read()
            else:
                if items[item_two]['articles']:
                    client.rss.mark_as_read(item_path=item_two, article_id=items[item_two]['articles'][0])
    finally:
        client.rss.remove_item(item_path=item_two)
        sleep(1)
        assert item_two not in client.rss.items()


def test_rules(client, api_version):
    rule_name = item_one + 'Rule'
    rule_name_new = rule_name + 'New'
    rule_def = {'enabled': True,
                'affectedFeeds': url,
                'addPaused': True}
    try:
        client.rss_add_feed(item_path=item_one, url=url)
        if is_version_less_than(api_version, '2.2', lteq=False):
            with pytest.raises(NotImplementedError):
                client.rss.refresh_item(item_path=item_two)
        else:
            client.rss.refresh_item(item_path=item_two)
        sleep(2)
        client.rss_set_rule(rule_name=rule_name, rule_def=rule_def)
        assert client.rss_rules()[rule_name]
        # rename is broken https://github.com/qbittorrent/qBittorrent/issues/12558
        # client.rss_rename_rule(orig_rule_name=rule_name, new_rule_name=rule_name_new)
        # assert client.rss_rules()[rule_name_new]
        if is_version_less_than(api_version, '2.5.1', lteq=False):
            with pytest.raises(NotImplementedError):
                client.rss_matching_articles(rule_name=rule_name)
        else:
            assert isinstance(client.rss_matching_articles(rule_name=rule_name),
                              RSSitemsDictionary)
    finally:
        client.rss_remove_rule(rule_name=rule_name)
        assert rule_name not in client.rss_rules()
        client.rss.remove_item(item_path=item_one)
        assert item_two not in client.rss_items()

    try:
        client.rss.add_feed(item_path=item_one, url=url)
        if is_version_less_than(api_version, '2.2', lteq=False):
            with pytest.raises(NotImplementedError):
                client.rss.refresh_item(item_path=item_two)
        else:
            client.rss.refresh_item(item_path=item_two)
        sleep(2)
        client.rss.set_rule(rule_name=rule_name, rule_def=rule_def)
        assert client.rss.rules[rule_name]
        # rename is broken https://github.com/qbittorrent/qBittorrent/issues/12558
        # client.rss_rename_rule(orig_rule_name=rule_name, new_rule_name=rule_name_new)
        # assert client.rss_rules()[rule_name_new]
        if is_version_less_than(api_version, '2.5.1', lteq=False):
            with pytest.raises(NotImplementedError):
                client.rss.matching_articles(rule_name=rule_name)
        else:
            assert isinstance(client.rss.matching_articles(rule_name=rule_name),
                              RSSitemsDictionary)
    finally:
        client.rss.remove_rule(rule_name=rule_name)
        assert rule_name not in client.rss.rules
        client.rss.remove_item(item_path=item_one)
        assert item_two not in client.rss.items()
