from __future__ import annotations

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    ClientCache,
    List,
    ListEntry,
    ListInputT,
)


class LogPeer(ListEntry):
    """Item in :class:`LogPeersList`"""


class LogPeersList(List[LogPeer]):
    """Response for :meth:`~LogAPIMixIn.log_peers`"""

    def __init__(self, list_entries: ListInputT, client: LogAPIMixIn | None = None):
        super().__init__(list_entries, entry_class=LogPeer)


class LogEntry(ListEntry):
    """Item in :class:`LogMainList`"""


class LogMainList(List[LogEntry]):
    """Response to :meth:`~LogAPIMixIn.log_main`"""

    def __init__(self, list_entries: ListInputT, client: LogAPIMixIn | None = None):
        super().__init__(list_entries, entry_class=LogEntry)


class LogAPIMixIn(AppAPIMixIn):
    """
    Implementation of all ``Log`` API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> client.log_main(info=False)
        >>> client.log_peers()
    """  # noqa: E501

    @property
    def log(self) -> Log:
        """
        Allows for transparent interaction with Log endpoints.

        See Log class for usage.
        """
        if self._log is None:
            self._log = Log(client=self)
        return self._log

    def log_main(
        self,
        normal: bool | None = None,
        info: bool | None = None,
        warning: bool | None = None,
        critical: bool | None = None,
        last_known_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> LogMainList:
        """
        Retrieve the qBittorrent log entries. Iterate over returned object.

        :param normal: False to exclude ``normal`` entries
        :param info: False to exclude ``info`` entries
        :param warning: False to exclude ``warning`` entries
        :param critical: False to exclude ``critical`` entries
        :param last_known_id: only entries with an ID greater than this value will be
            returned
        """
        params = {
            "normal": None if normal is None else bool(normal),
            "info": None if info is None else bool(info),
            "warning": None if warning is None else bool(warning),
            "critical": None if critical is None else bool(critical),
            "last_known_id": last_known_id,
        }
        return self._get_cast(
            _name=APINames.Log,
            _method="main",
            params=params,
            response_class=LogMainList,
            **kwargs,
        )

    def log_peers(
        self,
        last_known_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> LogPeersList:
        """
        Retrieve qBittorrent peer log.

        :param last_known_id: only entries with an ID greater than this value will be
            returned
        """
        params = {"last_known_id": last_known_id}
        return self._get_cast(
            _name=APINames.Log,
            _method="peers",
            params=params,
            response_class=LogPeersList,
            **kwargs,
        )


class Log(ClientCache[LogAPIMixIn]):
    """
    Allows interaction with ``Log`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # this is all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'log_' prepended)
        >>> log_list = client.log.main()
        >>> peers_list = client.log.peers(last_known_id="...")
        >>> # can also filter log down with additional attributes
        >>> log_info = client.log.main.info(last_known_id=1)
        >>> log_warning = client.log.main.warning(last_known_id=1)
    """  # noqa: E501

    def __init__(self, client: LogAPIMixIn):
        super().__init__(client=client)
        self._main = Log.Main(client=client)

    def peers(
        self,
        last_known_id: str | int | None = None,
        **kwargs: APIKwargsT,
    ) -> LogPeersList:
        """Implements :meth:`~LogAPIMixIn.log_peers`."""
        return self._client.log_peers(last_known_id=last_known_id, **kwargs)

    class Main(ClientCache["LogAPIMixIn"]):
        def _api_call(
            self,
            normal: bool | None = None,
            info: bool | None = None,
            warning: bool | None = None,
            critical: bool | None = None,
            last_known_id: str | int | None = None,
            **kwargs: APIKwargsT,
        ) -> LogMainList:
            return self._client.log_main(
                normal=normal,
                info=info,
                warning=warning,
                critical=critical,
                last_known_id=last_known_id,
                **kwargs,
            )

        def __call__(
            self,
            normal: bool | None = True,
            info: bool | None = True,
            warning: bool | None = True,
            critical: bool | None = True,
            last_known_id: str | int | None = None,
            **kwargs: APIKwargsT,
        ) -> LogMainList:
            """Implements :meth:`~LogAPIMixIn.log_main`."""
            return self._api_call(
                normal=normal,
                info=info,
                warning=warning,
                critical=critical,
                last_known_id=last_known_id,
                **kwargs,
            )

        def info(
            self,
            last_known_id: str | int | None = None,
            **kwargs: APIKwargsT,
        ) -> LogMainList:
            """Implements :meth:`~LogAPIMixIn.log_main`."""
            return self._api_call(last_known_id=last_known_id, **kwargs)

        def normal(
            self,
            last_known_id: str | int | None = None,
            **kwargs: APIKwargsT,
        ) -> LogMainList:
            """Implements :meth:`~LogAPIMixIn.log_main` with ``info=False``."""
            return self._api_call(info=False, last_known_id=last_known_id, **kwargs)

        def warning(
            self,
            last_known_id: str | int | None = None,
            **kwargs: APIKwargsT,
        ) -> LogMainList:
            """Implements :meth:`~LogAPIMixIn.log_main` with ``info=False`` and
            ``normal=False``."""
            return self._api_call(
                info=False,
                normal=False,
                last_known_id=last_known_id,
                **kwargs,
            )

        def critical(
            self,
            last_known_id: str | int | None = None,
            **kwargs: APIKwargsT,
        ) -> LogMainList:
            """Implements :meth:`~LogAPIMixIn.log_main` with ``info=False``,
            ``normal=False``, and ``warning=False``."""
            return self._api_call(
                info=False,
                normal=False,
                warning=False,
                last_known_id=last_known_id,
                **kwargs,
            )

    @property
    def main(self) -> Log.Main:
        """Implements :meth:`~LogAPIMixIn.log_main`."""
        return self._main
