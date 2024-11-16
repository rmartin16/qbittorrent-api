from __future__ import annotations

from logging import Logger, getLogger
from types import TracebackType
from typing import TYPE_CHECKING

from requests import Response

from qbittorrentapi._version_support import Version
from qbittorrentapi.definitions import APIKwargsT, APINames, ClientCache
from qbittorrentapi.exceptions import (
    LoginFailed,
    UnsupportedQbittorrentVersion,
)
from qbittorrentapi.request import Request

if TYPE_CHECKING:
    from qbittorrentapi.client import Client

logger: Logger = getLogger(__name__)


class AuthAPIMixIn(Request):
    """
    Implementation of all ``Authorization`` API methods.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> _ = client.is_logged_in
        >>> client.auth_log_in(username="admin", password="adminadmin")
        >>> client.auth_log_out()
    """  # noqa: E501

    @property
    def auth(self) -> Authorization:
        """Allows for transparent interaction with Authorization endpoints."""
        if self._authorization is None:
            self._authorization = Authorization(client=self)
        return self._authorization

    @property
    def authorization(self) -> Authorization:
        return self.auth

    @property
    def is_logged_in(self) -> bool:
        """
        Returns True if low-overhead API call succeeds; False otherwise.

        There isn't a reliable way to know if an existing session is still valid without
        attempting to use it. qBittorrent invalidates cookies when they expire.

        :returns: ``True``/``False`` if current authorization cookie is accepted by qBittorrent
        """  # noqa: E501
        try:
            # use _request_manager() directly so log in is not attempted
            self._request_manager(
                http_method="post",
                api_namespace=APINames.Application,
                api_method="version",
            )
        except Exception:
            return False
        else:
            return True

    def auth_log_in(
        self,
        username: str | None = None,
        password: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """
        Log in to qBittorrent host.

        :raises LoginFailed: if credentials failed to log in
        :raises Forbidden403Error: if user is banned...or not logged in

        :param username: username for qBittorrent client
        :param password: password for qBittorrent client
        """
        if username:
            self.username = username
            self._password = password or ""

        # trigger a (re-)initialization in case this is a new instance of qBittorrent
        self._initialize_context()

        creds = {"username": self.username, "password": self._password}
        auth_response = self._post_cast(
            _name=APINames.Authorization,
            _method="login",
            data=creds,
            response_class=Response,
            **kwargs,
        )

        if auth_response.text != "Ok.":
            logger.debug("Login failed")
            raise LoginFailed()
        logger.debug("Login successful")

        # check if the connected qBittorrent is fully supported by this Client yet
        if self._RAISE_UNSUPPORTEDVERSIONERROR:
            app_version = self.app_version()  # type: ignore
            api_version = self.app_web_api_version()  # type: ignore
            if not (
                Version.is_api_version_supported(api_version)
                and Version.is_app_version_supported(app_version)
            ):
                raise UnsupportedQbittorrentVersion(
                    "This version of qBittorrent is not fully supported => "
                    f"App Version: {app_version} API Version: {api_version}"
                )

    @property
    def _SID(self) -> str | None:
        """
        Authorization session cookie from qBittorrent using default cookie name `SID`.

        Backwards compatible for :meth:`~AuthAPIMixIn._session_cookie`.
        """
        return self._session_cookie()

    def _session_cookie(self, cookie_name: str = "SID") -> str | None:
        """
        Authorization session cookie from qBittorrent.

        :param cookie_name: Name of the authorization cookie; configurable after v4.5.0.
        """
        if self._http_session:
            return self._http_session.cookies.get(cookie_name, None)
        return None

    def auth_log_out(self, **kwargs: APIKwargsT) -> None:
        """End session with qBittorrent."""
        # Originally, if log out failed authentication, the client would re-authenticate
        # and then log out of that session. With the change to avoid retrying failed
        # auth calls, only attempt to log out if the current authentication is valid.
        if self.is_logged_in:
            self._post(_name=APINames.Authorization, _method="logout", **kwargs)

    def __enter__(self) -> Client:
        self.auth_log_in()
        return self  # type: ignore[return-value]

    def __exit__(
        self,
        exctype: type[BaseException] | None,
        excinst: BaseException | None,
        exctb: TracebackType | None,
    ) -> None:
        self.auth_log_out()


class Authorization(ClientCache[AuthAPIMixIn]):
    """
    Allows interaction with the ``Authorization`` API endpoints.

    :Usage:
        >>> from qbittorrentapi import Client
        >>> client = Client(host="localhost:8080", username="admin", password="adminadmin")
        >>> is_logged_in = client.auth.is_logged_in
        >>> client.auth.log_in(username="admin", password="adminadmin")
        >>> client.auth.log_out()
    """  # noqa: E501

    @property
    def is_logged_in(self) -> bool:
        """Implements :meth:`~AuthAPIMixIn.is_logged_in`."""
        return self._client.is_logged_in

    def log_in(
        self,
        username: str | None = None,
        password: str | None = None,
        **kwargs: APIKwargsT,
    ) -> None:
        """Implements :meth:`~AuthAPIMixIn.auth_log_in`."""
        return self._client.auth_log_in(username=username, password=password, **kwargs)

    def log_out(self, **kwargs: APIKwargsT) -> None:
        """Implements :meth:`~AuthAPIMixIn.auth_log_out`."""
        return self._client.auth_log_out(**kwargs)
