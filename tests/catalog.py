"""
A catalog of the client's API surface, derived from the library itself.

Every endpoint is reachable under several names. ``torrents_add_webseeds`` is
also spelled ``torrents_addWebSeeds`` on the client, and ``add_webseeds`` /
``addWebSeeds`` on the ``torrents`` interface. The camelCase spellings are plain
assignments (``torrents_addWebSeeds = torrents_add_webseeds``), so they are the
*same* function object rather than a second implementation.

Each endpoint also declares which Web API versions it exists in, by passing
``version_introduced`` and/or ``version_removed`` to the request helper it calls.

Deriving all of that once, here, lets the surface tests parametrize over every
endpoint instead of restating the same facts by hand for each one. Nothing in
this module talks to qBittorrent; it only reads the library.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from collections import defaultdict
from dataclasses import asdict, dataclass

import qbittorrentapi
from qbittorrentapi.definitions import APINames

#: Names of the request helpers an API method calls to reach qBittorrent.
REQUEST_HELPERS = {"_get", "_get_cast", "_post", "_post_cast", "_request_manager"}

#: Keyword arguments to those helpers that describe the endpoint.
ENDPOINT_KWARGS = ("_name", "_method", "version_introduced", "version_removed")

API_NAMESPACES = {namespace.value for namespace in APINames if namespace.value}


@dataclass(frozen=True, order=True)
class Endpoint:
    """One qBittorrent Web API endpoint, as exposed by the client."""

    #: client method name, e.g. ``torrents_add_webseeds``
    primary: str
    #: API namespace, e.g. ``torrents``
    namespace: str
    #: Web API method, e.g. ``addWebSeeds``
    api_method: str
    #: other client spellings bound to the same callable
    client_aliases: tuple[str, ...] = ()
    #: Web API version the endpoint first appeared in, if it is gated
    version_introduced: str = ""
    #: Web API version the endpoint was removed in, if it was removed
    version_removed: str = ""


def _literal(node: ast.expr) -> str | None:
    """Value of a constant or an ``APINames.X`` attribute reference."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        # e.g. APINames.Torrents -> "torrents"
        namespace = getattr(APINames, node.attr, None)
        return str(namespace.value) if namespace is not None else node.attr
    return None


def _endpoint_kwargs(func: object) -> dict[str, str]:
    """Read the endpoint-describing kwargs out of ``func``'s request call."""
    try:
        source = textwrap.dedent(inspect.getsource(func))  # type: ignore[arg-type]
    except (OSError, TypeError):  # pragma: no cover - builtins have no source
        return {}

    found: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        called = node.func
        name = called.attr if isinstance(called, ast.Attribute) else None
        if name not in REQUEST_HELPERS:
            continue
        for keyword in node.keywords:
            if keyword.arg in ENDPOINT_KWARGS:
                value = _literal(keyword.value)
                if value is not None:
                    # first call wins; later ones are version-specific fallbacks
                    found.setdefault(keyword.arg, value)
    return found


def _client_methods() -> dict[object, list[str]]:
    """Client API methods grouped by the callable they are bound to."""
    grouped: dict[object, list[str]] = defaultdict(list)
    for name in dir(qbittorrentapi.Client):
        if name.startswith("_") or name.split("_")[0] not in API_NAMESPACES:
            continue
        func = inspect.getattr_static(qbittorrentapi.Client, name)
        if callable(func):
            grouped[func].append(name)
    return grouped


def build_catalog() -> tuple[Endpoint, ...]:
    """Derive every API endpoint the client exposes."""
    endpoints = []
    for func, names in _client_methods().items():
        # the snake_case spelling is the canonical one; camelCase are aliases
        snake_case = sorted(name for name in names if name.lower() == name)
        primary = snake_case[0] if snake_case else sorted(names)[0]

        kwargs = _endpoint_kwargs(func)
        if not kwargs.get("_name"):
            # not a request-issuing method, so there is no endpoint to catalog
            continue
        # a few endpoints choose their Web API method at runtime (torrents_stop
        # calls "stop" or "pause" depending on the version), so there is no
        # literal to read and api_method is left empty

        endpoints.append(
            Endpoint(
                primary=primary,
                namespace=kwargs.get("_name", ""),
                api_method=kwargs.get("_method", ""),
                client_aliases=tuple(sorted(set(names) - {primary})),
                version_introduced=kwargs.get("version_introduced", ""),
                version_removed=kwargs.get("version_removed", ""),
            )
        )
    return tuple(sorted(endpoints))


CATALOG = build_catalog()


def as_snapshot() -> str:
    """The catalog as stable, diffable JSON."""
    import json

    return json.dumps([asdict(e) for e in CATALOG], indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    print(as_snapshot(), end="")
