from attrdict import AttrDict

from qbittorrentapi.decorators import Alias
from qbittorrentapi.decorators import aliased

try:
    from collections import UserList
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from UserList import UserList


##########################################################################
# Base Objects
##########################################################################
class Dictionary(AttrDict):
    def __init__(self, data=None, client=None):
        self._client = client

        # iterate through a dictionary converting any nested dictionaries to AttrDicts
        def convert_dict_values_to_attrdicts(d):
            converted_dict = AttrDict()
            if isinstance(d, dict):
                for key, value in d.items():
                    # if the value is a dictionary, convert it to a AttrDict
                    if isinstance(value, dict):
                        # recursively send each value to convert its dictionary children
                        converted_dict[key] = convert_dict_values_to_attrdicts(AttrDict(value))
                    else:
                        converted_dict[key] = value
                return converted_dict

        data = convert_dict_values_to_attrdicts(data)
        super(Dictionary, self).__init__(data if data is not None else dict())


class ListEntry(Dictionary):
    def __init__(self, data=None, client=None, **kwargs):
        self._client = client
        super(ListEntry, self).__init__(data, **kwargs)


class List(UserList):
    def __init__(self, list_entries=None, entry_class=None, client=None):
        self._client = client

        entries = []
        for entry in list_entries:
            if isinstance(entry, dict):
                entries.append(entry_class(data=entry, client=client))
            else:
                entries.append(entry)
        super(List, self).__init__(entries)


##########################################################################
# Dictionary Objects
##########################################################################
class SearchJobDictionary(Dictionary):
    def __init__(self, data, client):
        if 'id' in data:
            self._search_job_id = data.get('id', None)
        super(SearchJobDictionary, self).__init__(data=data, client=client)

    def stop(self, **kwargs):
        return self._client.search.stop(search_id=self._search_job_id, **kwargs)

    def status(self, **kwargs):
        return self._client.search.status(search_id=self._search_job_id, **kwargs)

    def results(self, limit=None, offset=None, **kwargs):
        return self._client.search.results(limit=limit, offset=offset, search_id=self._search_job_id, **kwargs)

    def delete(self, **kwargs):
        return self._client.search.delete(search_id=self._search_job_id, **kwargs)


@aliased
class TorrentDictionary(Dictionary):
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
        self._hash = data.get('hash', None)
        super(TorrentDictionary, self).__init__(data, client)

    @property
    def info(self):
        info = self._client.torrents_info(hashes=self._hash)
        if len(info) == 1:
            return info[0]
        return AttrDict()

    def resume(self, **kwargs):
        return self._client.torrents_resume(hashes=self._hash, **kwargs)

    def pause(self, **kwargs):
        return self._client.torrents_pause(hashes=self._hash, **kwargs)

    def delete(self, delete_files=None, **kwargs):
        return self._client.torrents_delete(delete_files=delete_files, hashes=self._hash, **kwargs)

    def recheck(self, **kwargs):
        return self._client.torrents_recheck(hashes=self._hash, **kwargs)

    def reannounce(self, **kwargs):
        return self._client.torrents_reannounce(hashes=self._hash, **kwargs)

    @Alias('increasePrio')
    def increase_priority(self, **kwargs):
        return self._client.torrents_increase_priority(hashes=self._hash, **kwargs)

    @Alias('decreasePrio')
    def decrease_priority(self, **kwargs):
        return self._client.torrents_decrease_priority(hashes=self._hash, **kwargs)

    @Alias('topPrio')
    def top_priority(self, **kwargs):
        return self._client.torrents_top_priority(hashes=self._hash, **kwargs)

    @Alias('bottomPrio')
    def bottom_priority(self, **kwargs):
        return self._client.torrents_bottom_priority(hashes=self._hash, **kwargs)

    @Alias('setShareLimits')
    def set_share_limits(self, ratio_limit=None, seeding_time_limit=None, **kwargs):
        return self._client.torrents_set_share_limits(ratio_limit=ratio_limit, seeding_time_limit=seeding_time_limit,
                                                      hashes=self._hash, **kwargs)

    @property
    def download_limit(self, **kwargs):
        return self._client.torrents_download_limit(hashes=self._hash, **kwargs)
    downloadLimit = download_limit

    @downloadLimit.setter
    def downloadLimit(self, v): self.download_limit(limit=v)
    @download_limit.setter
    def download_limit(self, v):
        self.set_download_limit(limit=v)

    @Alias('setDownloadLimit')
    def set_download_limit(self, limit=None, **kwargs):
        return self._client.torrents_set_download_limit(limit=limit, hashes=self._hash, **kwargs)

    @property
    def upload_limit(self, **kwargs):
        return self._client.torrents_set_upload_limit(hashes=self._hash, **kwargs)
    uploadLimit = upload_limit

    @uploadLimit.setter
    def uploadLimit(self, v): self.set_upload_limit(limit=v)
    @upload_limit.setter
    def upload_limit(self, v):
        self.set_upload_limit(limit=v)

    @Alias('setUploadLimit')
    def set_upload_limit(self, limit=None, **kwargs):
        return self._client.torrents_set_upload_limit(limit=limit, hashes=self._hash, **kwargs)

    @Alias('setLocation')
    def set_location(self, location=None, **kwargs):
        return self._client.torrents_set_location(location=location, hashes=self._hash, **kwargs)

    @Alias('setCategory')
    def set_category(self, category=None, **kwargs):
        return self._client.torrents_set_category(category=category, hashes=self._hash, **kwargs)

    @Alias('setAutoManagemnt')
    def set_auto_management(self, enable=None, **kwargs):
        return self._client.torrents_set_auto_management(enable=enable, hashes=self._hash, **kwargs)

    @Alias('toggleSequentialDownload')
    def toggle_sequential_download(self, **kwargs):
        return self._client.torrents_toggle_sequential_download(hashes=self._hash, **kwargs)

    @Alias('toggleFirstLastPiecePrio')
    def toggle_first_last_piece_priority(self, **kwargs):
        return self._client.torrents_toggle_first_last_piece_priority(hashes=self._hash, **kwargs)

    @Alias('setForceStart')
    def set_force_start(self, enable=None, **kwargs):
        return self._client.torrents_set_force_start(enable=enable, hashes=self._hash, **kwargs)

    @Alias('setSuperSeeding')
    def set_super_seeding(self, enable=None, **kwargs):
        return self._client.torrents_set_super_seeding(enable=enable, hashes=self._hash, **kwargs)

    @property
    def properties(self):
        return self._client.torrents_properties(hash=self._hash)

    @property
    def trackers(self):
        return self._client.torrents_trackers(hash=self._hash)

    @trackers.setter
    def trackers(self, v):
        self.add_trackers(urls=v)

    @property
    def webseeds(self):
        return self._client.torrents_webseeds(hash=self._hash)

    @property
    def files(self):
        return self._client.torrents_files(hash=self._hash)

    @property
    def piece_states(self):
        return self._client.torrents_piece_states(hash=self._hash)
    pieceStates = piece_states

    @property
    def piece_hashes(self):
        return self._client.torrents_piece_hashes(hash=self._hash)
    pieceHashes = piece_hashes

    @Alias('addTrackers')
    def add_trackers(self, urls=None, **kwargs):
        return self._client.torrents_add_trackers(hash=self._hash, urls=urls, **kwargs)

    @Alias('editTracker')
    def edit_tracker(self, orig_url=None, new_url=None, **kwargs):
        return self._client.torrents_edit_tracker(hash=self._hash, original_url=orig_url, new_url=new_url, **kwargs)

    @Alias('removeTrackers')
    def remove_trackers(self, urls=None, **kwargs):
        return self._client.torrents_remove_trackers(hash=self._hash, urls=urls, **kwargs)

    @Alias('filePriority')
    def file_priority(self, file_ids=None, priority=None, **kwargs):
        return self._client.torrents_file_priority(hash=self._hash, file_ids=file_ids, priority=priority, **kwargs)

    def rename(self, new_name=None, **kwargs):
        return self._client.torrents_rename(hash=self._hash, new_torrent_name=new_name, **kwargs)

    @Alias('addTags')
    def add_tags(self, tags=None, **kwargs):
        return self._client.torrents_add_tags(hashes=self._hash, tags=tags, **kwargs)

    @Alias('removeTags')
    def remove_tags(self, tags=None, **kwargs):
        return self._client.torrents_remove_tags(hashes=self._hash, tags=tags, **kwargs)


class TorrentPropertiesDictionary(Dictionary):
    pass


class TransferInfoDictionary(Dictionary):
    pass


class SyncMainDataDictionary(Dictionary):
    pass


class SyncTorrentPeersDictionary(Dictionary):
    pass


class ApplicationPreferencesDictionary(Dictionary):
    pass


class BuildInfoDictionary(Dictionary):
    pass


class RSSitemsDictionary(Dictionary):
    pass


class RSSRulesDictionary(Dictionary):
    pass


class SearchResultsDictionary(Dictionary):
    pass


class TorrentLimitsDictionary(Dictionary):
    pass


class TorrentCategoriesDictionary(Dictionary):
    pass


class TorrentsAddPeersDictionary(Dictionary):
    pass


##########################################################################
# List Objects
##########################################################################
class TorrentFilesList(List):
    def __init__(self, list_entries=None, client=None):
        super(TorrentFilesList, self).__init__(list_entries, entry_class=TorrentFile, client=client)


class TorrentFile(ListEntry):
    pass


class WebSeedsList(List):
    def __init__(self, list_entries=None, client=None):
        super(WebSeedsList, self).__init__(list_entries, entry_class=WebSeed, client=client)


class WebSeed(ListEntry):
    pass


class TrackersList(List):
    def __init__(self, list_entries=None, client=None):
        super(TrackersList, self).__init__(list_entries, entry_class=Tracker, client=client)


class Tracker(ListEntry):
    pass


class TorrentInfoList(List):
    def __init__(self, list_entries=None, client=None):
        super(TorrentInfoList, self).__init__(list_entries, entry_class=TorrentDictionary, client=client)


class LogPeersList(List):
    def __init__(self, list_entries=None, client=None):
        super(LogPeersList, self).__init__(list_entries, entry_class=LogPeer, client=client)


class LogPeer(ListEntry):
    pass


class LogMainList(List):
    def __init__(self, list_entries=None, client=None):
        super(LogMainList, self).__init__(list_entries, entry_class=LogEntry, client=client)


class LogEntry(ListEntry):
    pass


class TorrentPieceInfoList(List):
    def __init__(self, list_entries=None, client=None):
        super(TorrentPieceInfoList, self).__init__(list_entries, entry_class=TorrentPieceData, client=client)


class TorrentPieceData(ListEntry):
    pass


class TorrentCategoriesList(List):
    def __init__(self, list_entries=None, client=None):
        super(TorrentCategoriesList, self).__init__(list_entries, entry_class=TorrentCategory, client=client)


class TorrentCategory(ListEntry):
    pass


class SearchStatusesList(List):
    def __init__(self, list_entries=None, client=None):
        super(SearchStatusesList, self).__init__(list_entries, entry_class=SearchStatus, client=client)


class SearchStatus(ListEntry):
    pass


class SearchCategoriesList(List):
    def __init__(self, list_entries=None, client=None):
        super(SearchCategoriesList, self).__init__(list_entries, entry_class=SearchCategory, client=client)


class SearchCategory(ListEntry):
    pass


class SearchPluginsList(List):
    def __init__(self, list_entries=None, client=None):
        super(SearchPluginsList, self).__init__(list_entries, entry_class=SearchPlugin, client=client)


class SearchPlugin(ListEntry):
    pass


class TagList(List):
    def __init__(self, list_entries=None, client=None):
        super(TagList, self).__init__(list_entries, entry_class=Tag, client=client)


class Tag(ListEntry):
    pass
