import logging
import re
from os import environ
from unittest.mock import MagicMock, PropertyMock

import pytest
from requests import Response
from requests.adapters import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE

from qbittorrentapi import APINames, Client, exceptions
from qbittorrentapi._version_support import v
from qbittorrentapi.definitions import Dictionary, List
from qbittorrentapi.exceptions import Forbidden403Error
from qbittorrentapi.request import Request
from qbittorrentapi.torrents import TorrentDictionary, TorrentInfoList
from tests.conftest import IS_QBT_DEV
from tests.utils import mkpath


def test_method_name(client, app_version):
    assert app_version == client._get("app", "version", response_class=str)
    assert app_version == client._get(
        APINames.Application,
        "version",
        response_class=str,
    )


def test_log_in():
    client_good = Client(VERIFY_WEBUI_CERTIFICATE=False)
    client_bad = Client(
        username="asdf",
        password="asdfasdf",
        VERIFY_WEBUI_CERTIFICATE=False,
    )

    client_good.auth_log_out()
    assert client_good.auth_log_in() is None
    assert client_good.is_logged_in is True
    client_good.auth_log_out()
    assert client_good.auth.log_in() is None
    assert client_good.auth.is_logged_in is True
    assert client_good.auth.is_logged_in is True
    with pytest.raises(exceptions.LoginFailed):
        client_bad.auth_log_in()
    with pytest.raises(exceptions.LoginFailed):
        client_bad.auth.log_in()


def test_log_in_via_auth():
    client_good = Client(VERIFY_WEBUI_CERTIFICATE=False)
    client_bad = Client(
        username="asdf",
        password="asdfasdf",
        VERIFY_WEBUI_CERTIFICATE=False,
    )

    assert (
        client_good.auth_log_in(
            username=environ.get("QBITTORRENTAPI_USERNAME"),
            password=environ.get("QBITTORRENTAPI_PASSWORD"),
        )
        is None
    )
    with pytest.raises(exceptions.LoginFailed):
        client_bad.auth_log_in(username="asdf", password="asdfasdf")


def test_forbidden_when_banned(client, monkeypatch):
    monkeypatch.setattr(
        client,
        "_request_manager",
        MagicMock(
            side_effect=Forbidden403Error,
            spec=client._request_manager,
        ),
    )

    with pytest.raises(Forbidden403Error):
        client.auth.log_in()

    with pytest.raises(Forbidden403Error):
        _ = client.app.version


@pytest.mark.parametrize(
    "hostname",
    (
        "localhost:8080",
        "localhost:8080/",
        "http://localhost:8080",
        "http://localhost:8080/",
        "https://localhost:8080",
        "https://localhost:8080/",
        "//localhost:8080",
        "//localhost:8080/",
    ),
)
def test_hostname_format(app_version, hostname):
    client = Client(
        host=hostname,
        VERIFY_WEBUI_CERTIFICATE=False,
        REQUESTS_ARGS={"timeout": 1},
    )
    assert client.app.version == app_version
    # ensure the base URL is always normalized
    assert re.match(r"(http|https)://localhost:8080/", client._url._base_url)


@pytest.mark.parametrize(
    "hostname",
    (
        "localhost:8080/qbt",
        "localhost:8080/qbt/",
    ),
)
def test_hostname_user_base_path(hostname):
    client = Client(host=hostname, VERIFY_WEBUI_CERTIFICATE=False)
    # the command will fail but the URL will be built
    with pytest.raises(exceptions.APIConnectionError):
        _ = client.app.version
    # ensure user provided base paths are preserved
    assert re.match(r"(http|https)://localhost:8080/qbt/", client._url._base_url)


def test_port_from_host(app_version):
    host, port = environ.get("QBITTORRENTAPI_HOST").split(":")
    client = Client(host=host, port=port, VERIFY_WEBUI_CERTIFICATE=False)
    assert client.app.version == app_version


def _enable_disable_https(client, use_https):
    if use_https:
        client.app.preferences = {
            "use_https": True,
            "web_ui_https_cert_path": mkpath("/tmp", "_resources", "server.crt"),
            "web_ui_https_key_path": mkpath("/tmp", "_resources", "server.key"),
        }
    else:
        client.app.preferences = {"use_https": False}


@pytest.mark.skipif_before_api_version("2.2.1")
@pytest.mark.parametrize("use_https", (True, False))
def test_force_user_scheme(client, app_version, use_https):
    default_host = environ["QBITTORRENTAPI_HOST"]

    _enable_disable_https(client, use_https)

    client = Client(
        host="http://" + default_host,
        VERIFY_WEBUI_CERTIFICATE=False,
        FORCE_SCHEME_FROM_HOST=True,
        REQUESTS_ARGS={"timeout": 3},
    )
    if use_https:
        with pytest.raises(exceptions.APIConnectionError):
            assert client.app.version == app_version
    else:
        assert client.app.version == app_version
    assert client._url._base_url.startswith("http://")

    client = Client(
        host=default_host,
        VERIFY_WEBUI_CERTIFICATE=False,
        FORCE_SCHEME_FROM_HOST=True,
        REQUESTS_ARGS={"timeout": 3},
    )
    assert client.app.version == app_version
    if use_https:
        assert client._url._base_url.startswith("https://")
    else:
        assert client._url._base_url.startswith("http://")

    client = Client(
        host="https://" + default_host,
        VERIFY_WEBUI_CERTIFICATE=False,
        FORCE_SCHEME_FROM_HOST=True,
        REQUESTS_ARGS={"timeout": 3},
    )
    if not use_https:
        with pytest.raises(exceptions.APIConnectionError):
            assert client.app.version == app_version
    else:
        assert client.app.version == app_version
    assert client._url._base_url.startswith("https://")


@pytest.mark.skipif_before_api_version("2.2.1")
@pytest.mark.parametrize("scheme", ("http://", "https://"))
def test_both_https_http_not_working(client, app_version, scheme):
    default_host = environ["QBITTORRENTAPI_HOST"]
    _enable_disable_https(client, use_https=True)

    # rerun with verify=True
    test_client = Client(
        host=scheme + default_host,
        REQUESTS_ARGS={"timeout": 3},
    )
    with pytest.raises(exceptions.APIConnectionError):
        assert test_client.app.version == app_version
    assert test_client._url._base_url.startswith("https://")

    _enable_disable_https(client, use_https=False)


def test_legacy_env_vars():
    save_env_host = environ.get("QBITTORRENTAPI_HOST")
    save_env_username = environ.get("QBITTORRENTAPI_USERNAME")
    save_env_password = environ.get("QBITTORRENTAPI_PASSWORD")
    save_env_verify = environ.get("QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE")
    del environ["QBITTORRENTAPI_HOST"]
    del environ["QBITTORRENTAPI_USERNAME"]
    del environ["QBITTORRENTAPI_PASSWORD"]
    if "QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE" in environ:
        del environ["QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE"]

    client = Client()

    assert client.host == ""
    assert client.username == ""
    assert client._password == ""
    assert client._VERIFY_WEBUI_CERTIFICATE is True

    environ["PYTHON_QBITTORRENTAPI_HOST"] = excepted_host = "legacy:8090"
    environ["PYTHON_QBITTORRENTAPI_USERNAME"] = excepted_username = "legacyuser"
    environ["PYTHON_QBITTORRENTAPI_PASSWORD"] = expected_password = "legacypassword"
    environ["PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE"] = "true"

    client = Client()

    try:
        assert client.host == excepted_host
        assert client.username == excepted_username
        assert client._password == expected_password
        assert client._VERIFY_WEBUI_CERTIFICATE is False
    finally:
        environ["QBITTORRENTAPI_HOST"] = save_env_host
        environ["QBITTORRENTAPI_USERNAME"] = save_env_username
        environ["QBITTORRENTAPI_PASSWORD"] = save_env_password
        if save_env_verify is not None:
            environ["QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE"] = save_env_verify

    client = Client()

    assert client.host != excepted_host
    assert client.username != excepted_username
    assert client._password != expected_password
    assert client._VERIFY_WEBUI_CERTIFICATE is False

    del environ["PYTHON_QBITTORRENTAPI_HOST"]
    del environ["PYTHON_QBITTORRENTAPI_USERNAME"]
    del environ["PYTHON_QBITTORRENTAPI_PASSWORD"]
    del environ["PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE"]


def test_log_out(client):
    client.auth_log_out()
    with pytest.raises(exceptions.Forbidden403Error):
        # cannot call client.app.version directly since it will auto log back in
        client._request_manager("get", APINames.Application, "version")
    client.auth_log_in()
    client.auth.log_out()
    with pytest.raises(exceptions.Forbidden403Error):
        # cannot call client.app.version directly since it will auto log back in
        client._request_manager("get", APINames.Application, "version")
    client.auth_log_in()


def test_port(app_version):
    client = Client(host="localhost", port=8080, VERIFY_WEBUI_CERTIFICATE=False)
    assert client.app.version == app_version

    client = Client(host="localhost:8080", port=8081, VERIFY_WEBUI_CERTIFICATE=False)
    assert client.app.version == app_version


def test_response_str(client):
    response = MagicMock(spec_set=Response)

    type(response).text = PropertyMock(return_value="text response")
    assert client._cast(response, str) == "text response"

    type(response).text = PropertyMock(return_value="text response")
    with pytest.raises(exceptions.APIError, match="Exception during response parsing."):
        client._cast(response, int)


def test_response_int(client):
    response = MagicMock(spec_set=Response)

    type(response).text = PropertyMock(return_value="123")
    assert client._cast(response, int) == 123

    type(response).text = PropertyMock(return_value="text response")
    with pytest.raises(exceptions.APIError, match="Exception during response parsing."):
        client._cast(response, int)


def test_response_bytes(client):
    response = MagicMock(spec_set=Response)

    type(response).content = PropertyMock(return_value=b"bytes response")
    assert client._cast(response, bytes) == b"bytes response"


def test_response_json_list(client):
    response = MagicMock(spec_set=Response)

    response.json.return_value = ["json", "response"]
    assert client._cast(response, List) == ["json", "response"]

    response.json.return_value = 123
    with pytest.raises(exceptions.APIError, match="Exception during response parsing."):
        client._cast(response, List)

    del response.json

    type(response).text = PropertyMock(return_value='["json", "response"]')
    assert client._cast(response, List) == ["json", "response"]

    type(response).text = PropertyMock(return_value=123)
    with pytest.raises(exceptions.APIError, match="Exception during response parsing."):
        client._cast(response, List)


def test_response_json_dict(client):
    response = MagicMock(spec_set=Response)

    response.json.return_value = {"json": "response"}
    assert client._cast(response, Dictionary) == {"json": "response"}

    response.json.return_value = 123
    with pytest.raises(exceptions.APIError, match="Exception during response parsing."):
        client._cast(response, List)

    del response.json

    type(response).text = PropertyMock(return_value='{"json": "response"}')
    assert client._cast(response, Dictionary) == {"json": "response"}

    type(response).text = PropertyMock(return_value="123")
    with pytest.raises(exceptions.APIError, match="Exception during response parsing."):
        client._cast(response, List)


def test_response_unsupported(client):
    response = MagicMock(spec_set=Response)

    type(response).text = PropertyMock(return_value="123.01")
    with pytest.raises(
        exceptions.APIError,
        match="No handler defined to cast response.",
    ):
        client._cast(response, float)

    with pytest.raises(
        exceptions.APIError,
        match="No handler defined to cast response.",
    ):
        client._get(_name=APINames.Application, _method="version", response_class=float)


def test_simple_response(client):
    torrent = client.torrents_info()[0]
    assert isinstance(torrent, TorrentDictionary)
    torrent = client.torrents_info(SIMPLE_RESPONSE=True)[0]
    assert isinstance(torrent, dict)
    torrent = client.torrents_info(SIMPLE_RESPONSES=True)[0]
    assert isinstance(torrent, dict)
    torrent = client.torrents_info(SIMPLE_RESPONSE=False)[0]
    assert isinstance(torrent, TorrentDictionary)
    torrent = client.torrents_info(SIMPLE_RESPONSES=False)[0]
    assert isinstance(torrent, TorrentDictionary)
    client = Client(VERIFY_WEBUI_CERTIFICATE=False, SIMPLE_RESPONSES=True)
    torrent = client.torrents_info()[0]
    assert isinstance(torrent, dict)
    client = Client(VERIFY_WEBUI_CERTIFICATE=False, SIMPLE_RESPONSES=False)
    torrent = client.torrents_info()[0]
    assert isinstance(torrent, TorrentDictionary)


def test_request_extra_headers():
    client = Client(
        VERIFY_WEBUI_CERTIFICATE=False,
        EXTRA_HEADERS={"X-MY-HEADER": "asdf"},
    )
    client.auth.log_in()

    r = client._get(APINames.Application, "version")
    assert r.request.headers["X-MY-HEADER"] == "asdf"

    r = client._get(
        APINames.Application,
        "version",
        headers={"X-MY-HEADER-TWO": "zxcv"},
    )
    assert r.request.headers["X-MY-HEADER"] == "asdf"
    assert r.request.headers["X-MY-HEADER-TWO"] == "zxcv"

    r = client._get(
        APINames.Application,
        "version",
        headers={"X-MY-HEADER-TWO": "zxcv"},
        requests_args={"headers": {"X-MY-HEADER-THREE": "tyui"}},
    )
    assert r.request.headers["X-MY-HEADER"] == "asdf"
    assert r.request.headers["X-MY-HEADER-TWO"] == "zxcv"
    assert r.request.headers["X-MY-HEADER-THREE"] == "tyui"

    r = client._get(
        APINames.Application,
        "version",
        headers={"X-MY-HEADER": "zxcv"},
        requests_args={"headers": {"X-MY-HEADER": "tyui"}},
    )
    assert r.request.headers["X-MY-HEADER"] == "zxcv"

    r = client._get(APINames.Application, "version", headers={"X-MY-HEADER": "zxcv"})
    assert r.request.headers["X-MY-HEADER"] == "zxcv"


@pytest.mark.skipif_before_api_version("2.2.1")
def test_requests_timeout(api_version):
    class MyTimeoutError(Exception):
        pass

    logger = logging.getLogger("test_requests_timeout")

    timeout = 1e-100
    loops = 1000
    client = Client(VERIFY_WEBUI_CERTIFICATE=False)
    with pytest.raises(MyTimeoutError):
        try:
            for _ in range(loops):
                client.torrents_info(requests_args={"timeout": timeout})
        except exceptions.APIConnectionError as exp:
            logger.error("%r", exp)
            if "ReadTimeoutError" in str(exp) or "RemoteDisconnected" in str(exp):
                raise MyTimeoutError

    client = Client(VERIFY_WEBUI_CERTIFICATE=False, REQUESTS_ARGS={"timeout": timeout})
    with pytest.raises(MyTimeoutError):
        try:
            for _ in range(loops):
                client.torrents_info()
        except exceptions.APIConnectionError as exp:
            logger.error("%r", exp)
            if "ReadTimeoutError" in str(exp) or "RemoteDisconnected" in str(exp):
                raise MyTimeoutError


def test_request_extra_params(client, orig_torrent):
    """Extra params can be sent directly to qBittorrent but there aren't any real use-
    cases so force it."""
    response = client._post(
        APINames.Torrents,
        "info",
        hashes=orig_torrent.hash,
        extra_param="extra",
    )
    assert "extra_param=extra" in response.request.body
    torrent = TorrentInfoList(response.json(), client)[0]
    assert torrent.hash == orig_torrent.hash

    response = client._get(
        APINames.Torrents,
        "info",
        hashes=orig_torrent.hash,
        extra_param="extra",
    )
    assert "extra_param=extra" in response.request.url
    torrent = TorrentInfoList(response.json(), client)[0]
    assert torrent.hash == orig_torrent.hash


def test_unsupported_version_error(monkeypatch):
    if IS_QBT_DEV:
        return

    client = Client(
        VERIFY_WEBUI_CERTIFICATE=False,
        RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=True,
    )
    monkeypatch.setattr(client, "app_version", MagicMock(return_value="1.0.0"))
    with pytest.raises(exceptions.UnsupportedQbittorrentVersion):
        client.app_web_api_version()

    client = Client(
        VERIFY_WEBUI_CERTIFICATE=False,
        RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=True,
    )
    client.app_version()


def test_disable_logging():
    Client(DISABLE_LOGGING_DEBUG_OUTPUT=False)
    assert logging.getLogger("qbittorrentapi").level == logging.NOTSET
    assert logging.getLogger("requests").level == logging.NOTSET
    assert logging.getLogger("urllib3").level == logging.NOTSET

    Client(DISABLE_LOGGING_DEBUG_OUTPUT=True)
    assert logging.getLogger("qbittorrentapi").level == logging.INFO
    assert logging.getLogger("requests").level == logging.INFO
    assert logging.getLogger("urllib3").level == logging.INFO

    logging.getLogger("qbittorrentapi").setLevel(level=logging.CRITICAL)
    Client(DISABLE_LOGGING_DEBUG_OUTPUT=True)
    assert logging.getLogger("qbittorrentapi").level == logging.CRITICAL
    assert logging.getLogger("requests").level == logging.INFO
    assert logging.getLogger("urllib3").level == logging.INFO


def test_verify_cert(app_version):
    client = Client(VERIFY_WEBUI_CERTIFICATE=False)
    assert client._VERIFY_WEBUI_CERTIFICATE is False
    assert client.app.version == app_version

    # this is only ever going to work with a trusted cert....disabling for now
    # client = Client(VERIFY_WEBUI_CERTIFICATE=True)
    # assert client._VERIFY_WEBUI_CERTIFICATE is True
    # assert client.app.version == app_version

    environ["QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE"] = "true"
    client = Client(VERIFY_WEBUI_CERTIFICATE=True)
    assert client._VERIFY_WEBUI_CERTIFICATE is False
    assert client.app.version == app_version
    del environ["QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE"]


def test_api_connection_error():
    with pytest.raises(exceptions.APIConnectionError):
        Client(host="localhost:8081").auth_log_in(_retries=0)

    with pytest.raises(exceptions.APIConnectionError):
        Client(host="localhost:8081").auth_log_in(_retries=1)

    with pytest.raises(exceptions.APIConnectionError):
        Client(host="localhost:8081").auth_log_in(_retries=2)

    with pytest.raises(exceptions.APIConnectionError):
        Client(host="localhost:8081").auth_log_in(_retries=3)


def test_http400(client, app_version, orig_torrent):
    with pytest.raises(exceptions.MissingRequiredParameters400Error):
        client.torrents_file_priority(torrent_hash=orig_torrent.hash)

    if v(app_version) >= v("4.1.6"):
        with pytest.raises(exceptions.InvalidRequest400Error) as exc_info:
            client.torrents_file_priority(
                torrent_hash=orig_torrent.hash,
                file_ids="asdf",
                priority="asdf",
            )
        assert exc_info.value.http_status_code == 400


def test_http401():
    client = Client(VERIFY_WEBUI_CERTIFICATE=False)
    _ = client.app.preferences
    # ensure cross site scripting protection is enabled
    client.app.preferences = dict(web_ui_csrf_protection_enabled=True)
    # simulate a XSS request
    with pytest.raises(exceptions.Unauthorized401Error) as exc_info:
        client.app_version(
            headers={"Origin": "https://example.com", "Referer": "https://example.com"}
        )
    assert exc_info.value.http_status_code == 401


@pytest.mark.parametrize("params", ({}, {"hash": "asdf"}, {"hashes": "asdf|asdf"}))
def test_http404(client, params):
    with pytest.raises(exceptions.NotFound404Error, match="Torrent hash") as exc_info:
        client.torrents_rename(torrent_hash="zxcv", new_torrent_name="erty")
    assert "zxcv" in exc_info.value.args[0]

    response = MagicMock(spec=Response, status_code=404, text="", request=object())
    with pytest.raises(exceptions.HTTPError) as exc_info:
        Request._handle_error_responses(data={}, params=params, response=response)
    assert exc_info.value.http_status_code == 404
    if params:
        assert params[list(params.keys())[0]] in exc_info.value.args[0]

    response = MagicMock(
        spec=Response, status_code=404, text="unexpected msg", request=object()
    )
    with pytest.raises(exceptions.HTTPError, match="unexpected msg") as exc_info:
        Request._handle_error_responses(data={}, params=params, response=response)
    assert exc_info.value.http_status_code == 404
    assert exc_info.value.args[0] == "unexpected msg"

    response = MagicMock(spec=Response, status_code=404, text="", request=object())
    with pytest.raises(exceptions.HTTPError) as exc_info:
        Request._handle_error_responses(data=params, params={}, response=response)
    assert exc_info.value.http_status_code == 404
    if params:
        assert params[list(params.keys())[0]] in exc_info.value.args[0]

    response = MagicMock(
        spec=Response, status_code=404, text="unexpected msg", request=object()
    )
    with pytest.raises(exceptions.HTTPError, match="unexpected msg") as exc_info:
        Request._handle_error_responses(data=params, params={}, response=response)
    assert exc_info.value.http_status_code == 404
    assert exc_info.value.args[0] == "unexpected msg"


def test_http405(client, app_version):
    # v4.4.4 uses same API version as previous release...
    if v(app_version) >= v("v4.4.4"):
        with pytest.raises(exceptions.MethodNotAllowed405Error) as exc_info:
            client._get(APINames.Authorization, "logout")
        assert exc_info.value.http_status_code == 405


def test_http409(client, app_version):
    if v(app_version) >= v("4.1.6"):
        with pytest.raises(exceptions.Conflict409Error) as exc_info:
            client.torrents_set_location(torrent_hashes="asdf", location="/etc/asdf/")
        assert exc_info.value.http_status_code == 409


def test_http415(client):
    with pytest.raises(exceptions.UnsupportedMediaType415Error) as exc_info:
        client.torrents.add(torrent_files="/etc/hosts")
    assert exc_info.value.http_status_code == 415


@pytest.mark.parametrize("status_code", (500, 503))
def test_http500(status_code):
    response = MagicMock(
        spec=Response, status_code=status_code, text="asdf", request=object()
    )
    with pytest.raises(exceptions.InternalServerError500Error) as exc_info:
        Request._handle_error_responses(data={}, params={}, response=response)
    assert exc_info.value.http_status_code == status_code


@pytest.mark.parametrize("status_code", (402, 406))
def test_http_error(status_code):
    response = MagicMock(
        spec=Response, status_code=status_code, text="asdf", request=object()
    )
    with pytest.raises(exceptions.HTTPError) as exc_info:
        Request._handle_error_responses(data={}, params={}, response=response)
    assert exc_info.value.http_status_code == status_code


def test_request_retry_success(monkeypatch, caplog):
    def request500(*args, **kwargs):
        raise exceptions.HTTP500Error()

    client = Client(VERIFY_WEBUI_CERTIFICATE=False)
    client.auth_log_in()
    with monkeypatch.context() as m:
        m.setattr(client, "_request", request500)
        with (
            caplog.at_level(logging.DEBUG, logger="qbittorrentapi"),
            pytest.raises(exceptions.HTTP500Error),
        ):
            client.app_version()
        assert "Retry attempt" in caplog.text


def test_request_retry_skip(caplog):
    client = Client(VERIFY_WEBUI_CERTIFICATE=False)
    client.auth_log_in()
    with (
        caplog.at_level(logging.DEBUG, logger="qbittorrentapi"),
        pytest.raises(exceptions.MissingRequiredParameters400Error),
    ):
        client.torrents_rename()
    assert "Retry attempt" not in caplog.text


def test_verbose_logging(caplog):
    client = Client(VERBOSE_RESPONSE_LOGGING=True, VERIFY_WEBUI_CERTIFICATE=False)
    with (
        caplog.at_level(logging.DEBUG, logger="qbittorrentapi"),
        pytest.raises(exceptions.NotFound404Error),
    ):
        client.torrents_rename(torrent_hash="asdf", new_torrent_name="erty")
    assert "Response status" in caplog.text


def test_stack_printing(capsys):
    client = Client(VERIFY_WEBUI_CERTIFICATE=False)
    client._PRINT_STACK_FOR_EACH_REQUEST = True
    client.app_version()

    assert "print_stack()" in capsys.readouterr().err


def test_auto_authentication(caplog, app_version):
    client = Client(
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    # check if first API call works if already logged in
    client.auth_log_in()
    with caplog.at_level(logging.DEBUG, logger="qbittorrentapi"):
        qbt_version = client.app.version
    assert "Login may have expired...attempting new login" not in caplog.text
    assert qbt_version == app_version

    # ensure login happens after first API call fails
    client.auth_log_out()
    with caplog.at_level(logging.DEBUG, logger="qbittorrentapi"):
        qbt_version = client.app.version
    assert "Login may have expired...attempting new login" in caplog.text
    assert qbt_version == app_version


def test_not_implemented_no_error(monkeypatch):
    client = Client(VERIFY_WEBUI_CERTIFICATE=False)

    monkeypatch.setattr(client, "app_web_api_version", MagicMock(return_value="1.0.0"))
    assert client.search_categories() is None

    monkeypatch.setattr(client, "app_web_api_version", MagicMock(return_value="10.0.0"))
    assert client.search_categories() is None


def test_not_implemented_error(monkeypatch, client):
    monkeypatch.setattr(client, "app_web_api_version", MagicMock(return_value="1.0.0"))
    with pytest.raises(NotImplementedError, match=r"This endpoint is available"):
        client.search_categories()

    monkeypatch.setattr(client, "app_web_api_version", MagicMock(return_value="10.0.0"))
    with pytest.raises(NotImplementedError, match=r"This endpoint was removed"):
        client.search_categories()


def test_http_adapter_defaults():
    client = Client(
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    assert client._session.adapters["http://"] is client._session.adapters["https://"]
    assert client._session.adapters["http://"].max_retries.total == 1
    assert client._session.adapters["http://"]._pool_connections == DEFAULT_POOLSIZE
    assert client._session.adapters["http://"]._pool_maxsize == DEFAULT_POOLSIZE
    assert client._session.adapters["http://"]._pool_block is DEFAULT_POOLBLOCK


def test_http_adapter_overrides():
    client = Client(
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
        HTTPADAPTER_ARGS=dict(
            pool_connections=100,
            pool_maxsize=50,
            max_retries=10,
            pool_block=True,
        ),
    )
    assert client._session.adapters["http://"] is client._session.adapters["https://"]
    assert client._session.adapters["http://"].max_retries.total == 10
    assert client._session.adapters["http://"]._pool_connections == 100
    assert client._session.adapters["http://"]._pool_maxsize == 50
    assert client._session.adapters["http://"]._pool_block is True
