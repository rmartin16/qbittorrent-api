from collections import namedtuple
import logging
from os import environ

import pytest

from qbittorrentapi import Client, Request
from qbittorrentapi.exceptions import *
from qbittorrentapi.helpers import is_version_less_than
from qbittorrentapi.torrents import TorrentDictionary
from qbittorrentapi.torrents import TorrentInfoList

MockResponse = namedtuple('MockResponse', ('status_code', 'text'))


def test_log_in():
    client_good = Client()
    client_bad = Client(username='asdf', password='asdfasdf')

    assert client_good.auth_log_in() is None
    with pytest.raises(LoginFailed):
        client_bad.auth_log_in()


def test_log_in_via_auth():
    client_good = Client()
    client_bad = Client(username='asdf', password='asdfasdf')

    assert client_good.auth_log_in(username=environ.get('PYTHON_QBITTORRENTAPI_USERNAME'),
                                   password=environ.get('PYTHON_QBITTORRENTAPI_PASSWORD')) is None
    with pytest.raises(LoginFailed):
        client_bad.auth_log_in(username='asdf', password='asdfasdf')


def test_port(app_version):
    host, port = environ.get('PYTHON_QBITTORRENTAPI_HOST').split(':')
    client = Client(host=host, port=port)
    assert client.app.version == app_version


def test_log_out(client):
    client.auth_log_out()
    with pytest.raises(Forbidden403Error):
        # cannot call client.app.version directly since it will auto log back in
        client._get('app', 'version')
    client.auth_log_in()


def test_port(api_version):
    client = Client(host='localhost', port=8080)
    assert client.app.web_api_version == api_version


def test_simple_response(client, test_torrent):
    torrent = client.torrents_info()[0]
    assert isinstance(torrent, TorrentDictionary)
    torrent = client.torrents_info(SIMPLE_RESPONSE=True)[0]
    assert isinstance(torrent, dict)


def test_request_extra_params(client, torrent_hash):
    """ extra params can be sent directly to qBittorrent but there
    aren't any real use-cases so force it """
    json_response = client._post(_name='torrents', _method='info', hashes=torrent_hash).json()
    torrent = TorrentInfoList(json_response, client)[0]
    assert isinstance(torrent, TorrentDictionary)
    json_response = client._get(_name='torrents', _method='info', hashes=torrent_hash).json()
    torrent = TorrentInfoList(json_response, client)[0]
    assert isinstance(torrent, TorrentDictionary)


def test_mock_api_version():
    client = Client(MOCK_WEB_API_VERSION='1.5')
    assert client.app_web_api_version() == '1.5'


def test_disable_logging():
    _ = Client(DISABLE_LOGGING_DEBUG_OUTPUT=False)
    assert logging.getLogger('qbittorrentapi').level == logging.NOTSET
    assert logging.getLogger('requests').level == logging.NOTSET
    assert logging.getLogger('urllib3').level == logging.NOTSET

    _ = Client(DISABLE_LOGGING_DEBUG_OUTPUT=True)
    assert logging.getLogger('qbittorrentapi').level == logging.INFO
    assert logging.getLogger('requests').level == logging.INFO
    assert logging.getLogger('urllib3').level == logging.INFO


def test_verify_cert(api_version):
    client = Client(VERIFY_WEBUI_CERTIFICATE=False)
    assert client._VERIFY_WEBUI_CERTIFICATE is False
    assert client.app.web_api_version == api_version

    client = Client(VERIFY_WEBUI_CERTIFICATE=True)
    assert client._VERIFY_WEBUI_CERTIFICATE is True
    assert client.app.web_api_version == api_version

    environ['PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE'] = 'true'
    client = Client(VERIFY_WEBUI_CERTIFICATE=True)
    assert client._VERIFY_WEBUI_CERTIFICATE is False
    assert client.app.web_api_version == api_version


def test_api_connection_error():
    with pytest.raises(APIConnectionError):
        Client(host='localhost:8081').auth_log_in()


def test_request_http400(client, api_version, torrent_hash):
    with pytest.raises(MissingRequiredParameters400Error):
        client.torrents_file_priority(hash=torrent_hash)

    if is_version_less_than('4.1.5', api_version, lteq=False):
        with pytest.raises(InvalidRequest400Error):
            client.torrents_file_priority(hash=torrent_hash, file_ids='asdf', priority='asdf')


def test_http401():
    client = Client()
    _ = client.app.version
    # ensure cross site scripting protection is enabled
    client.app.preferences = dict(web_ui_csrf_protection_enabled=True)
    # simulate a XSS request
    with pytest.raises(Unauthorized401Error):
        client.app_version(headers={'X-Forwarded-Host': 'http://example.com'})


@pytest.mark.parametrize('params', ({}, {'hash': 'asdf'}, {'hashes': 'asdf|asdf'}))
def test_http404(client, params):
    with pytest.raises(NotFound404Error):
        client.torrents_rename(hash='asdf', new_torrent_name='erty')

    response = MockResponse(status_code=404, text='')
    with pytest.raises(HTTPError):
        Request.handle_error_responses(data={}, params=params, response=response)


def test_http409(client, api_version):
    if is_version_less_than('4.1.5', api_version, lteq=False):
        with pytest.raises(Conflict409Error):
            client.torrents.increase_priority(hashes='asdf')


def test_http415(client):
    with pytest.raises(UnsupportedMediaType415Error):
        client.torrents.add(torrent_files='/etc/hosts')


@pytest.mark.parametrize('status_code', (500, 503))
def test_http500(status_code):
    response = MockResponse(status_code=status_code, text='asdf')
    with pytest.raises(InternalServerError500Error):
        Request.handle_error_responses(data={}, params={}, response=response)


@pytest.mark.parametrize('status_code', (402, 406))
def test_http_error(status_code):
    response = MockResponse(status_code=status_code, text='asdf')
    with pytest.raises(HTTPError):
        Request.handle_error_responses(data={}, params={}, response=response)


def test_verbose_logging(caplog):
    client = Client(VERBOSE_RESPONSE_LOGGING=True)
    with caplog.at_level(logging.DEBUG, logger='qbittorrentapi'):
        with pytest.raises(NotFound404Error):
            client.torrents_rename(hash='asdf', new_torrent_name='erty')
    assert 'Response status' in caplog.text


def test_stack_printing(capsys):
    client = Client(PRINT_STACK_FOR_EACH_REQUEST=True)
    client.app.version
    captured = capsys.readouterr()
    assert 'print_stack()' in captured.err
