from __future__ import annotations

from collections.abc import Iterable, Mapping
from json import dumps
from typing import Any

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    ClientCache,
    Dictionary,
    JsonValueT,
)


class ClientDataDictionary(Dictionary[JsonValueT]):
    """Response for :meth:`~ClientDataAPIMixIn.clientdata_load`"""


class ClientDataAPIMixIn(AppAPIMixIn):
    """
    Implementation of all ``ClientData`` API methods.

    qBittorrent persists arbitrary key/value data on behalf of a Web API client;
    the WebUI uses it to store its own preferences.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> client.clientdata_store(data={"my_app": {"theme": "dark"}})
        >>> stored = client.clientdata_load(keys=["my_app"])
    """  # noqa: E501

    @property
    def clientdata(self) -> ClientData:
        """
        Allows for transparent interaction with ``ClientData`` endpoints.

        See ClientData class for usage.
        """
        if self._clientdata is None:
            self._clientdata = ClientData(client=self)
        return self._clientdata

    def clientdata_load(
        self,
        keys: Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> ClientDataDictionary:
        """
        Retrieve stored client data.

        This method was introduced with qBittorrent v5.2.0 (Web API v2.13.1).

        :raises InvalidRequest400Error: if ``keys`` is not a list of strings

        :param keys: keys to retrieve; omit for all stored data
        """
        params = {
            "keys": (
                None if keys is None else dumps(list(keys), separators=(",", ":"))
            ),
        }
        return self._get_cast(
            _name=APINames.ClientData,
            _method="load",
            params=params,
            response_class=ClientDataDictionary,
            version_introduced="2.13.1",
            **kwargs,
        )

    def clientdata_store(
        self,
        data: Mapping[str, Any] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Store client data.

        This method was introduced with qBittorrent v5.2.0 (Web API v2.13.1).

        :raises InvalidRequest400Error: if ``data`` is not an object
        :raises Conflict409Error: if the data cannot be stored

        :param data: mapping of keys to values to store
        """
        post_data = {"data": dumps(data or {}, separators=(",", ":"))}
        self._post(
            _name=APINames.ClientData,
            _method="store",
            data=post_data,
            version_introduced="2.13.1",
            **kwargs,
        )


class ClientData(ClientCache[ClientDataAPIMixIn]):
    """
    Allows interaction with ``ClientData`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> client.clientdata.store(data={"my_app": {"theme": "dark"}})
        >>> stored = client.clientdata.load(keys=["my_app"])
    """  # noqa: E501

    def load(
        self,
        keys: Iterable[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> ClientDataDictionary:
        """Implements :meth:`~ClientDataAPIMixIn.clientdata_load`."""
        return self._client.clientdata_load(keys=keys, **kwargs)

    def store(
        self,
        data: Mapping[str, Any] | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~ClientDataAPIMixIn.clientdata_store`."""
        self._client.clientdata_store(data=data, **kwargs)
