import sys
from unittest.mock import MagicMock

import pytest

from qbittorrentapi import APINames, Client
from qbittorrentapi.exceptions import (
    APIConnectionError,
    Forbidden403Error,
    LoginFailed,
    Unauthorized401Error,
)


@pytest.mark.skipif(sys.version_info < (3, 9), reason="removeprefix not in 3.8")
def test_methods(client):
    namespace = APINames.Authorization
    all_dotted_methods = set(dir(getattr(client, namespace)))

    for meth in [meth for meth in dir(client) if meth.startswith(f"{namespace}_")]:
        assert meth.removeprefix(f"{namespace}_") in all_dotted_methods


def test_is_logged_in():
    client = Client(
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    assert client.is_logged_in is False

    client.auth_log_in()
    assert client.is_logged_in is True

    client.auth_log_out()
    assert client.is_logged_in is False

    client.auth.log_in()
    assert client.is_logged_in is True

    client.auth.log_out()
    assert client.is_logged_in is False

    client.authorization.log_in()
    assert client.is_logged_in is True

    client.authorization.log_out()
    assert client.is_logged_in is False


def test_is_logged_in_bad_client():
    client = Client(
        host="asdf",
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    assert client.is_logged_in is False

    with pytest.raises(APIConnectionError):
        client.auth_log_in()
    assert client.is_logged_in is False

    assert client.is_logged_in is False
    client.auth_log_out()  # does nothing if not logged in


def test_session_cookie(app_version):
    client = Client(
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    assert client._session_cookie() is None

    # make the client perform a login
    assert client.app.version == app_version

    # should test other cookie names but it's difficult to change
    curr_sess_cookie = client._session_cookie()
    assert curr_sess_cookie is not None
    assert curr_sess_cookie == client._SID


def test_login_context_manager():
    with Client(
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        VERIFY_WEBUI_CERTIFICATE=False,
    ) as client:
        assert client.is_logged_in
    assert not client.is_logged_in


def test_api_key_sets_bearer_header():
    client = Client(
        host="localhost:8080",
        api_key="qbt_test_key",
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    assert client._api_key == "qbt_test_key"
    assert client._session.headers["Authorization"] == "Bearer qbt_test_key"


def test_api_key_does_not_override_explicit_authorization_header():
    # an Authorization header explicitly supplied via EXTRA_HEADERS takes precedence
    client = Client(
        host="localhost:8080",
        api_key="qbt_test_key",
        EXTRA_HEADERS={"Authorization": "Bearer custom"},
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    assert client._session.headers["Authorization"] == "Bearer custom"


def test_api_key_env_var(monkeypatch):
    monkeypatch.setenv("QBITTORRENTAPI_API_KEY", "qbt_env_key")
    client = Client(host="localhost:8080", VERIFY_WEBUI_CERTIFICATE=False)
    assert client._api_key == "qbt_env_key"
    assert client._session.headers["Authorization"] == "Bearer qbt_env_key"


def test_api_key_python_env_var_not_supported(monkeypatch):
    # only QBITTORRENTAPI_API_KEY is consulted; the PYTHON_ prefixed variant is not
    monkeypatch.delenv("QBITTORRENTAPI_API_KEY", raising=False)
    monkeypatch.setenv("PYTHON_QBITTORRENTAPI_API_KEY", "qbt_env_key")
    client = Client(host="localhost:8080", VERIFY_WEBUI_CERTIFICATE=False)
    assert client._api_key == ""
    assert "Authorization" not in client._session.headers


def test_api_key_auth_log_in_success(monkeypatch):
    client = Client(
        host="localhost:8080",
        api_key="qbt_test_key",
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    # is_logged_in performs a low-overhead app/version call; mock it as successful
    request_manager = MagicMock(spec=client._request_manager)
    monkeypatch.setattr(client, "_request_manager", request_manager)

    assert client.auth_log_in() is None
    # validation was via app/version, not an auth/login POST
    assert request_manager.call_args.kwargs["api_namespace"] == APINames.Application
    assert request_manager.call_args.kwargs["api_method"] == "version"


@pytest.mark.parametrize("error", [Unauthorized401Error, Forbidden403Error])
def test_api_key_auth_log_in_failure(monkeypatch, error):
    client = Client(
        host="localhost:8080",
        api_key="qbt_test_key",
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    monkeypatch.setattr(
        client,
        "_request_manager",
        MagicMock(side_effect=error, spec=client._request_manager),
    )
    with pytest.raises(LoginFailed):
        client.auth_log_in()


def test_api_key_auth_log_out_is_noop(monkeypatch):
    client = Client(
        host="localhost:8080",
        api_key="qbt_test_key",
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    post = MagicMock(spec=client._post)
    monkeypatch.setattr(client, "_post", post)
    client.auth_log_out()
    post.assert_not_called()


def test_api_key_no_relogin_retry_on_403(monkeypatch):
    client = Client(
        host="localhost:8080",
        api_key="qbt_test_key",
        VERIFY_WEBUI_CERTIFICATE=False,
    )
    monkeypatch.setattr(
        client,
        "_request_manager",
        MagicMock(side_effect=Forbidden403Error, spec=client._request_manager),
    )
    log_in = MagicMock(spec=client.auth_log_in)
    monkeypatch.setattr(client, "auth_log_in", log_in)

    # a 403 on a normal endpoint must propagate without attempting re-authentication
    with pytest.raises(Forbidden403Error):
        client._auth_request(
            http_method="get",
            api_namespace=APINames.Application,
            api_method="version",
        )
    log_in.assert_not_called()
