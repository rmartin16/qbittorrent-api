class APIError(Exception):
    pass


class LoginFailed(APIError):
    pass


class APIConnectionError(APIError):
    pass


class HTTPError(APIError):
    pass


class HTTP400Error(HTTPError):
    pass


class HTTP401Error(HTTPError):
    pass


class HTTP403Error(HTTPError):
    pass


class HTTP404Error(HTTPError):
    pass


class HTTP409Error(HTTPError):
    pass


class HTTP415Error(HTTPError):
    pass


class HTTP500Error(HTTPError):
    pass


class MissingRequiredParameters400Error(HTTP400Error):
    pass


class InvalidRequest400Error(HTTP400Error):
    pass


class Unauthorized401Error(HTTP401Error):
    pass


class Forbidden403Error(HTTP403Error):
    pass


class NotFound404Error(HTTP404Error):
    pass


class Conflict409Error(HTTP409Error):
    pass


class UnsupportedMediaType415Error(HTTP415Error):
    pass


class InternalServerError500Error(HTTP500Error):
    pass
