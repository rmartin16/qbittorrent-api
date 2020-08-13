from enum import Enum

try:
    from collections import UserList
except ImportError:
    from UserList import UserList

from attrdict import AttrDict


class APINames(Enum):
    """
    API names for API endpoints

    e.g 'torrents' in http://localhost:8080/api/v2/torrents/addTrackers
    """
    Authorization = 'auth'
    Application = 'app'
    Log = 'log'
    Sync = 'sync'
    Transfer = 'transfer'
    Torrents = 'torrents'
    RSS = 'rss'
    Search = 'search'


class ClientCache(object):

    """Caches the client. Subclass this for any object that needs access to the Client."""

    def __init__(self, *args, **kwargs):
        self._client = kwargs.pop('client')
        super(ClientCache, self).__init__(*args, **kwargs)


class Dictionary(ClientCache, AttrDict):

    """Base definition of dictionary-like objects returned from qBittorrent."""

    def __init__(self, data=None, client=None):

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
        super(Dictionary, self).__init__(data or dict(), client=client)
        # allows updating properties that aren't necessarily a part of the AttrDict
        self._setattr('_allow_invalid_attributes', True)


class List(ClientCache, UserList):

    """Base definition for list-like objects returned from qBittorrent."""

    def __init__(self, list_entries=None, entry_class=None, client=None):

        entries = []
        for entry in list_entries:
            if isinstance(entry, dict):
                entries.append(entry_class(data=entry, client=client))
            else:
                entries.append(entry)
        super(List, self).__init__(entries, client=client)


class ListEntry(Dictionary):

    """Base definition for objects within a list returned from qBittorrent."""
