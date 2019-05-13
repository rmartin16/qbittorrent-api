from attrdict import AttrDict
try:
    from collections import UserList
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from UserList import UserList

import logging


def suppress_context(exc):
    """
    This is used to mask an exception with another one.

    For instance, below, the devide by zero error is masked by the CustomException.
        try:
            1/0
        except ZeroDivisionError:
            raise suppress_context(CustomException())

    Note: In python 3, the last line would simply be raise CustomException() from None
    :param exc: new Exception that will be raised
    :return: Exception to be raised
    """
    exc.__cause__ = None
    return exc


##########################################################################
# Application Objects
##########################################################################
class InteractionLayer(object):
    # _real_attrs = ['_client']
    """Set of attrs that are that not being inherited from Client and aren't already
    part of the sets below. Effectively 'normal and real attrs."""

    _client_method_name = ""
    """API name for methods in Client. For instance, 'app' for Application API methods."""

    _attrs_that_trigger_api_update = {}
    """When a particular attr is set, which API method should be triggered with the value.
    For instance, when client.application.preferences is set to a value, that value should
    be sent to qBittorrent via the app_set_preferences method.
    For this example, {'app_preferences': 'app_set_preferences'}.
    Additionally, the method to trigger can be specified locally to wrap the API method in Client."""

    _client_attributes_to_cache = []
    """Client methods whose API repsonses shall be cached. This should include methods
    whose responses are static over time like app_version."""

    _client_attributes_as_properties = []
    """List of attributes that should be treated as properties.
    For instance, client.application.version as opposed to client.transfer.set_upload_limit()"""

    def __init__(self, client=None):
        # all 'real' attrs are assumed to start with an underscore
        self._add_attribute('_client', client)

        super(InteractionLayer, self).__init__()

    def _add_attribute(self, attr_name, attr_value):
        self.__setattr__(attr_name, attr_value, force=True)

    def _get_attribute_name(self, item):
        """
        Normalize attribute handling for getting and setting.

        Cases for item:
            1. Calling with naked endpoint name:
                item = webapiVersion:
                        attribute: app_webapiVersion
            2. Calling with already formatted attribute
                item = app_webapiVersion:
                    attribute = app_webapiVersion
            3. Calling with a 'real' attribute:
                item = _client:
                    attribute: _client
        :param item: attribute for getting or setting
        :return: normalized forrmatting attribute of InteractionLayer or Client
        """
        attribute = ''
        if item:
            # assumes default is Case 2 or 3
            attribute = item
            # don't change attributes starting with an underscore (like _client)
            #  but ensure all others start with the name of the API for Client
            if item[0] != "_" and item[0:len(self._client_method_name)] != self._client_method_name:
                attribute = "%s_%s" % (self._client_method_name, item)

        return attribute

    def __setattr__(self, key, value, force=False):
        """
        Send values to qBittorrent if necessary and store 'real' attrs and cached API responses.

        :param key: attr
        :param value: attr value
        :param force: True from __getattr__; False anywhere else. Allows caching of API responses
                      while preventing developers from cloberring the internal data structure.
        :return: None
        """
        attribute = self._get_attribute_name(key)

        # update preferences in qBittorrent
        if attribute in self._attrs_that_trigger_api_update:
            try:
                # check if the method to trigger is specified locally
                #  e.g. client.transfer.speedLimitsMode = True triggers client.transfer.wrap_toggle_speed_limits_mode
                getattr(self, self._attrs_that_trigger_api_update[attribute])(value)
            except AttributeError:
                # else go find the method to trigger in Client
                getattr(self._client, self._attrs_that_trigger_api_update[attribute])(value)

        # set attribute
        if force:
            super(InteractionLayer, self).__setattr__(key, value)
        else:
            # TODO: remove this
            logging.getLogger(__name__).debug("WARNING: Interaction layer '%s' did not set attribute '%s' to value '%s'" % (self.__class__.__name__, key, value))

    def __getattribute__(self, item, *args, **kwargs):
        """
        Retrieve attribute value (may be a method)

        Hierarchy to find return value:
            1) return value from raw provided attribute
            2) return value from cached attribute result
            3) value from formatted attribute (i.e. if provided input is 'version', formatted attr is 'app_version'
            4) value from interaction layer method override
            5) value from Client

            if the attribute is specified in _client_attributes_as_properties, the attribute will be invoked
             and the return value sent back
            if the attribute is specifed in _client_attributes_to_cache, the attribute value is cached

        :param item: attr
        :return: attr value
        """
        attribute = item
        attribute_value = None
        try:
            # first, check if the un-formatted input exists as an attribute.
            #  Otherwise, stuck in a infinite loop since _get_attribute_name invokes this method (ie __getattribute__)
            result = super(InteractionLayer, self).__getattribute__(attribute)
            # attributes that require special handling shall not start with an underscore
            if attribute[0] == '_':
                return result
        except AttributeError:
            attribute = self._get_attribute_name(item)
            try:
                # check if the attribute value is cached
                return super(InteractionLayer, self).__getattribute__(self._interaction_layer_cached_attibute_name(attribute))
            except AttributeError:
                try:
                    #  check if the attribute exists locally. These can be properties or methods.
                    #  One, this allows for overriding or amending Client method behavior here in the interaction layer.
                    #  Two, this allows for entirely new methods that don't exist in Client
                    #  for instance, client.rss.items_with_data
                    result = super(InteractionLayer, self).__getattribute__(attribute)
                except AttributeError:
                    try:
                        # check if a InteractionLayerMethodOverride is specified for the attribute
                        result = super(InteractionLayer, self).__getattribute__(self._interaction_layer_method_override_attribute_name(attribute))
                    except AttributeError:
                        try:
                            # Finally, request it from Client (and ultimately through the API most likely)
                            result = getattr(self._client, attribute)
                        except AttributeError:
                            # mask the intermediate AttributeErrors
                            # raise suppress_context(AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, item)))
                            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, item))

        if result is not None:
            # all attributes should be methods, so call it to return the value
            if attribute in self._client_attributes_as_properties:
                attribute_value = result()
            else:
                attribute_value = result
            # cache if successful
            if result is not None and attribute in self._client_attributes_to_cache:
                self.__setattr__(self._interaction_layer_cached_attibute_name(attribute), attribute_value, force=True)
        return attribute_value

    def _add_client_method(self, endpoint, method_class, *args, **kwargs):
        api_name_len = len(self._client_method_name)
        api_entry = getattr(self._client, endpoint)
        api_method = method_class(client=self._client, api_entry=api_entry, *args, **kwargs)
        self._add_attribute(self._interaction_layer_method_override_attribute_name(endpoint), api_method)
        self._add_attribute(self._interaction_layer_method_override_attribute_name(endpoint[api_name_len+1:]), api_method)

    @staticmethod
    def _interaction_layer_method_override_attribute_name(attribute):
        return "override_%s" % attribute

    @staticmethod
    def _interaction_layer_cached_attibute_name(attribute):
        return "cached_%s" % attribute


class InteractionLayerMethodOverride(object):
    def __init__(self, client=None, api_entry=None, **kwargs):
        self._client = client
        self._api_entry = api_entry
        self._default_API_params = kwargs if kwargs is not None else {}

    def __call__(self, *args, **kwargs):
        return self._api_call(*args, **kwargs)

    def _api_call(self, *args, **kwargs):
        merged_kwargs = self._default_API_params.copy()
        merged_kwargs.update(kwargs)
        return self._api_entry(*args, **merged_kwargs)

    def __getattr__(self, item):
        return self.__call__()[item]

    __getitem__ = __getattr__


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
        >>> # this updates qBittorrent in real-time
        >>> client.application.preferences.dht = not is_dht_enabled
        >>> # supports sending a just subset of preferences to update
        >>> client.application.preferences = {'dht': True}
        >>> prefs = client.application.preferences
        >>> prefs['web_ui_clickjacking_protection_enabled'] = True
        >>> # or send all preferences back
        >>> client.application.preferences = prefs
        >>>
        >>> client.application.shutdown()
    """

    _client_method_name = "app"

    _attrs_that_trigger_api_update = {'app_preferences': 'app_set_preferences'}

    _client_attributes_to_cache = ['app_version',
                                   'app_web_api_version',
                                   'app_webapiVersion',
                                   'app_build_info',
                                   'app_buildInfo',
                                   'app_default_save_path',
                                   'app_defaultSavePath']

    _client_attributes_as_properties = ['app_preferences']
    _client_attributes_as_properties.extend(_client_attributes_to_cache)


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
    _client_method_name = "log"

    _attrs_that_trigger_api_update = {}

    _client_attributes_to_cache = []

    _client_attributes_as_properties = []

    # For Log, the log_main API method in Client is effectively overridden below with
    # class _Main since the local attribute main is assigned. The __call__ function in
    # _Main ensure that client.log.main() still works.

    def __init__(self, client):
        super(Log, self).__init__(client=client)
        self._add_client_method(endpoint="log_main", method_class=Log._Main)

    class _Main(InteractionLayerMethodOverride):
        def info(self, *args, **kwargs):
            return self._api_call(*args, **kwargs)

        def normal(self, *args, **kwargs):
            return self._api_call(info=False, *args, **kwargs)

        def warning(self, *args, **kwargs):
            return self._api_call(info=False, normal=False, *args, **kwargs)

        def critical(self, *args, **kwargs):
            return self._api_call(info=False, normal=False, warning=False, *args, **kwargs)


class Sync(InteractionLayer):
    """
    Alows interaction with the "Sync" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'sync_' prepended)
        >>> maindata = client.sync.maindata(rid="...")
        >>> torrentPeers= client.application.torrentPeers(hash="...'", rid='...')
        >>> torrent_peers = client.application.torrent_peers(hash="...'", rid='...')
    """
    _client_method_name = "sync"

    _attrs_that_trigger_api_update = {}

    _client_attributes_to_cache = []

    _client_attributes_as_properties = []


class Transfer(InteractionLayer):
    """
    Alows interaction with the "Transfer" API endpoints.

    Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host='localhost:8080', username='admin', password='adminadmin')
        >>> # this are all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'transfer_' prepended)
        >>> transfer_info = client.transfer_info
        >>> info = client.application.info
        >>> # access and set download/upload limits as attributes
        >>> dl_limit = client.transfer.download_limit
        >>> # this updates qBittorrent in real-time
        >>> client.transfer.download_limit = 1024000
        >>> # update speed limits mode to alternate or not
        >>> client.transfer.speedLimitsMode = True
    """
    _client_method_name = "transfer"

    _attrs_that_trigger_api_update = {'transfer_speed_limits_mode': 'wrap_toggle_speed_limits_mode',
                                      'transfer_speedLimitsMode': 'wrap_toggle_speed_limits_mode',
                                      'transfer_download_limit': 'transfer_set_download_limit',
                                      'transfer_upload_limit': 'transfer_set_upload_limit',
                                      'transfer_uploadLimit': 'transfer_set_upload_limit'}

    _client_attributes_as_properties = ['transfer_speed_limits_mode',
                                        'transfer_speedLimitsMode',
                                        'transfer_info',
                                        'transfer_download_limit',
                                        'transfer_downloadLimit',
                                        'transfer_upload_limit',
                                        'transfer_uploadLimit']

    _client_attributes_to_cache = []

    def wrap_toggle_speed_limits_mode(self, intended_state):
        self._client.transfer_toggle_speed_limits_mode(intended_state=intended_state)


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

    _client_method_name = "torrents"

    _attrs_that_trigger_api_update = {}

    _client_attributes_to_cache = []

    _client_attributes_as_properties = []

    _client_methods_for_single_torrent = ['torrents_trackers',
                                          'torrents_webseeds',
                                          'torrents_files',
                                          'torrents_piece_states',
                                          'torrents_pieceStates',
                                          'torrents_piece_hashes',
                                          'torrents_pieceHashes',
                                          'torrents_addTrackers',
                                          'torrents_add_trackers',
                                          'torrents_addTrackers',
                                          'torrents_edit_tracker',
                                          'torrents_editTracker',
                                          'torrents_remove_trackers',
                                          'torrents_removeTrackers',
                                          'torrents_file_priority',
                                          'torrents_filePrio',
                                          'torrents_rename']

    _client_methods_for_multiple_torrents = ['torrents_resume',
                                             'torrents_pause',
                                             'torrents_delete',
                                             'torrents_recheck',
                                             'torrents_reannounce',
                                             'torrents_increase_priority',
                                             'torrents_increasePrio',
                                             'torrents_decrease_priority',
                                             'torrents_decreasePrio',
                                             'torrents_top_priority',
                                             'torrents_topPrio',
                                             'torrents_bottom_priority',
                                             'torrents_bottomPrio',
                                             'torrents_download_limit',
                                             'torrents_downloadLimit',
                                             'torrents_set_download_limit',
                                             'torrents_setDownloadLimit',
                                             'torrents_set_share_limits',
                                             'torrents_setShareLimits',
                                             'torrents_upload_limit',
                                             'torrents_uploadLimit',
                                             'torrents_set_upload_limit',
                                             'torrents_setUploadLimit',
                                             'torrents_set_location',
                                             'torrents_setLocation',
                                             'torrents_set_category',
                                             'torrents_setCategory',
                                             'torrents_set_auto_management',
                                             'torrents_setAutoManagement',
                                             'torrents_toggle_sequential_download',
                                             'torrents_toggleSequentialDownload',
                                             'torrents_toggle_first_last_piece_priority',
                                             'torrents_toggleFirstLastPiecePrio',
                                             'torrents_set_force_start',
                                             'torrents_setForceStart',
                                             'torrents_set_super_seeding',
                                             'torrents_setSuperSeeding']

    def __init__(self, client):
        super(Torrents, self).__init__(client=client)

        for endpoint in self._client_methods_for_multiple_torrents:
            self._add_client_method(endpoint=endpoint, method_class=Torrents._MultipleTorrentsAction)

        self._add_client_method(endpoint='torrents_info', method_class=Torrents._Info)

    class _Info(InteractionLayerMethodOverride):
        """Overrides torrents_info from Client."""
        def __getattr__(self, item):
            try:
                options = {'downloading': {'status_filter': 'downloading'},
                           'completed': {'status_filter': 'compelted'},
                           'paused': {'status_filter': 'paused'},
                           'active': {'status_filter': 'active'},
                           'inactive': {'status_filter': 'inactive'},
                           'resumed': {'status_filter': 'resumed'}}
                kwargs = options[item]
                return InteractionLayerMethodOverride(client=self._client,
                                                      api_entry=getattr(self._client, 'torrents_info'),
                                                      **kwargs)
            except KeyError:
                return super(Torrents._Info, self).__getattr__(item)

    class _MultipleTorrentsAction(InteractionLayerMethodOverride):
        def all(self, *args, **kwargs):
            return self._api_call(hashes='all', *args, **kwargs)


# noinspection PyProtectedMember
class Torrent(InteractionLayer):
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
        >>> torrent.set_location(location='/home/user/torrents/')
        >>> torrent.set_category(category='video')
        >>> # or set them via assignment
        >>> torrent.set_location = '/home/user/torrents/'
        >>> torrent.set_category = 'video'
    """

    _client_method_name = "torrents"

    _attrs_that_trigger_api_update = {'torrents_download_limit': 'torrents_setDownloadLimit',
                                      'torrents_downloadLimit': 'torrents_setDownloadLimit',
                                      'torrents_upload_limit': 'torrents_set_upload_limit',
                                      'torrents_uploadLimit': 'torrents_set_upload_limit',
                                      'torrents_set_location': 'torrents_set_location',
                                      'torrents_setLocation': 'torrents_set_location',
                                      'torrents_set_category': 'torrents_set_category',
                                      'torrents_setCategory': 'torrents_set_category',
                                      'torrents_set_auto_management': 'torrents_set_auto_management',
                                      'torrents_setAutoManagement': 'torrents_set_auto_management',
                                      'torrents_set_force_start': 'torrents_set_force_start',
                                      'torrents_set_super_seeding': 'torrents_set_super_seeding'}

    _client_attributes_to_cache = []

    _client_attributes_as_properties = ['torrents_info',
                                        'torrents_properties',
                                        'torrents_trackers',
                                        'torrents_webseeds',
                                        'torrents_files',
                                        'torrents_piece_states',
                                        'torrents_pieceStates',
                                        'torrents_piece_hashes',
                                        'torrents_pieceHashes',
                                        'torrents_download_limit',
                                        'torrents_downloadLimit',
                                        'torrents_upload_limit',
                                        'torrents_uploadLimit']

    _client_methods_for_single_torrent = Torrents._client_methods_for_single_torrent

    _client_methods_for_multiple_torrents = Torrents._client_methods_for_multiple_torrents

    def __init__(self, data, client):
        super(Torrent, self).__init__(client=client)
        # do not reference '_info' directly outside of __init__ unless it is immediately
        # after Torrent is instantiated. instead, make getattr() calls to self.
        # That way, a new API call is made and stale data is not used.
        self._add_attribute('_info', AttrDict(data))
        self._add_attribute('_hash', self._info['hash'])

        self._add_client_method(endpoint='torrents_info',
                                method_class=Torrent._Info,
                                hashes=self._hash)

        self._add_client_method(endpoint='torrents_properties',
                                method_class=InteractionLayerMethodOverride,
                                hash=self._hash)

        for endpoint in self._client_methods_for_single_torrent:
            self._add_client_method(endpoint=endpoint,
                                    method_class=InteractionLayerMethodOverride,
                                    hash=self._hash)

        for endpoint in self._client_methods_for_multiple_torrents:
            self._add_client_method(endpoint=endpoint,
                                    method_class=Torrent._MultipleTorrentsAction,
                                    hashes=self._hash)

    def __getattr__(self, item):
        """ensures 'info' access still works if calling client.torrents_info()"""
        try:
            return self.info[item]
        except (KeyError, AttributeError):
            pass
        return super(Torrent, self).__getattribute__(item)

    __getitem__ = __getattr__

    def __repr__(self):
        self._add_attribute('_info', self.info)
        return "Torrent hash: %s\n%s" % (self._hash, dict(self._info))

    def __str__(self):
        return str(dict(self.info))

    # noinspection PyProtectedMember
    class _Info(InteractionLayerMethodOverride):
        def __call__(self, *args, **kwargs):
            # torrents_info returns a TorrentInfoList
            info = super(Torrent._Info, self).__call__(*args, **kwargs)
            if len(info) == 1:
                return info[0]._info
            return {}

    class _MultipleTorrentsAction(InteractionLayerMethodOverride):
        def __call__(self, *args, **kwargs):
            multiple_torrent_response = super(Torrent._MultipleTorrentsAction, self).__call__(*args, **kwargs)
            if multiple_torrent_response is not None:
                return multiple_torrent_response[self._default_API_params['hashes']]


# TODO: consider api triggering by setting client.torrent_categories.categories...need to handle both add and create
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
        >>> # delete categories
        >>> client.torrent_categories.removeCategories(categories='Video')
        >>> client.torrent_categories.removeCategories(categories=['Audio', "ISOs"])
    """

    _client_method_name = "torrents"

    _attrs_that_trigger_api_update = {}

    _client_attributes_to_cache = []

    _client_attributes_as_properties = ['torrents_categories']


# TODO: consider trigger API methods
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
    """
    _client_method_name = "rss"

    _attrs_that_trigger_api_update = {}

    _client_attributes_to_cache = []

    _client_attributes_as_properties = ['rss_rules']

    def rss_items_without_data(self):
        return self._client.rss_items(include_feed_data=False)

    def rss_items_with_data(self):
        return self._client.rss_items(include_feed_data=True)


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
        >>> plugins = client.search_plugins
        >>> cats = client.search_categories(plugin_name='...')
        >>> client.search.install_plugin(sources='...')
        >>> client.search.update_plugins()
    """
    _client_method_name = "search"

    _attrs_that_trigger_api_update = {}

    _client_attributes_to_cache = []

    _client_attributes_as_properties = ['search_plugins']


##########################################################################
# Base Objects
##########################################################################
class APIDict(AttrDict):

    def __init__(self, data=None, client=None):
        self._client = client
        super(APIDict, self).__init__(data if data is not None else {})


class ListEntry(APIDict):
    def __init__(self, data=None, client=None, **kwargs):
        self._client = client
        super(ListEntry, self).__init__(data if data is not None else {}, **kwargs)


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
class TorrentPropertiesDict(APIDict):
    pass


class TransferInfoDict(APIDict):
    pass


class SyncMainDataDict(APIDict):
    pass


class SyncTorrentPeersDict(APIDict):
    pass


class ApplicationPreferencesDict(APIDict):

    def __setattr__(self, key, value):
        if key != '_client':
            if key not in self or self[key] != value:
                self._client.app_set_preferences(prefs={key: value})

        super(APIDict, self).__setattr__(key, value)


class BuildInfoDict(APIDict):
    pass


class RssitemsDict(APIDict):
    pass


class RSSRulesDict(APIDict):
    pass


class SearchJobDict(APIDict):
    def __init__(self, data, client):
        if 'id' in data:
            self._search_job_id = data['id']
        super(SearchJobDict, self).__init__(data=data, client=client)

    def stop(self, *args, **kwargs):
        self._client.search.stop(search_id=self._search_job_id, *args, **kwargs)

    def status(self, *args, **kwargs):
        return self._client.search.status(search_id=self._search_job_id, *args, **kwargs)

    def results(self, *args, **kwargs):
        return self._client.search.results(search_id=self._search_job_id, *args, **kwargs)

    def delete(self, *args, **kwargs):
        self._client.search.delete(search_id=self._search_job_id, *args, **kwargs)


class SearchResultsDict(APIDict):
    pass


class TorrentLimitsDict(APIDict):
    pass


class TorrentCategoriesDict(APIDict):
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
        super(TorrentInfoList, self).__init__(list_entiries, entry_class=Torrent, client=client)


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
