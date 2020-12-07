import logging
from json import dumps

from attrdict import AttrDict

import pytest

from qbittorrentapi import Client
from qbittorrentapi.decorators import (
    _is_version_less_than,
    response_json,
    response_text,
)
from qbittorrentapi.decorators import version_implemented, version_removed
from qbittorrentapi import APIError


def test_is_version_less_than():
    assert _is_version_less_than("1", "1", lteq=True) is True
    assert _is_version_less_than("1", "1", lteq=False) is False
    assert _is_version_less_than("1.5", "1", lteq=True) is False
    assert _is_version_less_than("1.5", "1", lteq=False) is False
    assert _is_version_less_than("1", "1.5", lteq=True) is True
    assert _is_version_less_than("1", "1.5", lteq=False) is True


def test_login_required(caplog, app_version):
    client = Client(
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    with caplog.at_level(logging.DEBUG, logger="qbittorrentapi"):
        qbt_version = client.app.version
    assert "Not logged in...attempting login" in caplog.text
    assert qbt_version == app_version

    client.auth_log_out()
    with caplog.at_level(logging.DEBUG, logger="qbittorrentapi"):
        qbt_version = client.app.version
    assert "Not logged in...attempting login" in caplog.text
    assert qbt_version == app_version


def test_response_text():
    class ResponseTextTest:
        @response_text(str)
        def return_input_as_str(self, input):
            return input

        @response_text(dict)
        def return_input_as_dict(self, input):
            return input

    input = "asdf"
    assert input == ResponseTextTest().return_input_as_str(input)
    with pytest.raises(APIError):
        ResponseTextTest().return_input_as_dict(input)


def test_response_json():
    class MyDict(AttrDict):
        def __init__(self, *args):
            super(AttrDict, self).__init__(args[0])
            self._setattr("_allow_invalid_attributes", True)

    class FakeJson(AttrDict):
        data = None

        def __init__(self):
            super(AttrDict, self).__init__()
            self._setattr("_allow_invalid_attributes", True)

        @property
        def text(self):
            return dumps(self.data)

    class ResponseJsonTest:
        _SIMPLE_RESPONSES = False

        @response_json(dict)
        def return_input_as_dict(self, input):
            return input

        @response_json(MyDict)
        def return_input_as_mydict(self, input):
            return input

    input = {"one": 1}
    assert isinstance(ResponseJsonTest().return_input_as_dict(input), dict)
    input = FakeJson()
    input.data = {"one": 1}
    assert isinstance(ResponseJsonTest().return_input_as_mydict(input), MyDict)
    input.data = ["asdf"]
    with pytest.raises(APIError):
        ResponseJsonTest().return_input_as_mydict(input)


def test_version_implemented():
    class FakeClient:
        _RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS = True
        version = "1.0"

        def _app_web_api_version_from_version_checker(self):
            return self.version

        @version_implemented("1.1", "test1")
        def endpoint_not_implemented(self):
            return

        @version_implemented("0.9", "test2")
        def endpoint_implemented(self):
            return

        @version_implemented("1.1", "test3", ("var1", "var1"))
        def endpoint_param_not_implemented(self, var1="zxcv"):
            return var1

        @version_implemented("0.9", "test3", ("var1", "var1"))
        def endpoint_param_implemented(self, var1="zxcv"):
            return var1

    with pytest.raises(NotImplementedError):
        FakeClient().endpoint_not_implemented()

    assert FakeClient().endpoint_implemented() is None

    with pytest.raises(NotImplementedError):
        FakeClient().endpoint_param_not_implemented(var1="asdf")

    assert FakeClient().endpoint_param_not_implemented(var1=None) is None

    fake_client = FakeClient()
    fake_client._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS = False
    assert fake_client.endpoint_param_not_implemented(var1="asdf") is None
    assert fake_client.endpoint_not_implemented() is None

    assert FakeClient().endpoint_param_implemented(var1="asdf") == "asdf"


def test_version_removed():
    class FakeClient:
        _RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS = True
        version = "1.0"

        def _app_web_api_version_from_version_checker(self):
            return self.version

        @version_removed("0.0.0", "test1")
        def endpoint_not_implemented(self):
            return

        @version_removed("9999999", "test2")
        def endpoint_implemented(self):
            return

    with pytest.raises(NotImplementedError):
        FakeClient().endpoint_not_implemented()

    assert FakeClient().endpoint_implemented() is None

    fake_client = FakeClient()
    fake_client._RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS = False
    assert fake_client.endpoint_not_implemented() is None
