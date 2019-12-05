from requests.exceptions import RequestException


class APIError(Exception):
    """
    Base error for all exceptions from this Client.
    """
    pass


class FileError(IOError, APIError):
    """
    Base class for all exceptions for file handling.
    """
    pass


class TorrentFileError(FileError):
    """
    Base class for all exceptions for torrent files.
    """
    pass


class TorrentFileNotFoundError(TorrentFileError):
    """
    Specified torrent file does not appear to exist.
    """
    pass


class TorrentFilePermissionError(TorrentFileError):
    """
    Permission was denied to read the specified torrent file.
    """
    pass


class APIConnectionError(RequestException, APIError):
    """
    Base class for all communications errors including HTTP errors.
    """
    pass


class LoginFailed(APIConnectionError):
    """
    This can technically be raised with any request since log in may be attempted for any request and could fail.
    """
    pass


class HTTPError(APIConnectionError):
    """
    Base error for all HTTP errors. All errors following a successful connection to qBittorrent are returned as HTTP statuses.
    """
    pass


class HTTP4XXError(HTTPError):
    """
    Base error for all HTTP 4XX statuses.
    """
    pass


class HTTP5XXError(HTTPError):
    """
    Base error for all HTTP 5XX statuses.
    """
    pass


class HTTP400Error(HTTP4XXError):
    pass


class HTTP401Error(HTTP4XXError):
    pass


class HTTP403Error(HTTP4XXError):
    pass


class HTTP404Error(HTTP4XXError):
    pass


class HTTP409Error(HTTP4XXError):
    pass


class HTTP415Error(HTTP4XXError):
    pass


class HTTP500Error(HTTP5XXError):
    pass


class MissingRequiredParameters400Error(HTTP400Error):
    """
    Endpoint call is missing one or more required parameters.
    """
    pass


class InvalidRequest400Error(HTTP400Error):
    """
    One or more endpoint arguments are malformed.
    """
    pass


class Unauthorized401Error(HTTP401Error):
    """
    Primarily reserved for XSS and host header issues.
    """
    pass


class Forbidden403Error(HTTP403Error):
    """
    Not logged in, IP has been banned, or calling an API method that isn't public.
    """
    pass


class NotFound404Error(HTTP404Error):
    """
    This should mean qBittorrent couldn't find a torrent for the torrent hash.
    It is also possible this means the endpoint doesn't exist in qBittorrent...but that also means this Client has a bug.
    """
    pass


class Conflict409Error(HTTP409Error):
    """
    Returned if arguments don't make sense specific to the endpoint.
    """
    pass


class UnsupportedMediaType415Error(HTTP415Error):
    """
    torrents/add endpoint will return this for invalid URL(s) or files.
    """
    pass


class InternalServerError500Error(HTTP500Error):
    """
    Returned if qBittorent craps on itself while processing the request...
    """
    pass
