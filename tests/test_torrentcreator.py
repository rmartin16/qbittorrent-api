import sys
from pathlib import Path

import pytest

from qbittorrentapi import APINames
from qbittorrentapi.exceptions import NotFound404Error
from qbittorrentapi.torrentcreator import (
    TaskStatus,
    TorrentCreatorTaskDictionary,
    TorrentCreatorTaskStatus,
    TorrentCreatorTaskStatusList,
)
from tests.utils import check


@pytest.fixture
def task(client) -> TorrentCreatorTaskDictionary:
    source_path = Path(Path.cwd() / "tests/_resources/test_torrent")
    source_path.mkdir(parents=True, exist_ok=True)
    test_file = source_path / "test-file"
    test_file.touch()
    with test_file.open("w") as f:
        f.write("hello world")

    yield (
        task := client.torrentcreator_add_task(
            source_path=Path("/tmp/_resources/test_torrent"), start_seeding=False
        )
    )

    task.delete()
    test_file.unlink()
    source_path.rmdir()


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    namespace = APINames.TorrentCreator
    all_dotted_methods = set(dir(getattr(client, namespace)))

    for meth in [meth for meth in dir(client) if meth.startswith(f"{namespace}_")]:
        assert meth.removeprefix(f"{namespace}_") in all_dotted_methods


@pytest.mark.skipif_before_api_version("2.10.4")
@pytest.mark.parametrize(
    "add_task_func",
    [
        "torrentcreator_add_task",
        "torrentcreator_addTask",
        "torrentcreator.add_task",
        "torrentcreator.addTask",
    ],
)
def test_add_task(client, add_task_func):
    task = client.func(add_task_func)(source_path="/empty-dir", start_seeding=False)

    assert isinstance(task, TorrentCreatorTaskDictionary)
    assert task.taskID
    assert task.task_id


@pytest.mark.skipif_after_api_version("2.10.4")
@pytest.mark.parametrize(
    "add_task_func",
    [
        "torrentcreator_add_task",
        "torrentcreator_addTask",
        "torrentcreator.add_task",
        "torrentcreator.addTask",
    ],
)
def test_add_task_not_implemented(client, add_task_func):
    with pytest.raises(NotImplementedError):
        client.func(add_task_func)()


@pytest.mark.skipif_before_api_version("2.10.4")
@pytest.mark.parametrize(
    "status_func", ["torrentcreator_status", "torrentcreator.status"]
)
def test_status(client, status_func, task):
    assert isinstance(
        client.func(status_func)(task_id=task.task_id), TorrentCreatorTaskStatusList
    )
    assert isinstance(
        client.func(status_func)(task_id=task.task_id)[0], TorrentCreatorTaskStatus
    )
    assert isinstance(task.status(), TorrentCreatorTaskStatus)
    assert TaskStatus(task.status().status) in TaskStatus


@pytest.mark.skipif_after_api_version("2.10.4")
@pytest.mark.parametrize(
    "status_func", ["torrentcreator_status", "torrentcreator.status"]
)
def test_status_not_implemented(client, status_func):
    with pytest.raises(NotImplementedError):
        client.func(status_func)()


def test_status_enum():
    assert TaskStatus("Failed") is TaskStatus.FAILED
    assert TaskStatus("Queued") is TaskStatus.QUEUED
    assert TaskStatus("Running") is TaskStatus.RUNNING
    assert TaskStatus("Finished") is TaskStatus.FINISHED


@pytest.mark.skipif_before_api_version("2.10.4")
@pytest.mark.parametrize(
    "torrent_file_func", ["torrentcreator_torrent_file", "torrentcreator.torrent_file"]
)
def test_torrent_file(client, torrent_file_func, task):
    check(lambda: TaskStatus(task.status().status), [TaskStatus.FINISHED])
    assert isinstance(client.func(torrent_file_func)(task_id=task.task_id), bytes)
    assert isinstance(task.torrent_file(), bytes)
    assert isinstance(task.torrentFile(), bytes)


@pytest.mark.skipif_after_api_version("2.10.4")
@pytest.mark.parametrize(
    "torrent_file_func", ["torrentcreator_torrent_file", "torrentcreator.torrent_file"]
)
def test_torrent_file_not_implemented(client, torrent_file_func):
    with pytest.raises(NotImplementedError):
        client.func(torrent_file_func)()


@pytest.mark.skipif_before_api_version("2.10.4")
@pytest.mark.parametrize(
    "torrent_delete_func", ["torrentcreator_delete_task", "torrentcreator.delete_task"]
)
def test_delete(client, torrent_delete_func):
    task = client.torrentcreator_add_task(source_path="/empty-dir", start_seeding=False)
    task.delete()
    with pytest.raises(NotFound404Error):
        task.status()

    task = client.torrentcreator_add_task(source_path="/empty-dir", start_seeding=False)
    client.func(torrent_delete_func)(task_id=task.task_id)
    with pytest.raises(NotFound404Error):
        client.func(torrent_delete_func)(task_id=task.task_id)


@pytest.mark.skipif_after_api_version("2.10.4")
@pytest.mark.parametrize(
    "torrent_delete_func", ["torrentcreator_delete_task", "torrentcreator.delete_task"]
)
def test_delete_not_implemented(client, torrent_delete_func):
    with pytest.raises(NotImplementedError):
        client.func(torrent_delete_func)()
