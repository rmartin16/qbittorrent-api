from attrdict import AttrDict
try:
    from collections import UserList
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from UserList import UserList


class Alias(object):
    """
    Alias class that can be used as a decorator for making methods callable
    through other names (or "aliases").
    Note: This decorator must be used inside an @aliased -decorated class.
    For example, if you want to make the method shout() be also callable as
    yell() and scream(), you can use alias like this:

        @alias('yell', 'scream')
        def shout(message):
            # ....
    """

    def __init__(self, *aliases):
        """Constructor."""
        self.aliases = set(aliases)

    def __call__(self, f):
        """
        Method call wrapper. As this decorator has arguments, this method will
        only be called once as a part of the decoration process, receiving only
        one argument: the decorated function ('f'). As a result of this kind of
        decorator, this method must return the callable that will wrap the
        decorated function.
        """
        f._aliases = self.aliases
        return f


def aliased(aliased_class):
    """
    Decorator function that *must* be used in combination with @alias
    decorator. This class will make the magic happen!
    @aliased classes will have their aliased method (via @alias) actually
    aliased.
    This method simply iterates over the member attributes of 'aliased_class'
    seeking for those which have an '_aliases' attribute and then defines new
    members in the class using those aliases as mere pointer functions to the
    original ones.

    Usage:
        @aliased
        class MyClass(object):
            @alias('coolMethod', 'myKinkyMethod')
            def boring_method():
                # ...

        i = MyClass()
        i.coolMethod() # equivalent to i.myKinkyMethod() and i.boring_method()
    """
    original_methods = aliased_class.__dict__.copy()
    for name, method in original_methods.items():
        if hasattr(method, '_aliases'):
            # Add the aliases for 'method', but don't override any
            # previously-defined attribute of 'aliased_class'
            # noinspection PyProtectedMember
            for method_alias in method._aliases - set(original_methods):
                setattr(aliased_class, method_alias, method)
    return aliased_class


##########################################################################
# Application Objects
##########################################################################
class APINames(object):
    """
    API names for API endpoints

    e.g 'torrents' in http://localhost:8080/api/v2/torrents/addTrackers
    """

    Blank = ''
    Authorization = "auth"
    Application = "app"
    Log = "log"
    Sync = "sync"
    Transfer = "transfer"
    Torrents = "torrents"
    RSS = "rss"
    Search = "search"

    def __init__(self):
        super(APINames, self).__init__()


@aliased
class InteractionLayer(object):
    def __init__(self, client):
        super(InteractionLayer, self).__init__()
        self._client = client


@aliased
class Application(InteractionLayer):
    """
    Allows interaction with "Application" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'app_' prepended)
        >>> webapiVersion = client.application.webapiVersion
        >>> web_api_version = client.application.web_api_version
        >>> app_web_api_version = client.application.app_web_api_version
        >>> # access and set preferences as attributes
        >>> is_dht_enabled = client.application.preferences.dht
        >>> # supports sending a just subset of preferences to update
        >>> client.application.preferences = dict(dht=(not is_dht_enabled))
        >>> prefs = client.application.preferences
        >>> prefs['web_ui_clickjacking_protection_enabled'] = True
        >>> client.app.preferences = prefs
        >>>
        >>> client.application.shutdown()
    """
    @property
    def version(self):
        return self._client.app_version()

    @property
    def web_api_version(self):
        return self._client.app_web_api_version()
    webapiVersion = web_api_version

    @property
    def build_info(self):
        return self._client.app_build_info()
    buildInfo = build_info

    @property
    def shutdown(self):
        return self._client.app_shutdown()

    @property
    def preferences(self):
        return self._client.app_preferences()

    @preferences.setter
    def preferences(self, v: dict):
        self.set_preferences(prefs=v)

    @Alias("setPreferences")
    def set_preferences(self, prefs: dict = None, **kwargs):
        return self._client.app_set_preferences(prefs=prefs, **kwargs)

    @property
    def default_save_path(self, **kwargs): return self._client.app_default_save_path(**kwargs)
    defaultSavePath = default_save_path


class Log(InteractionLayer):
    """
    Allows interaction with "Log" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this is all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'log_' prepended)
        >>> log_list = client.log.main()
        >>> peers_list = client.log.peers(hash='...')
        >>> # can also filter log down with additional attributes
        >>> log_info = client.log.main.info(last_known_id='...')
        >>> log_warning = client.log.main.warning(last_known_id='...')
    """

    def __init__(self, client):
        super(Log, self).__init__(client)
        self.main = Log._Main(client)

    def peers(self, last_known_id=None, **kwargs):
        return self._client.log_peers(last_known_id=last_known_id, **kwargs)

    class _Main(InteractionLayer):
        def _api_call(self, normal=None, info=None, warning=None, critical=None, last_known_id=None, **kwargs):
            return self._client.log_main(normal=normal, info=info, warning=warning, critical=critical,
                                         last_known_id=last_known_id, **kwargs)

        def __call__(self, normal=None, info=None, warning=None, critical=None, last_known_id=None, **kwargs):
            return self._api_call(normal=normal, info=info, warning=warning, critial=critical,
                                  last_known_id=last_known_id, **kwargs)

        def info(self, last_known_id=None, **kwargs):
            return self._api_call(last_known_id=last_known_id, **kwargs)

        def normal(self, last_known_id=None, **kwargs):
            return self._api_call(info=False, last_known_id=last_known_id, **kwargs)

        def warning(self, last_known_id=None, **kwargs):
            return self._api_call(info=False, normal=False, last_known_id=last_known_id, **kwargs)

        def critical(self, last_known_id=None, **kwargs):
            return self._api_call(info=False, normal=False, warning=False, last_known_id=last_known_id, **kwargs)


class Sync(InteractionLayer):
    """
    Alows interaction with the "Sync" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'sync_' prepended)
        >>> maindata = client.sync.maindata(rid="...")
        >>> torrentPeers= client.sync.torrentPeers(hash="...'", rid='...')
        >>> torrent_peers = client.sync.torrent_peers(hash="...'", rid='...')
    """
    def maindata(self, rid=None, **kwargs):
        return self._client.sync_maindata(rid=rid, **kwargs)

    @Alias('torrentPeers')
    def torrent_peers(self, hash=None, rid=None, **kwargs):
        return self._client.sync_torrent_peers(hash=hash, rid=rid, **kwargs)


@aliased
class Transfer(InteractionLayer):
    """
    Alows interaction with the "Transfer" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'transfer_' prepended)
        >>> transfer_info = client.transfer.info
        >>> # access and set download/upload limits as attributes
        >>> dl_limit = client.transfer.download_limit
        >>> # this updates qBittorrent in real-time
        >>> client.transfer.download_limit = 1024000
        >>> # update speed limits mode to alternate or not
        >>> client.transfer.speedLimitsMode = True
    """

    @property
    def info(self):
        return self._client.transfer_info()

    @property
    def speed_limits_mode(self):
        return self._client.transfer_speed_limits_mode()
    speedLimitsMode = speed_limits_mode

    @speedLimitsMode.setter
    def speedLimitsMode(self, v: bool): self.speed_limits_mode = v
    @speed_limits_mode.setter
    def speed_limits_mode(self, v: bool):
        self.toggle_speed_limits_mode(intended_state=v)

    @Alias('toggleSpeedLimitsMode')
    def toggle_speed_limits_mode(self, intended_state=None, **kwargs):
        return self._client.transfer_toggle_speed_limits_mode(intended_state=intended_state, **kwargs)

    @property
    def download_limit(self):
        return self._client.transfer_download_limit()
    downloadLimit = download_limit

    @downloadLimit.setter
    def downloadLimit(self, v: int): self.download_limit = v
    @download_limit.setter
    @Alias('downloadLimit')
    def download_limit(self, v: int):
        self.set_download_limit(limit=v)

    @property
    def upload_limit(self):
        return self._client.transfer_upload_limit()
    uploadLimit = upload_limit

    @uploadLimit.setter
    def uploadLimit(self, v: int): self.upload_limit = v
    @upload_limit.setter
    def upload_limit(self, v: int):
        self.set_upload_limit(limit=v)

    @Alias('setDownloadLimit')
    def set_download_limit(self, limit=None, **kwargs):
        return self._client.transfer_set_download_limit(limit=limit, **kwargs)

    @Alias('setUploadLimit')
    def set_upload_limit(self, limit=None, **kwargs):
        return self._client.transfer_set_upload_limit(limit=limit, **kwargs)


@aliased
class Torrents(InteractionLayer):
    """
    Alows interaction with the "Torrents" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'torrents_' prepended)
        >>> torrent_list = client.torrents.info()
        >>> torrent_list_active = client.torrents.info.active()
        >>> torrent_list_active_partial = client.torrents.active(limit=100, offset=200)
        >>> torrent_list_downloading = client.torrents.info.downloading()
        >>> # torrent looping
        >>> for torrent in client.torrents.info.completed()
        >>> # all torrents endpoints with a 'hashes' parameters support all method to apply action to all torrents
        >>> client.torrents.pause.all()
        >>> client.torrents.resume.all()
        >>> # or specify the individual hashes
        >>> client.torrents.downloadLimit(hashes=['...', '...'])
    """
    def __init__(self, client):
        super(Torrents, self).__init__(client)
        self.info = self._Info(client)
        self.resume = self._ActionForAllTorrents(client, func=client.torrents_resume)
        self.pause = self._ActionForAllTorrents(client, func=client.torrents_pause)
        self.delete = self._ActionForAllTorrents(client, func=client.torrents_delete)
        self.recheck = self._ActionForAllTorrents(client, func=client.torrents_recheck)
        self.reannounce = self._ActionForAllTorrents(client, func=client.torrents_reannounce)
        self.increase_priority = self._ActionForAllTorrents(client, func=client.torrents_increase_priority)
        self.increasePrio = self.increase_priority
        self.decrease_priority = self._ActionForAllTorrents(client, func=client.torrents_decrease_priority)
        self.decreasePrio = self.decrease_priority
        self.top_priority = self._ActionForAllTorrents(client, func=client.torrents_top_priority)
        self.topPrio = self.top_priority
        self.bottom_priority = self._ActionForAllTorrents(client, func=client.torrents_bottom_priority)
        self.bottomPrio = self.bottom_priority
        self.set_download_limit = self._ActionForAllTorrents(client, func=client.torrents_set_download_limit)
        self.setDownloadLimit = self.set_download_limit
        self.set_share_limits = self._ActionForAllTorrents(client, func=client.torrents_set_share_limits)
        self.setShareLimits = self.set_share_limits
        self.set_upload_limit = self._ActionForAllTorrents(client, func=client.torrents_set_upload_limit)
        self.setUploadLimit = self.set_upload_limit
        self.set_location = self._ActionForAllTorrents(client, func=client.torrents_set_location)
        self.setLocation = self.set_location
        self.set_category = self._ActionForAllTorrents(client, func=client.torrents_set_category)
        self.setCategory = self.set_category
        self.set_auto_management = self._ActionForAllTorrents(client, func=client.torrents_set_auto_management)
        self.setAutoManagemnt = self.set_auto_management
        self.toggle_sequential_download = self._ActionForAllTorrents(client, func=client.torrents_toggle_sequential_download)
        self.toggleSequentialDownload = self.toggle_sequential_download
        self.toggle_first_last_piece_priority = self._ActionForAllTorrents(client, func=client.torrents_toggle_first_last_piece_priority)
        self.toggleFirstLastPiecePrio = self.toggle_first_last_piece_priority
        self.set_force_start = self._ActionForAllTorrents(client, func=client.torrents_set_force_start)
        self.setForceStart = self.set_force_start
        self.set_super_seeding = self._ActionForAllTorrents(client, func=client.torrents_set_super_seeding)
        self.setSuperSeeding = self.set_super_seeding

    @property
    def download_limit(self):
        return self._ActionForAllTorrents(self._client, func=self._client.torrents_download_limit)
    downloadLimit = download_limit

    @download_limit.setter
    def download_limit(self, v: dict):
        self.set_download_limit(**v)

    @property
    def upload_limit(self):
        return self._ActionForAllTorrents(self._client, func=self.client.torrents_upload_limit)
    uploadLimit = upload_limit

    @upload_limit.setter
    def upload_limit(self, v: dict):
        self.set_upload_limit(**v)

    class _ActionForAllTorrents(InteractionLayer):
        def __init__(self, client, func):
            super(Torrents._ActionForAllTorrents, self).__init__(client)
            self.func = func

        def __call__(self, hashes=None, **kwargs):
            return self.func(hashes=hashes, **kwargs)

        def all(self):
            return self.func(hashes='all')

    class _Info(InteractionLayer):
        def __call__(self, status_filter=None, category=None, sort=None, reverse=None, limit=None, offset=None,
                     hashes=None, **kwargs):
            return self._client.torrents_info(status_filter=status_filter, category=category, sort=sort,
                                              reverse=reverse, limit=limit, offset=offset,
                                              hashes=hashes, **kwargs)

        def all(self, category=None, sort=None, reverse=None, limit=None, offset=None,
                hashes=None, **kwargs):
            return self._client.torrents_info(status_filter='all', category=category, sort=sort, reverse=reverse,
                                              limit=limit, offset=offset,
                                              hashes=hashes, **kwargs)

        def downloading(self, category=None, sort=None, reverse=None, limit=None, offset=None,
                        hashes=None, **kwargs):
            return self._client.torrents_info(status_filter='downloading', category=category, sort=sort,
                                              reverse=reverse,
                                              limit=limit, offset=offset,
                                              hashes=hashes, **kwargs)

        def completed(self, category=None, sort=None, reverse=None, limit=None, offset=None,
                      hashes=None, **kwargs):
            return self._client.torrents_info(status_filter='completed', category=category, sort=sort,
                                              reverse=reverse,
                                              limit=limit, offset=offset,
                                              hashes=hashes, **kwargs)

        def paused(self, category=None, sort=None, reverse=None, limit=None, offset=None,
                   hashes=None, **kwargs):
            return self._client.torrents_info(status_filter='paused', category=category, sort=sort,
                                              reverse=reverse,
                                              limit=limit, offset=offset,
                                              hashes=hashes, **kwargs)

        def active(self, category=None, sort=None, reverse=None, limit=None, offset=None,
                   hashes=None, **kwargs):
            return self._client.torrents_info(status_filter='active', category=category, sort=sort,
                                              reverse=reverse,
                                              limit=limit, offset=offset,
                                              hashes=hashes, **kwargs)

        def ianvtive(self, category=None, sort=None, reverse=None, limit=None, offset=None,
                     hashes=None, **kwargs):
            return self._client.torrents_info(status_filter='inactive', category=category, sort=sort,
                                              reverse=reverse,
                                              limit=limit, offset=offset,
                                              hashes=hashes, **kwargs)

        def resumed(self, category=None, sort=None, reverse=None, limit=None, offset=None,
                    hashes=None, **kwargs):
            return self._client.torrents_info(status_filter='resumed', category=category, sort=sort,
                                              reverse=reverse,
                                              limit=limit, offset=offset,
                                              hashes=hashes, **kwargs)


@aliased
class TorrentCategories(InteractionLayer):
    """
    Alows interaction with torrent categories within the "Torrents" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'torrents_' prepended)
        >>> categories = client.torrent_categories.categories
        >>> # create or edit categories
        >>> client.torrent_categories.create_category(name='Video', save_path='/home/user/torrents/Video')
        >>> client.torrent_categories.edit_category(name='Video', save_path='/data/torrents/Video')
        >>> # edit or create new by assignment
        >>> client.torrent_categories.categories = dict(name='Video', save_path='/hone/user/')
        >>> # delete categories
        >>> client.torrent_categories.removeCategories(categories='Video')
        >>> client.torrent_categories.removeCategories(categories=['Audio', "ISOs"])
    """

    @property
    def categories(self):
        return self._client.torrents_categories()

    @categories.setter
    def categories(self, v: dict):
        if v.get('name', '') in self.categories:
            self.edit_category(**v)
        else:
            self.create_category(**v)

    @Alias('createCategory')
    def create_category(self, name=None, save_path=None, **kwargs):
        return self._client.torrents_create_category(name=name, save_path=save_path, **kwargs)

    @Alias('editCategory')
    def edit_category(self, name=None, save_path=None, **kwargs):
        return self._client.torrents_edit_category(name=name, save_path=save_path, **kwargs)

    @Alias('removeCategories')
    def remove_categories(self, categories=None, **kwargs):
        return self._client.torrents_remove_categories(categories=categories, **kwargs)


@aliased
class RSS(InteractionLayer):
    """
    Allows interaction with "RSS" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this is all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'log_' prepended)
        >>> rss_rules = client.rss.rules
        >>> client.rss.addFolder(folder_path="TPB")
        >>> client.rss.addFeed(url='...', item_path="TPB\\Top100")
        >>> client.rss.remove_item(item_path="TPB") # deletes TPB and Top100
        >>> client.rss.set_rule(rule_name="...", rule_def={...})
        >>> client.rss.items.with_data
        >>> client.rss.items.without_data
    """
    def __init__(self, client):
        super(RSS, self).__init__(client)
        self.items = RSS._Items(client)

    @Alias('addFolder')
    def add_folder(self, folder_path=None, **kwargs):
        return self._client.rss_add_folder(folder_path=folder_path, **kwargs)

    @Alias('addFeed')
    def add_feed(self, url=None, item_path=None, **kwargs):
        return self._client.rss_add_feed(url=url, item_path=item_path, **kwargs)

    @Alias('removeItem')
    def remove_item(self, item_path=None, **kwargs):
        return self._client.rss_remove_item(item_path=item_path, **kwargs)

    @Alias('moveItem')
    def move_item(self, orig_item_path=None, new_item_path=None, **kwargs):
        return self._client.rss_move_item(orig_item_path=orig_item_path, new_item_path=new_item_path, **kwargs)

    @Alias('setRule')
    def set_rule(self, rule_name=None, rule_def=None, **kwargs):
        return self._client.rss_set_rule(rule_name=rule_name, rule_def=rule_def, **kwargs)

    @Alias('renameRule')
    def rename_rule(self, orig_rule_name=None, new_rule_name=None, **kwargs):
        return self._client.rss_rename_rule(orig_rule_name=orig_rule_name, new_rule_name=new_rule_name, **kwargs)

    @Alias('removeRule')
    def remove_rule(self, rule_name=None, **kwargs):
        return self._client.rss_remove_rule(rule_name=rule_name, **kwargs)

    @property
    def rules(self):
        return self._client.rss_rules()

    class _Items(InteractionLayer):
        def __call__(self, include_feed_data=None, **kwargs):
            return self._client.rss_items(include_feed_data=include_feed_data, **kwargs)

        @property
        def without_data(self):
            return self._client.rss_items(include_feed_data=False)

        @property
        def with_data(self):
            return self._client.rss_items(include_feed_data=True)


@aliased
class Search(InteractionLayer):
    """
    Allows interaction with "Search" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this is all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'search_' prepended)
        >>> # initiate searches and retrieve results
        >>> search_job = client.search.start(pattern='Ubuntu', plugins='all', category='all')
        >>> status = search_job.status()
        >>> results = search_job.result()
        >>> search_job.delete()
        >>> # inspect and manage plugins
        >>> plugins = client.search.plugins
        >>> cats = client.search.categories(plugin_name='...')
        >>> client.search.install_plugin(sources='...')
        >>> client.search.update_plugins()
    """
    def start(self, pattern=None, plugins=None, category=None, **kwargs):
        return self._client.search_start(pattern=pattern, plugins=plugins, category=category, **kwargs)

    def stop(self, search_id=None, **kwargs):
        return self._client.search_stop(search_id=search_id, **kwargs)

    def status(self, search_id=None, **kwargs):
        return self._client.search_status(search_id=search_id, **kwargs)

    def results(self, search_id=None, limit=None, offset=None, **kwargs):
        return self._client.search_results(search_id=search_id, limit=limit, offset=offset, **kwargs)

    def delete(self, search_id=None, **kwargs):
        return self._client.search_delete(search_id=search_id, **kwargs)

    def categories(self, plugin_name=None, **kwargs):
        return self._client.search_plugins(plugin_name=plugin_name, **kwargs)

    @property
    def plugins(self):
        return self._client.search_plugins()

    @Alias('installPlugin')
    def install_plugin(self, sources=None, **kwargs):
        return self._client.search_install_plugins(sources=sources, **kwargs)

    @Alias('uninstallPlugin')
    def uninstall_plugin(self, sources=None, **kwargs):
        return self._client.search_uninstall_plugin(sources=sources, **kwargs)

    @Alias('enablePlugin')
    def enable_plugin(self, plugins=None, enable=None, **kwargs):
        return self._client.search_enable_plugin(plugins=plugins, enable=enable, **kwargs)

    @Alias('updatePlugins')
    def update_plugins(self, **kwargs):
        return self._client.search_update_plugins(**kwargs)


##########################################################################
# Base Objects
##########################################################################
class Dict(AttrDict):
    def __init__(self, data=None, client=None):
        self._client = client
        super(Dict, self).__init__(data if data is not None else dict())


class ListEntry(Dict):
    def __init__(self, data=None, client=None, **kwargs):
        self._client = client
        super(ListEntry, self).__init__(data, **kwargs)


class List(UserList):
    def __init__(self, list_entiries=None, entry_class=None, client=None):
        self._client = client

        entries = []
        for entry in list_entiries:
            if isinstance(entry, dict):
                entries.append(entry_class(data=entry, client=client))
            else:
                entries.append(entry)
        super(List, self).__init__(entries)


##########################################################################
# Dictionary Objects
##########################################################################
class SearchJobDict(Dict):
    def __init__(self, data, client):
        if 'id' in data:
            self._search_job_id = data['id']
        super(SearchJobDict, self).__init__(data=data, client=client)

    def stop(self, **kwargs):
        self._client.search.stop(search_id=self._search_job_id, **kwargs)

    def status(self, **kwargs):
        return self._client.search.status(search_id=self._search_job_id, **kwargs)

    def results(self, limit=None, offset=None, **kwargs):
        return self._client.search.results(search_id=self._search_job_id, limit=limit, offset=offset, **kwargs)

    def delete(self, **kwargs):
        self._client.search.delete(search_id=self._search_job_id, **kwargs)


@aliased
class TorrentDict(Dict):
    """
    Alows interaction with individual torrents via the "Torrents" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'transfer_' prepended)
        >>> torrent = client.torrents.info()[0]
        >>> hash = torrent.info.hash
        >>> # Attributes without inputs and a return value are properties
        >>> properties = torrent.properties
        >>> trackers = torrent.trackers
        >>> files = torrent.files
        >>> # Action methods
        >>> torrent.edit_tracker(original_url="...", new_url="...")
        >>> torrent.remove_trackers(urls='http://127.0.0.2/')
        >>> torrent.rename(new_torrent_name="...")
        >>> torrent.resume()
        >>> torrent.pause()
        >>> torrent.recheck()
        >>> torrent.torrents_top_priority()
        >>> torrent.setLocation(location='/home/user/torrents/')
        >>> torrent.setCategory(category='video')
    """
    def __init__(self, data, client):
        self._torrent_hash = data.get('hash', None)
        super(TorrentDict, self).__init__(data, client)

    @property
    def info(self):
        return self._client.torrents_info(hashes=self._torrent_hash)

    def resume(self, **kwargs):
        return self._client.torrents_resume(hashes=self._torrent_hash, **kwargs)

    def pause(self, **kwargs):
        return self._client.torrents_pause(hashes=self._torrent_hash, **kwargs)

    def delete(self, **kwargs):
        return self._client.torrents_delete(hashes=self._torrent_hash, **kwargs)

    def recheck(self, **kwargs):
        return self._client.torrents_recheck(hashes=self._torrent_hash, **kwargs)

    def reannounce(self, **kwargs):
        return self._client.torrents_reannounce(hashes=self._torrent_hash, **kwargs)

    @Alias('increasePrio')
    def increase_priority(self, **kwargs):
        return self._client.torrents_increase_priority(hashes=self._torrent_hash, **kwargs)

    @Alias('decreasePrio')
    def decrease_priority(self, **kwargs):
        return self._client.torrents_decrease_priority(hashes=self._torrent_hash, **kwargs)

    @Alias('topPrio')
    def top_priority(self, **kwargs):
        return self._client.torrents_top_priority(hashes=self._torrent_hash, **kwargs)

    @Alias('bottomPrio')
    def bottom_priority(self, **kwargs):
        return self._client.torrents_bottom_priority(hashes=self._torrent_hash, **kwargs)

    @Alias('setShareLimits')
    def set_share_limits(self, ratio_limit=None, seeding_time_limit=None, **kwargs):
        return self._client.torrents_set_share_limits(hashes=self._torrent_hash, ratio_limit=ratio_limit, seeding_time_limit=seeding_time_limit, **kwargs)

    @property
    def download_limit(self, **kwargs):
        return self._client.torrents_download_limit(hashes=self._torrent_hash, **kwargs)
    downloadLimit = download_limit

    @downloadLimit.setter
    def downloadLimit(self, v: int): self.download_limit(limit=v)
    @download_limit.setter
    def download_limit(self, v: int):
        self.set_download_limit(limit=v)

    @Alias('setDownloadLimit')
    def set_download_limit(self, limit=None, **kwargs):
        return self._client.torrents_set_download_limit(hashes=self._torrent_hash, limit=limit, **kwargs)

    @property
    def upload_limit(self, **kwargs):
        return self._client.torrents_set_upload_limit(hashes=self._torrent_hash, **kwargs)
    uploadLimit = upload_limit

    @uploadLimit.setter
    def uploadLimit(self, v: int): self.set_upload_limit(limit=v)
    @upload_limit.setter
    def upload_limit(self, v: int):
        self.set_upload_limit(limit=v)

    @Alias('setUploadLimit')
    def set_upload_limit(self, limit=None, **kwargs):
        return self._client.torrents_set_upload_limit(hashes=self._torrent_hash, limit=limit, **kwargs)

    @Alias('setLocation')
    def set_location(self, location=None, **kwargs):
        return self._client.torrents_set_location(location=location, hashes=self._torrent_hash, **kwargs)

    @Alias('setCategory')
    def set_category(self, category=None, **kwargs):
        return self._client.torrents_set_category(category=category, hashes=self._torrent_hash, **kwargs)

    @Alias('setAutoManagemnt')
    def set_auto_management(self, enable=None, **kwargs):
        return self._client.torrents_set_auto_management(hashes=self._torrent_hash, enable=enable, **kwargs)

    @Alias('toggleSequentialDownload')
    def toggle_sequential_download(self, **kwargs):
        return self._client.torrents_toggle_sequential_download(hashes=self._torrent_hash, **kwargs)

    @Alias('toggleFirstLastPiecePrio')
    def toggle_first_last_piece_priority(self, **kwargs):
        return self._client.torrents_toggle_first_last_piece_priority(hashes=self._torrent_hash, **kwargs)

    @Alias('setForceStart')
    def set_force_start(self, enable=None, **kwargs):
        return self._client.torrents_set_force_start(hashes=self._torrent_hash, enable=enable, **kwargs)

    @Alias('setSuperSeeding')
    def set_super_seeding(self, enable=None, **kwargs):
        return self._client.torrents_set_super_seeding(hashes=self._torrent_hash, enable=enable, **kwargs)

    @property
    def properties(self):
        return self._client.torrents_properties(hash=self._torrent_hash)

    @property
    def trackers(self):
        return self._client.torrents_trackers(hash=self._torrent_hash)

    @trackers.setter
    def trackers(self, v: list):
        self.add_trackers(urls=v)

    @property
    def webseeds(self):
        return self._client.torrents_webseeds(hash=self._torrent_hash)

    @property
    def files(self):
        return self._client.torrents_files(hash=self._torrent_hash)

    @property
    def piece_states(self):
        return self._client.torrents_piece_states(hash=self._torrent_hash)
    pieceStates = piece_states

    @property
    def piece_hashes(self):
        return self._client.torrents_piece_hashes(hash=self._torrent_hash)
    pieceHashes = piece_hashes

    @Alias('addTrackers')
    def add_trackers(self, urls=None, **kwargs):
        return self._client.torrents_add_trackers(hash=self._torrent_hash, urls=urls, **kwargs)

    @Alias('editTracker')
    def edit_tracker(self, orig_url=None, new_url=None, **kwargs):
        return self._client.torrents_edit_tracker(hash=self._torrent_hash, original_url=orig_url, new_url=new_url, **kwargs)

    @Alias('removeTrackers')
    def remove_trackers(self, urls=None, **kwargs):
        return self._client.torrents_remove_trackers(hash=self._torrent_hash, urls=urls, **kwargs)

    @Alias('filePriority')
    def file_priority(self, file_ids=None, priority=None, **kwargs):
        return self._client.torrents_file_priority(hash=self._torrent_hash, file_ids=file_ids, priority=priority, **kwargs)

    def rename(self, new_name=None, **kwargs):
        return self._client.torrents_rename(hash=self._torrent_hash, new_torrent_name=new_name, **kwargs)


class TorrentPropertiesDict(Dict):
    pass


class TransferInfoDict(Dict):
    pass


class SyncMainDataDict(Dict):
    pass


class SyncTorrentPeersDict(Dict):
    pass


class ApplicationPreferencesDict(Dict):
    pass


class BuildInfoDict(Dict):
    pass


class RssitemsDict(Dict):
    pass


class RSSRulesDict(Dict):
    pass


class SearchResultsDict(Dict):
    pass


class TorrentLimitsDict(Dict):
    pass


class TorrentCategoriesDict(Dict):
    pass


##########################################################################
# List Objects
##########################################################################
class TorrentFilesList(List):
    def __init__(self, list_entiries=None, client=None):
        super(TorrentFilesList, self).__init__(list_entiries, entry_class=TorrentFile, client=client)


class TorrentFile(ListEntry):
    pass


class WebSeedsList(List):
    def __init__(self, list_entiries=None, client=None):
        super(WebSeedsList, self).__init__(list_entiries, entry_class=WebSeed, client=client)


class WebSeed(ListEntry):
    pass


class TrackersList(List):
    def __init__(self, list_entiries=None, client=None):
        super(TrackersList, self).__init__(list_entiries, entry_class=Tracker, client=client)


class Tracker(ListEntry):
    pass


class TorrentInfoList(List):
    def __init__(self, list_entiries=None, client=None):
        super(TorrentInfoList, self).__init__(list_entiries, entry_class=TorrentDict, client=client)


class LogPeersList(List):
    def __init__(self, list_entiries=None, client=None):
        super(LogPeersList, self).__init__(list_entiries, entry_class=LogPeer, client=client)


class LogPeer(ListEntry):
    pass


class LogMainList(List):
    def __init__(self, list_entiries=None, client=None):
        super(LogMainList, self).__init__(list_entiries, entry_class=LogEntry, client=client)


class LogEntry(ListEntry):
    pass


class TorrentPieceInfoList(List):
    def __init__(self, list_entiries=None, client=None):
        super(TorrentPieceInfoList, self).__init__(list_entiries, entry_class=TorrentPieceData, client=client)


class TorrentPieceData(ListEntry):
    pass


class TorrentCategoriesList(List):
    def __init__(self, list_entiries=None, client=None):
        super(TorrentCategoriesList, self).__init__(list_entiries, entry_class=TorrentCategory, client=client)


class TorrentCategory(ListEntry):
    pass


class SearchStatusesList(List):
    def __init__(self, list_entiries=None, client=None):
        super(SearchStatusesList, self).__init__(list_entiries, entry_class=SearchStatus, client=client)


class SearchStatus(ListEntry):
    pass


class SearchCategoriesList(List):
    def __init__(self, list_entiries=None, client=None):
        super(SearchCategoriesList, self).__init__(list_entiries, entry_class=SearchCategory, client=client)


class SearchCategory(ListEntry):
    pass


class SearchPluginsList(List):
    def __init__(self, list_entiries=None, client=None):
        super(SearchPluginsList, self).__init__(list_entiries, entry_class=SearchPlugin, client=client)


class SearchPlugin(ListEntry):
    pass
