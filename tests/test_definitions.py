from enum import Enum

import pytest

from qbittorrentapi._attrdict import AttrDict
from qbittorrentapi.definitions import (
    Dictionary,
    List,
    ListEntry,
    TorrentState,
    TrackerStatus,
)

torrent_all_states = [
    "error",
    "missingFiles",
    "uploading",
    "pausedUP",
    "stoppedUP",
    "queuedUP",
    "stalledUP",
    "checkingUP",
    "forcedUP",
    "allocating",
    "downloading",
    "metaDL",
    "forcedMetaDL",
    "pausedDL",
    "stoppedDL",
    "queuedDL",
    "forcedDL",
    "stalledDL",
    "checkingDL",
    "checkingResumeData",
    "moving",
    "unknown",
]

torrent_downloading_states = [
    "downloading",
    "metaDL",
    "forcedMetaDL",
    "stalledDL",
    "checkingDL",
    "pausedDL",
    "stoppedDL",
    "queuedDL",
    "forcedDL",
]

torrent_uploading_states = [
    "uploading",
    "stalledUP",
    "checkingUP",
    "queuedUP",
    "forcedUP",
]

torrent_complete_states = [
    "uploading",
    "stalledUP",
    "checkingUP",
    "pausedUP",
    "stoppedUP",
    "queuedUP",
    "forcedUP",
]

torrent_checking_states = ["checkingUP", "checkingDL", "checkingResumeData"]

torrent_errored_states = ["missingFiles", "error"]

torrent_paused_states = ["stoppedUP", "pausedUP", "stoppedDL", "pausedDL"]


def test_torrent_states_exists():
    assert isinstance(TorrentState("unknown"), Enum)


@pytest.mark.parametrize("state", torrent_all_states)
def test_all_states(state):
    assert TorrentState(state) in TorrentState


@pytest.mark.parametrize("state", torrent_all_states)
def test_states_cmp_str(state):
    assert TorrentState(state) == TorrentState(state).value


@pytest.mark.parametrize("state", torrent_downloading_states)
def test_downloading_states(state):
    assert TorrentState(state).is_downloading


@pytest.mark.parametrize("state", torrent_uploading_states)
def test_uploading_states(state):
    assert TorrentState(state).is_uploading


@pytest.mark.parametrize("state", torrent_complete_states)
def test_completing_states(state):
    assert TorrentState(state).is_complete


@pytest.mark.parametrize("state", torrent_checking_states)
def test_checking_states(state):
    assert TorrentState(state).is_checking


@pytest.mark.parametrize("state", torrent_errored_states)
def test_errored_states(state):
    assert TorrentState(state).is_errored


@pytest.mark.parametrize("state", torrent_paused_states)
def test_paused_states(state):
    assert TorrentState(state).is_paused


@pytest.mark.parametrize("status", [0, 1, 2, 3, 4])
def test_tracker_statuses_exist(status):
    assert isinstance(TrackerStatus(status), Enum)


@pytest.mark.parametrize("status", [0, 1, 2, 3, 4])
def test_tracker_statuses_cmp_int(status):
    assert TrackerStatus(status) == TrackerStatus(status).value


@pytest.mark.parametrize(
    "status, display_value",
    [
        (0, "Disabled"),
        (1, "Not contacted"),
        (2, "Working"),
        (3, "Updating"),
        (4, "Not working"),
    ],
)
def test_tracker_status_display(status, display_value):
    assert TrackerStatus(status).display == display_value


def test_testing_groups():
    assert set(torrent_all_states) == {s.value for s in iter(TorrentState)}
    assert set(torrent_downloading_states) == {
        s.value for s in TorrentState if s.is_downloading
    }
    assert set(torrent_uploading_states) == {
        s.value for s in TorrentState if s.is_uploading
    }
    assert set(torrent_complete_states) == {
        s.value for s in TorrentState if s.is_complete
    }
    assert set(torrent_checking_states) == {
        s.value for s in TorrentState if s.is_checking
    }
    assert set(torrent_errored_states) == {
        s.value for s in TorrentState if s.is_errored
    }


def test_dictionary():
    assert len(Dictionary()) == 0
    assert len(Dictionary({"one": {"two": 2}})) == 1
    assert isinstance(Dictionary({"one": {"two": 2}}).one, AttrDict)
    assert isinstance(Dictionary({"one": {"two": 2}})["one"], AttrDict)
    assert Dictionary({"one": {"two": 2}}).one.two == 2
    assert Dictionary({"one": {"two": 2}})["one"]["two"] == 2
    assert Dictionary({"three": 3}).three == 3
    assert Dictionary({"three": 3})["three"] == 3


def test_list(client):
    assert len(List()) == 0
    list_entries = [{"one": "1"}, {"two": "2"}, {"three": "3"}]
    test_list = List(list_entries, entry_class=ListEntry)
    assert len(test_list) == 3
    assert issubclass(type(test_list[0]), ListEntry)
    assert test_list[0].one == "1"


def test_list_actions(client):
    list_one = List(
        [{"one": "1"}, {"two": "2"}, {"three": "3"}],
        entry_class=ListEntry,
    )
    list_two = List([{"four": "4"}], entry_class=ListEntry)

    assert list_one[1:3] == [
        ListEntry({"two": "2"}),
        ListEntry({"three": "3"}),
    ]
    assert list_one + list_two == [
        ListEntry({"one": "1"}),
        ListEntry({"two": "2"}),
        ListEntry({"three": "3"}),
    ] + [ListEntry({"four": "4"})]

    assert list_one.copy() == [
        ListEntry({"one": "1"}),
        ListEntry({"two": "2"}),
        ListEntry({"three": "3"}),
    ]
