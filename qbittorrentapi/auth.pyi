from typing import Any
from typing import Optional
from typing import Text

from qbittorrentapi.definitions import ClientCache
from qbittorrentapi.request import Request

KWARGS = Any

class Authorization(ClientCache):
    @property
    def is_logged_in(self) -> bool: ...
    def log_in(
        self,
        username: Optional[Text] = None,
        password: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    def log_out(self, **kwargs: KWARGS) -> None: ...

class AuthAPIMixIn(Request):
    @property
    def auth(self) -> Authorization: ...
    authorization = auth
    @property
    def is_logged_in(self) -> bool: ...
    def auth_log_in(
        self,
        username: Optional[Text] = None,
        password: Optional[Text] = None,
        **kwargs: KWARGS
    ) -> None: ...
    @property
    def _SID(self) -> Optional[Text]: ...
    def auth_log_out(self, **kwargs: KWARGS) -> None: ...
