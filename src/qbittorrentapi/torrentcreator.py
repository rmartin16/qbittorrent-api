from __future__ import annotations

import enum
import os
from collections.abc import Mapping
from typing import Any, Literal, cast

from qbittorrentapi.app import AppAPIMixIn
from qbittorrentapi.definitions import (
    APIKwargsT,
    APINames,
    ClientCache,
    Dictionary,
    JsonValueT,
    List,
    ListEntry,
    ListInputT,
)


class TaskStatus(enum.Enum):
    """Enumeration of possible task statuses."""

    FAILED = "Failed"
    QUEUED = "Queued"
    RUNNING = "Running"
    FINISHED = "Finished"


class TorrentCreatorTaskStatus(ListEntry):
    """
    Item in :class:`TorrentCreatorTaskStatusList`

    Definition: not documented...yet
    """


class TorrentCreatorTaskStatusList(List[TorrentCreatorTaskStatus]):
    """Response for :meth:`~TorrentCreatorAPIMixIn.torrentcreator_status`"""

    def __init__(
        self, list_entries: ListInputT, client: TorrentCreatorAPIMixIn | None = None
    ):
        super().__init__(
            list_entries, entry_class=TorrentCreatorTaskStatus, client=client
        )


class TorrentCreatorAPIMixIn(AppAPIMixIn):
    """
    Implementation of all ``TorrentCreator`` API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> task = client.torrentcreator_add_task(source_path="/path/to/data")
        >>> if TaskStatus(task.status().status) == TaskStatus.FINISHED:
        >>>     torrent_data = task.torrent_file()
        >>> task.delete()
        >>> # or
        >>> client.torrentcreator_delete_task(task_id=task.taskID)
    """  # noqa: E501

    @property
    def torrentcreator(self) -> TorrentCreator:
        """
        Allows for transparent interaction with TorrentCreator endpoints.

        See TorrentCreator class for usage.
        """
        if self._torrentcreator is None:
            self._torrentcreator = TorrentCreator(client=self)
        return self._torrentcreator

    def torrentcreator_add_task(
        self,
        source_path: str | os.PathLike[Any] | None = None,
        torrent_file_path: str | os.PathLike[Any] | None = None,
        format: Literal["v1", "v2", "hybrid"] | None = None,
        start_seeding: bool | None = None,
        is_private: bool | None = None,
        optimize_alignment: bool | None = None,
        padded_file_size_limit: int | None = None,
        piece_size: int | None = None,
        comment: str | None = None,
        trackers: str | list[str] | None = None,
        url_seeds: str | list[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentCreatorTaskDictionary:
        """
        Add a task to create a new torrent.

        This method was introduced with qBittorrent v5.0.0 (Web API v2.10.4).

        :raises Conflict409Error: too many existing torrent creator tasks
        :param source_path: source file path for torrent content
        :param torrent_file_path: file path to save torrent
        :param format: BitTorrent V1 or V2; defaults to "hybrid" format if None
        :param start_seeding: should qBittorrent start seeding this torrent?
        :param is_private: is the torrent private or not?
        :param optimize_alignment: should optimized alignment be enforced for new
            torrent?
        :param padded_file_size_limit: size limit for padding files
        :param piece_size: size of the pieces
        :param comment: comment
        :param trackers: list of trackers to add
        :param url_seeds: list of URLs seeds to add
        """
        data = {
            "sourcePath": source_path,
            "torrentFilePath": (
                os.fsdecode(torrent_file_path) if torrent_file_path else None
            ),
            "format": format,
            "private": None if is_private is None else bool(is_private),
            "optimizeAlignment": (
                None if optimize_alignment is None else bool(optimize_alignment)
            ),
            "startSeeding": None if start_seeding is None else bool(start_seeding),
            "paddedFileSizeLimit": padded_file_size_limit,
            "pieceSize": piece_size,
            "comment": comment,
            "trackers": self._list2string(trackers),
            "urlSeeds": self._list2string(url_seeds),
        }

        return self._post_cast(
            _name=APINames.TorrentCreator,
            _method="addTask",
            data=data,
            response_class=TorrentCreatorTaskDictionary,
            version_introduced="2.10.4",
            **kwargs,
        )

    torrentcreator_addTask = torrentcreator_add_task

    def torrentcreator_status(
        self,
        task_id: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentCreatorTaskStatusList:
        """
        Status for a torrent creation task.

        This method was introduced with qBittorrent v5.0.0 (Web API v2.10.4).

        :raises NotFound404Error: task not found
        :param task_id: ID of torrent creation task
        """
        data = {"taskID": task_id}

        return self._post_cast(
            _name=APINames.TorrentCreator,
            _method="status",
            data=data,
            response_class=TorrentCreatorTaskStatusList,
            version_introduced="2.10.4",
            **kwargs,
        )

    def torrentcreator_torrent_file(
        self,
        task_id: str | None = None,
        **kwargs: APIKwargsT,
    ) -> bytes:
        """
        Retrieve torrent file for created torrent.

        This method was introduced with qBittorrent v5.0.0 (Web API v2.10.4).

        :raises NotFound404Error: task not found
        :raises Conflict409Error: torrent creation is not finished or failed
        :param task_id: ID of torrent creation task
        """
        data = {"taskID": task_id}

        return self._post_cast(
            _name=APINames.TorrentCreator,
            _method="torrentFile",
            data=data,
            response_class=bytes,
            version_introduced="2.10.4",
            **kwargs,
        )

    torrentcreator_torrentFile = torrentcreator_torrent_file

    def torrentcreator_delete_task(
        self,
        task_id: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Delete a torrent creation task.

        This method was introduced with qBittorrent v5.0.0 (Web API v2.10.4).

        :raises NotFound404Error: task not found
        :param task_id: ID of torrent creation task
        """
        data = {"taskID": task_id}

        self._post(
            _name=APINames.TorrentCreator,
            _method="deleteTask",
            data=data,
            version_introduced="2.10.4",
            **kwargs,
        )

    torrentcreator_deleteTask = torrentcreator_delete_task


class TorrentCreatorTaskDictionary(
    ClientCache[TorrentCreatorAPIMixIn], Dictionary[JsonValueT]
):
    """Response for :meth:`~TorrentCreatorAPIMixIn.torrentcreator_add_task`"""

    def __init__(self, data: Mapping[str, JsonValueT], client: TorrentCreatorAPIMixIn):
        self.task_id: str | None = cast(str, data.get("taskID", None))
        super().__init__(data=data, client=client)

    def status(self, **kwargs: APIKwargsT) -> TorrentCreatorTaskStatus:
        """Implements :meth:`~TorrentCreatorAPIMixIn.torrentcreator_status`."""
        return self._client.torrentcreator_status(task_id=self.task_id, **kwargs)[0]

    def torrent_file(self, **kwargs: APIKwargsT) -> bytes:
        """Implements :meth:`~TorrentCreatorAPIMixIn.torrentcreator_torrent_file`."""
        return self._client.torrentcreator_torrent_file(task_id=self.task_id, **kwargs)

    torrentFile = torrent_file

    def delete(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~TorrentCreatorAPIMixIn.torrentcreator_delete_task`."""
        return self._client.torrentcreator_delete_task(task_id=self.task_id, **kwargs)


class TorrentCreator(ClientCache[TorrentCreatorAPIMixIn]):
    """
    Allows interaction with ``TorrentCreator`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> # this is all the same attributes that are available as named in the
        >>> #  endpoints or the more pythonic names in Client (with or without 'torrentcreator_' prepended)
        >>> task = client.torrentcreator.add_task(source_path="/path/to/data")
        >>> if TaskStatus(task.status().status) == TaskStatus.FINISHED:
        >>>     torrent_data = task.torrent_file()
        >>> task.delete()
        >>> # or
        >>> client.torrentcreator.delete_task(task_id=task.taskID)
    """  # noqa: E501

    def add_task(
        self,
        source_path: str | os.PathLike[Any] | None = None,
        torrent_file_path: str | os.PathLike[Any] | None = None,
        format: Literal["v1", "v2", "hybrid"] | None = None,
        start_seeding: bool | None = None,
        is_private: bool | None = None,
        optimize_alignment: bool | None = None,
        padded_file_size_limit: int | None = None,
        piece_size: int | None = None,
        comment: str | None = None,
        trackers: str | list[str] | None = None,
        url_seeds: str | list[str] | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentCreatorTaskDictionary:
        """Implements :meth:`~TorrentCreatorAPIMixIn.torrentcreator_add_task`."""
        return self._client.torrentcreator_add_task(
            source_path=source_path,
            torrent_file_path=torrent_file_path,
            format=format,
            start_seeding=start_seeding,
            is_private=is_private,
            optimize_alignment=optimize_alignment,
            padded_file_size_limit=padded_file_size_limit,
            piece_size=piece_size,
            comment=comment,
            trackers=trackers,
            url_seeds=url_seeds,
            **kwargs,
        )

    addTask = add_task

    def status(
        self,
        task_id: str | None = None,
        **kwargs: APIKwargsT,
    ) -> TorrentCreatorTaskStatusList:
        """Implements :meth:`~TorrentCreatorAPIMixIn.torrentcreator_status`."""
        return self._client.torrentcreator_status(task_id=task_id, **kwargs)

    def torrent_file(
        self,
        task_id: str | None = None,
        **kwargs: APIKwargsT,
    ) -> bytes:
        """Implements :meth:`~TorrentCreatorAPIMixIn.torrentcreator_torrent_file`."""
        return self._client.torrentcreator_torrent_file(task_id=task_id, **kwargs)

    torrentFile = torrent_file

    def delete_task(
        self,
        task_id: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~TorrentCreatorAPIMixIn.torrentcreator_delete_task`."""
        self._client.torrentcreator_delete_task(task_id=task_id, **kwargs)

    deleteTask = delete_task
