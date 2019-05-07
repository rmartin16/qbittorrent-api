try:
    from collections import UserList
except ImportError:
    from UserList import UserList
from attrdict import AttrDict


# TODO: rename to include whether Dict or List
##########################################################################
# Base Objects
##########################################################################
class APIDict(AttrDict):
    _STR_ATTR = None

    # def __init__(self, data=None, str_attr=""):
    #    if str_attr != "":
    #        self._STR_ATTR = str_attr
    #    super(APIDict, self).__init__(data)


class ListEntry(APIDict):
    pass


class List(UserList):
    def __init__(self, list_entiries=None, entry_class=ListEntry):

        entries = []
        for entry in list_entiries:
            if isinstance(entry, dict):
                entries.append(entry_class(entry))
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
    # STR_ATTR = 'connection_status'


class SyncMainDataDict(APIDict):
    _STR_ATTR = 'rid'


class SyncTorrentPeersDict(APIDict):
    _STR_ATTR = 'rid'


class ApplicationPreferencesDict(APIDict):
    _STR_ATTR = 'autorun_program'


class BuildInfoDict(APIDict):
    pass


class RssitemsDict(APIDict):
    pass


class RSSRulesDict(APIDict):
    pass


class SearchJobDict(APIDict):
    pass


class SearchResultsDict(APIDict):
    pass


class TorrentLimitsDict(APIDict):
    pass


##########################################################################
# List Objects
##########################################################################
class TorrentFilesList(List):
    def __init__(self, list_entiries=None):
        super(TorrentFilesList, self).__init__(list_entiries, entry_class=TorrentFile)


class TorrentFile(ListEntry):
    pass


class WebSeedsList(List):
    def __init__(self, list_entiries=None):
        super(WebSeedsList, self).__init__(list_entiries, entry_class=WebSeed)


class WebSeed(ListEntry):
    pass


class TrackersList(List):
    def __init__(self, list_entiries=None):
        super(TrackersList, self).__init__(list_entiries, entry_class=Tracker)


class Tracker(ListEntry):
    pass


class TorrentInfoList(List):
    def __init__(self, list_entiries=None):
        super(TorrentInfoList, self).__init__(list_entiries, entry_class=Torrent)


class Torrent(ListEntry):
    pass


class LogPeersList(List):
    def __init__(self, list_entiries=None):
        super(LogPeersList, self).__init__(list_entiries, entry_class=LogPeer)


class LogPeer(ListEntry):
    pass


class LogMainList(List):
    def __init__(self, list_entiries=None):
        super(LogMainList, self).__init__(list_entiries, entry_class=LogEntry)


class LogEntry(ListEntry):
    pass


class TorrentPieceInfoList(List):
    def __init__(self, list_entiries=None):
        super(TorrentPieceInfoList, self).__init__(list_entiries, entry_class=TorrentPieceData)


class TorrentPieceData(ListEntry):
    pass


class TorrentCategoriesList(List):
    def __init__(self, list_entiries=None):
        super(TorrentCategoriesList, self).__init__(list_entiries, entry_class=TorrentCategory)


class TorrentCategory(ListEntry):
    pass


class SearchStatusesList(List):
    def __init__(self, list_entiries=None):
        super(SearchStatusesList, self).__init__(list_entiries, entry_class=SearchStatus)


class SearchStatus(ListEntry):
    pass


class SearchCategoriesList(List):
    def __init__(self, list_entiries=None):
        super(SearchCategoriesList, self).__init__(list_entiries, entry_class=SearchCategory)


class SearchCategory(ListEntry):
    pass


class SearchPluginsList(List):
    def __init__(self, list_entiries=None):
        super(SearchPluginsList, self).__init__(list_entiries, entry_class=SearchPlugin)


class SearchPlugin(ListEntry):
    pass
