from typing import Callable
from typing import Set
from typing import Text
from typing import Type
from typing import TypeVar

from qbittorrentapi.request import Request

T = TypeVar("T", bound=Request)
API_RETURN_T = TypeVar("API_RETURN_T")

class alias:
    aliases: Set[Text]
    def __init__(self, *aliases: Text) -> None: ...
    def __call__(
        self, f: Callable[..., API_RETURN_T]
    ) -> Callable[..., API_RETURN_T]: ...

def aliased(aliased_class: Type[T]) -> Type[T]: ...
def login_required(
    func: Callable[..., API_RETURN_T]
) -> Callable[..., API_RETURN_T]: ...
def handle_hashes(func: Callable[..., API_RETURN_T]) -> Callable[..., API_RETURN_T]: ...
def endpoint_introduced(
    version_introduced: Text, endpoint: Text
) -> Callable[[Callable[..., API_RETURN_T]], Callable[..., API_RETURN_T]]: ...
def version_removed(
    version_obsoleted: Text, endpoint: Text
) -> Callable[[Callable[..., API_RETURN_T]], Callable[..., API_RETURN_T]]: ...
def check_for_raise(client: Request, error_message: Text) -> None: ...
