import logging
from json import dumps

from qbittorrentapi.request import RequestMixIn
from qbittorrentapi.decorators import response_json
from qbittorrentapi.decorators import login_required
from qbittorrentapi.decorators import Alias
from qbittorrentapi.decorators import aliased
from qbittorrentapi.decorators import version_implemented
from qbittorrentapi.helpers import APINames
from qbittorrentapi.responses import RSSRulesDictionary
from qbittorrentapi.responses import RSSitemsDictionary

logger = logging.getLogger(__name__)


@aliased
class RSSMixIn(RequestMixIn):
    @Alias('rss_addFolder')
    @login_required
    def rss_add_folder(self, folder_path=None, **kwargs):
        """
        Add a RSS folder. Any intermediate folders in path must already exist. (alias: rss_addFolder)

        Exceptions:
            Conflict409Error

        :param folder_path: path to new folder (e.g. Linux\ISOs)
        :return: None
        """
        data = {'path': folder_path}
        self._post(_name=APINames.RSS, _method='addFolder', data=data, **kwargs)

    @Alias('rss_addFeed')
    @login_required
    def rss_add_feed(self, url=None, item_path=None, **kwargs):
        """
        Add new RSS feed. Folders in path must already exist. (alias: rss_addFeed)

        Exceptions:
            Conflict409Error

        :param url: URL of RSS feed (e.g http://thepiratebay.org/rss/top100/200)
        :param item_path: Name and/or path for new feed (e.g. Folder\Subfolder\FeedName)
        :return: None
        """
        data = {'url': url,
                'path': item_path}
        self._post(_name=APINames.RSS, _method='addFeed', data=data, **kwargs)

    @Alias('rss_removeItem')
    @login_required
    def rss_remove_item(self, item_path=None, **kwargs):
        """
        Remove a RSS item (folder, feed, etc). (alias: rss_removeItem)

        NOTE: Removing a folder also removes everything in it.

        Exceptions:
            Conflict409Error

        :param item_path: path to item to be removed (e.g. Folder\Subfolder\ItemName)
        :return: None
        """
        data = {'path': item_path}
        self._post(_name=APINames.RSS, _method='removeItem', data=data, **kwargs)

    @Alias('rss_moveItem')
    @login_required
    def rss_move_item(self, orig_item_path=None, new_item_path=None, **kwargs):
        """
        Move/rename a RSS item (folder, feed, etc). (alias: rss_moveItem)

        Exceptions:
            Conflict409Error

        :param orig_item_path: path to item to be removed (e.g. Folder\Subfolder\ItemName)
        :param new_item_path: path to item to be removed (e.g. Folder\Subfolder\ItemName)
        :return: None
        """
        data = {'itemPath': orig_item_path,
                'destPath': new_item_path}
        self._post(_name=APINames.RSS, _method='moveItem', data=data, **kwargs)

    @response_json(RSSitemsDictionary)
    @login_required
    def rss_items(self, include_feed_data=None, **kwargs):
        """
        Retrieve RSS items and optionally feed data.

        :param include_feed_data: True or false to include feed data
        :return: dictionary of RSS items
        """
        params = {'withData': include_feed_data}
        return self._get(_name=APINames.RSS, _method='items', params=params, **kwargs)

    @version_implemented('2.2', 'rss/refreshItem')
    @Alias("rss_refreshItem")
    @login_required
    def rss_refresh_item(self, item_path=None, **kwargs):
        """
        Trigger a refresh for a RSS item (alias: rss_refreshItem)

        :param item_path: path to item to be refreshed (e.g. Folder\Subfolder\ItemName)
        :return: None
        """
        # HACK: v4.1.7 and v4.1.8 both use api v2.2; however, refreshItem was introduced in v4.1.8
        from qbittorrentapi.helpers import is_version_less_than
        if is_version_less_than('v4.1.7', self.app_version(), False):
            params = {"itemPath": item_path}
            self._get(_name=APINames.RSS, _method="refreshItem", params=params, **kwargs)

    @Alias('rss_setRule')
    @login_required
    def rss_set_rule(self, rule_name=None, rule_def=None, **kwargs):
        """
        Create a new RSS auto-downloading rule. (alias: rss_setRule)

        :param rule_name: name for new rule
        :param rule_def: dictionary with rule fields
            Properties: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation#set-auto-downloading-rule
        :return: None
        """
        data = {'ruleName': rule_name,
                'ruleDef': dumps(rule_def)}
        self._post(_name=APINames.RSS, _method='setRule', data=data, **kwargs)

    @Alias('rss_renameRule')
    @login_required
    def rss_rename_rule(self, orig_rule_name=None, new_rule_name=None, **kwargs):
        """
        Rename a RSS auto-download rule. (alias: rss_renameRule)

        :param orig_rule_name: current name of rule
        :param new_rule_name: new name for rule
        :return: None
        """
        data = {'ruleName': orig_rule_name,
                'newRuleName': new_rule_name}
        self._post(_name=APINames.RSS, _method='renameRule', data=data, **kwargs)

    @Alias('rss_removeRule')
    @login_required
    def rss_remove_rule(self, rule_name=None, **kwargs):
        """
        Delete a RSS auto-downloading rule. (alias: rss_removeRule)

        :param rule_name: Name of rule to delete
        :return: None
        """
        data = {'ruleName': rule_name}
        self._post(_name=APINames.RSS, _method='removeRule', data=data, **kwargs)

    @response_json(RSSRulesDictionary)
    @login_required
    def rss_rules(self, **kwargs):
        """
        Retrieve RSS auto-download rule definitions.

        :return: None
        """
        return self._get(_name=APINames.RSS, _method='rules', **kwargs)
