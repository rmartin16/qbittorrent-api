from qbittorrentapi.decorators import Alias
from qbittorrentapi.decorators import aliased


# TODO: these should probably be properly incorporated in to Client...
##########################################################################
# Application Objects
##########################################################################
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
    def preferences(self, v):
        self.set_preferences(prefs=v)

    @Alias("setPreferences")
    def set_preferences(self, prefs=None, **kwargs):
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
        >>> # for looping
        >>> md = client.sync.maindata.delta()
        >>> #
        >>> torrentPeers= client.sync.torrentPeers(hash="...'", rid='...')
        >>> torrent_peers = client.sync.torrent_peers(hash="...'", rid='...')
    """
    def __init__(self, client):
        super(Sync, self).__init__(client)
        self.maindata = self._MainData(client)

    @Alias('torrentPeers')
    def torrent_peers(self, hash=None, rid=None, **kwargs):
        return self._client.sync_torrent_peers(hash=hash, rid=rid, **kwargs)

    class _MainData(InteractionLayer):
        def __init__(self, client):
            super(Sync._MainData, self).__init__(client)
            self._rid = 0

        def __call__(self, rid=None, **kwargs):
            return self._client.sync_maindata(rid=rid, **kwargs)

        def delta(self, **kwargs):
            md = self._client.sync_maindata(rid=self._rid, **kwargs)
            self._rid = md.get('rid', 0)
            return md

        def reset_rid(self):
            self._rid = 0


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
    def speedLimitsMode(self, v): self.speed_limits_mode = v
    @speed_limits_mode.setter
    def speed_limits_mode(self, v):
        self.toggle_speed_limits_mode(intended_state=v)

    @Alias('toggleSpeedLimitsMode')
    def toggle_speed_limits_mode(self, intended_state=None, **kwargs):
        return self._client.transfer_toggle_speed_limits_mode(intended_state=intended_state, **kwargs)

    @property
    def download_limit(self):
        return self._client.transfer_download_limit()
    downloadLimit = download_limit

    @downloadLimit.setter
    def downloadLimit(self, v): self.download_limit = v
    @download_limit.setter
    @Alias('downloadLimit')
    def download_limit(self, v):
        self.set_download_limit(limit=v)

    @property
    def upload_limit(self):
        return self._client.transfer_upload_limit()
    uploadLimit = upload_limit

    @uploadLimit.setter
    def uploadLimit(self, v): self.upload_limit = v
    @upload_limit.setter
    def upload_limit(self, v):
        self.set_upload_limit(limit=v)

    @Alias('setDownloadLimit')
    def set_download_limit(self, limit=None, **kwargs):
        return self._client.transfer_set_download_limit(limit=limit, **kwargs)

    @Alias('setUploadLimit')
    def set_upload_limit(self, limit=None, **kwargs):
        return self._client.transfer_set_upload_limit(limit=limit, **kwargs)

    @Alias('banPeers')
    def ban_peers(self, peers=None, **kwargs):
        return self._client.transfer_ban_peers(peers=peers, **kwargs)


@aliased
class Torrents(InteractionLayer):
    """
    Allows interaction with the "Torrents" API endpoints.

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
        self.download_limit = self._ActionForAllTorrents(client, func=client.torrents_download_limit)
        self.downloadLimit = self.download_limit
        self.upload_limit = self._ActionForAllTorrents(client, func=client.torrents_upload_limit)
        self.uploadLimit = self.upload_limit
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
        self.setAutoManagement = self.set_auto_management
        self.toggle_sequential_download = self._ActionForAllTorrents(client, func=client.torrents_toggle_sequential_download)
        self.toggleSequentialDownload = self.toggle_sequential_download
        self.toggle_first_last_piece_priority = self._ActionForAllTorrents(client, func=client.torrents_toggle_first_last_piece_priority)
        self.toggleFirstLastPiecePrio = self.toggle_first_last_piece_priority
        self.set_force_start = self._ActionForAllTorrents(client, func=client.torrents_set_force_start)
        self.setForceStart = self.set_force_start
        self.set_super_seeding = self._ActionForAllTorrents(client, func=client.torrents_set_super_seeding)
        self.setSuperSeeding = self.set_super_seeding
        self.add_peers = self._ActionForAllTorrents(client, func=client.torrents_add_peers)
        self.addPeers = self.add_peers

    def add(self, urls=None, torrent_files=None, save_path=None, cookie=None, category=None,
            is_skip_checking=None, is_paused=None, is_root_folder=None, rename=None,
            upload_limit=None, download_limit=None, use_auto_torrent_management=None,
            is_sequential_download=None, is_first_last_piece_priority=None, **kwargs):
        return self._client.torrents_add(urls=urls, torrent_files=torrent_files, save_path=save_path, cookie=cookie,
                                         category=category, is_skip_checking=is_skip_checking, is_paused=is_paused,
                                         is_root_folder=is_root_folder, rename=rename, upload_limit=upload_limit,
                                         download_limit=download_limit,
                                         use_auto_torrent_management=use_auto_torrent_management,
                                         is_sequential_download=is_sequential_download,
                                         is_first_last_piece_priority=is_first_last_piece_priority, **kwargs)

    class _ActionForAllTorrents(InteractionLayer):
        def __init__(self, client, func):
            super(Torrents._ActionForAllTorrents, self).__init__(client)
            self.func = func

        def __call__(self, hashes=None, **kwargs):
            return self.func(hashes=hashes, **kwargs)

        def all(self, **kwargs):
            return self.func(hashes='all', **kwargs)

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

        def inactive(self, category=None, sort=None, reverse=None, limit=None, offset=None,
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
    def categories(self, v):
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
class TorrentTags(InteractionLayer):
    """
    Allows interaction with torrent tags within the "Torrent" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> tags = client.torrent_tags.tags
        >>> client.torrent_tags.tags = 'tv show'  # create category
        >>> client.torrent_tags.create_tags(tags=['tv show', 'linux distro'])
        >>> client.torrent_tags.delete_tags(tags='tv show')
    """

    @property
    def tags(self):
        return self._client.torrents_tags()

    @tags.setter
    def tags(self, v):
        self._client.torrents_create_tags(tags=v)

    @Alias('addTags')
    def add_tags(self, tags=None, hashes=None, **kwargs):
        self._client.torrents_add_tags(tags=tags, hashes=hashes, **kwargs)

    @Alias('removeTags')
    def remove_tags(self, tags=None, hashes=None, **kwargs):
        self._client.torrents_remove_tags(tags=tags, hashes=hashes, **kwargs)

    @Alias('createTags')
    def create_tags(self, tags=None, **kwargs):
        self._client.torrents_create_tags(tags=tags, **kwargs)

    @Alias('deleteTags')
    def delete_tags(self, tags=None, **kwargs):
        self._client.torrents_delete_tags(tags=tags, **kwargs)


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

    @Alias('refreshItem')
    def refresh_item(self, item_path=None):
        return self._client.rss_refresh_item(item_path=item_path)

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
