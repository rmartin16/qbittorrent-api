from pkg_resources import parse_version


def list2string(input_list=None, delimiter="|"):
    """
    Convert entries in a list to a concatenated string

    :param input_list: list to convert
    :param delimiter: delimiter for concatenation
    :return: if input is a list, concatenated string...else whatever the input was
    """
    if isinstance(input_list, list):
        return delimiter.join([str(x) for x in input_list])
    return input_list


def suppress_context(exc):
    """
    This is used to mask an exception with another one.

    For instance, below, the devide by zero error is masked by the CustomException.
        try:
            1/0
        except ZeroDivisionError:
            raise suppress_context(CustomException())

    Note: In python 3, the last line would simply be raise CustomException() from None
    :param exc: new Exception that will be raised
    :return: Exception to be raised
    """
    exc.__cause__ = None
    return exc


def is_version_less_than(ver1, ver2, lteq=True):
    """
    Determine if ver1 is equal to or later than ver2.

    :param ver1: version to check
    :param ver2: current version of application
    :param lteq: True for Less Than or Equals; False for just Less Than
    :return: True or False
    """
    if lteq:
        return parse_version(ver1) <= parse_version(ver2)
    return parse_version(ver1) < parse_version(ver2)


class APINames(object):
    """
    API names for API endpoints

    e.g 'torrents' in http://localhost:8080/api/v2/torrents/addTrackers
    """
    Authorization = "auth"
    Application = "app"
    Log = "log"
    Sync = "sync"
    Transfer = "transfer"
    Torrents = "torrents"
    RSS = "rss"
    Search = "search"

    def __init__(self):
        super(APINames, self).__init__()
