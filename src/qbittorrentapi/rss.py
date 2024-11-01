from __future__ import annotations

from collections.abc import Mapping
from json import dumps

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    ClientCache,
    Dictionary,
    JsonValueT,
)


class RSSitemsDictionary(Dictionary[JsonValueT]):
    """Response for :meth:`~RSSAPIMixIn.rss_items`"""


class RSSRulesDictionary(Dictionary[JsonValueT]):
    """Response for :meth:`~RSSAPIMixIn.rss_rules`"""


class RSSAPIMixIn(AppAPIMixIn):
    """
    Implementation of all ``RSS`` API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> rss_rules = client.rss_rules()
        >>> client.rss_set_rule(rule_name="...", rule_def={...})
    """  # noqa: E501

    @property
    def rss(self) -> RSS:
        """
        Allows for transparent interaction with RSS endpoints.

        See RSS class for usage.
        """
        if self._rss is None:
            self._rss = RSS(client=self)
        return self._rss

    def rss_add_folder(
        self,
        folder_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Add an RSS folder. Any intermediate folders in path must already exist.

        :raises Conflict409Error:

        :param folder_path: path to new folder (e.g. ``Linux\\ISOs``)
        """
        data = {"path": folder_path}
        self._post(_name=APINames.RSS, _method="addFolder", data=data, **kwargs)

    rss_addFolder = rss_add_folder

    def rss_add_feed(
        self,
        url: str | None = None,
        item_path: str = "",
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Add new RSS feed. Folders in path must already exist.

        :raises Conflict409Error:

        :param url: URL of RSS feed (e.g. https://distrowatch.com/news/torrents.xml)
        :param item_path: Name and/or path for new feed; defaults to the URL.
            (e.g. ``Folder\\Subfolder\\FeedName``)
        """  # noqa: E501
        data = {"path": item_path, "url": url}
        self._post(_name=APINames.RSS, _method="addFeed", data=data, **kwargs)

    rss_addFeed = rss_add_feed

    def rss_set_feed_url(
        self,
        url: str | None = None,
        item_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Update the URL for an existing RSS feed.

        This method was introduced with qBittorrent v4.6.0 (Web API v2.9.1).

        :raises Conflict409Error:

        :param url: URL of RSS feed (e.g. https://distrowatch.com/news/torrents.xml)
        :param item_path: Name and/or path for feed (e.g. ``Folder\\Subfolder\\FeedName``)
        """  # noqa: E501
        data = {"path": item_path, "url": url}
        self._post(
            _name=APINames.RSS,
            _method="setFeedURL",
            data=data,
            version_introduced="2.9.1",
            **kwargs,
        )

    rss_setFeedURL = rss_set_feed_url

    def rss_remove_item(
        self,
        item_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Remove an RSS item (folder, feed, etc.).

        NOTE: Removing a folder also removes everything in it.

        :raises Conflict409Error:

        :param item_path: path to item to be removed
            (e.g. ``Folder\\Subfolder\\ItemName``)
        """
        data = {"path": item_path}
        self._post(_name=APINames.RSS, _method="removeItem", data=data, **kwargs)

    rss_removeItem = rss_remove_item

    def rss_move_item(
        self,
        orig_item_path: str | None = None,
        new_item_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Move/rename an RSS item (folder, feed, etc.).

        :raises Conflict409Error:

        :param orig_item_path: path to item to be removed
            (e.g. ``Folder\\Subfolder\\ItemName``)
        :param new_item_path: path to item to be removed
            (e.g. ``Folder\\Subfolder\\ItemName``)
        """
        data = {"itemPath": orig_item_path, "destPath": new_item_path}
        self._post(_name=APINames.RSS, _method="moveItem", data=data, **kwargs)

    rss_moveItem = rss_move_item

    def rss_items(
        self,
        include_feed_data: bool | None = None,
        **kwargs: APIKwargsT,
    ) -> RSSitemsDictionary:
        """
        Retrieve RSS items and optionally feed data.

        :param include_feed_data: True or false to include feed data
        """
        params = {
            "withData": None if include_feed_data is None else bool(include_feed_data)
        }
        return self._get_cast(
            _name=APINames.RSS,
            _method="items",
            params=params,
            response_class=RSSitemsDictionary,
            **kwargs,
        )

    def rss_refresh_item(
        self,
        item_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Trigger a refresh for an RSS item.

        Note: qBittorrent v4.1.5 through v4.1.8 all use Web API v2.2 but this endpoint
        was introduced with v4.1.8; so, behavior may be undefined for these versions.

        :param item_path: path to item to be refreshed
            (e.g. ``Folder\\Subfolder\\ItemName``)
        """
        data = {"itemPath": item_path}
        self._post(
            _name=APINames.RSS,
            _method="refreshItem",
            data=data,
            version_introduced="2.2",
            **kwargs,
        )

    rss_refreshItem = rss_refresh_item

    def rss_mark_as_read(
        self,
        item_path: str | None = None,
        article_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Mark RSS article as read. If article ID is not provider, the entire feed is
        marked as read.

        This method was introduced with qBittorrent v4.2.5 (Web API v2.5.1).

        :raises NotFound404Error:

        :param item_path: path to item to be refreshed
            (e.g. ``Folder\\Subfolder\\ItemName``)
        :param article_id: article ID from :meth:`~RSSAPIMixIn.rss_items`
        """
        data = {"itemPath": item_path, "articleId": article_id}
        self._post(
            _name=APINames.RSS,
            _method="markAsRead",
            data=data,
            version_introduced="2.5.1",
            **kwargs,
        )

    rss_markAsRead = rss_mark_as_read

    def rss_set_rule(
        self,
        rule_name: str | None = None,
        rule_def: Mapping[str, JsonValueT] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Create a new RSS auto-downloading rule.

        :param rule_name: name for new rule
        :param rule_def: dictionary with rule fields - `<https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-set-auto-downloading-rule>`_
        """  # noqa: E501
        data = {"ruleName": rule_name, "ruleDef": dumps(rule_def)}
        self._post(_name=APINames.RSS, _method="setRule", data=data, **kwargs)

    rss_setRule = rss_set_rule

    def rss_rename_rule(
        self,
        orig_rule_name: str | None = None,
        new_rule_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Rename an RSS auto-download rule.

        This method did not work properly until qBittorrent v4.3.0 (Web API v2.6).

        :param orig_rule_name: current name of rule
        :param new_rule_name: new name for rule
        """
        data = {"ruleName": orig_rule_name, "newRuleName": new_rule_name}
        self._post(_name=APINames.RSS, _method="renameRule", data=data, **kwargs)

    rss_renameRule = rss_rename_rule

    def rss_remove_rule(
        self,
        rule_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Delete a RSS auto-downloading rule.

        :param rule_name: Name of rule to delete
        """
        data = {"ruleName": rule_name}
        self._post(_name=APINames.RSS, _method="removeRule", data=data, **kwargs)

    def rss_rules(self, **kwargs: APIKwargsT) -> RSSRulesDictionary:
        """Retrieve RSS auto-download rule definitions."""
        return self._get_cast(
            _name=APINames.RSS,
            _method="rules",
            response_class=RSSRulesDictionary,
            **kwargs,
        )

    rss_removeRule = rss_remove_rule

    def rss_matching_articles(
        self,
        rule_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> RSSitemsDictionary:
        """
        Fetch all articles matching a rule.

        This method was introduced with qBittorrent v4.2.5 (Web API v2.5.1).

        :param rule_name: Name of rule to return matching articles
        """
        data = {"ruleName": rule_name}
        return self._post_cast(
            _name=APINames.RSS,
            _method="matchingArticles",
            data=data,
            response_class=RSSitemsDictionary,
            version_introduced="2.5.1",
            **kwargs,
        )

    rss_matchingArticles = rss_matching_articles


class RSS(ClientCache[RSSAPIMixIn]):
    """
    Allows interaction with ``RSS`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # this is all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'log_' prepended)
        >>> rss_rules = client.rss.rules
        >>> client.rss.addFolder(folder_path="TPB")
        >>> client.rss.addFeed(url="...", item_path="TPB\\Top100")
        >>> client.rss.remove_item(item_path="TPB") # deletes TPB and Top100
        >>> client.rss.set_rule(rule_name="...", rule_def={...})
        >>> items = client.rss.items.with_data
        >>> items_no_data = client.rss.items.without_data
    """  # noqa: E501

    def __init__(self, client: RSSAPIMixIn):
        super().__init__(client=client)
        self._items = RSS.Items(client=client)

    def add_folder(
        self,
        folder_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_add_folder`."""
        return self._client.rss_add_folder(folder_path=folder_path, **kwargs)

    addFolder = add_folder

    def add_feed(
        self,
        url: str | None = None,
        item_path: str = "",
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_add_feed`."""
        return self._client.rss_add_feed(url=url, item_path=item_path, **kwargs)

    addFeed = add_feed

    def set_feed_url(
        self,
        url: str | None = None,
        item_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_set_feed_url`."""
        return self._client.rss_set_feed_url(url=url, item_path=item_path, **kwargs)

    setFeedURL = set_feed_url

    def remove_item(self, item_path: str | None = None, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_remove_item`."""
        return self._client.rss_remove_item(item_path=item_path, **kwargs)

    removeItem = remove_item

    def move_item(
        self,
        orig_item_path: str | None = None,
        new_item_path: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_move_item`."""
        return self._client.rss_move_item(
            orig_item_path=orig_item_path,
            new_item_path=new_item_path,
            **kwargs,
        )

    moveItem = move_item

    def refresh_item(self, item_path: str | None = None) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_refresh_item`."""
        return self._client.rss_refresh_item(item_path=item_path)

    refreshItem = refresh_item

    def mark_as_read(
        self,
        item_path: str | None = None,
        article_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_mark_as_read`."""
        return self._client.rss_mark_as_read(
            item_path=item_path,
            article_id=article_id,
            **kwargs,
        )

    markAsRead = mark_as_read

    def set_rule(
        self,
        rule_name: str | None = None,
        rule_def: Mapping[str, JsonValueT] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_set_rule`."""
        return self._client.rss_set_rule(
            rule_name=rule_name,
            rule_def=rule_def,
            **kwargs,
        )

    setRule = set_rule

    def rename_rule(
        self,
        orig_rule_name: str | None = None,
        new_rule_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_rename_rule`."""
        return self._client.rss_rename_rule(
            orig_rule_name=orig_rule_name,
            new_rule_name=new_rule_name,
            **kwargs,
        )

    renameRule = rename_rule

    def remove_rule(
        self,
        rule_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~RSSAPIMixIn.rss_remove_rule`."""
        return self._client.rss_remove_rule(rule_name=rule_name, **kwargs)

    removeRule = remove_rule

    @property
    def rules(self) -> RSSRulesDictionary:
        """Implements :meth:`~RSSAPIMixIn.rss_rules`."""
        return self._client.rss_rules()

    def matching_articles(
        self,
        rule_name: str | None = None,
        **kwargs: APIKwargsT,
    ) -> RSSitemsDictionary:
        """Implements :meth:`~RSSAPIMixIn.rss_matching_articles`."""
        return self._client.rss_matching_articles(rule_name=rule_name, **kwargs)

    matchingArticles = matching_articles

    class Items(ClientCache[RSSAPIMixIn]):
        def __call__(
            self,
            include_feed_data: bool | None = None,
            **kwargs: APIKwargsT,
        ) -> RSSitemsDictionary:
            """Implements :meth:`~RSSAPIMixIn.rss_items`."""
            return self._client.rss_items(include_feed_data=include_feed_data, **kwargs)

        @property
        def without_data(self) -> RSSitemsDictionary:
            """Implements :meth:`~RSSAPIMixIn.rss_items` with
            ``include_feed_data=False``."""
            return self._client.rss_items(include_feed_data=False)

        @property
        def with_data(self) -> RSSitemsDictionary:
            """Implements :meth:`~RSSAPIMixIn.rss_items` with
            ``include_feed_data=True``."""
            return self._client.rss_items(include_feed_data=True)

    @property
    def items(self) -> RSS.Items:
        """Implements :meth:`~RSSAPIMixIn.rss_items`."""
        return self._items
