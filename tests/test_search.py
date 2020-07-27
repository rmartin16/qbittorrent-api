import time

import pytest

from qbittorrentapi import NotFound404Error
from qbittorrentapi.helpers import is_version_less_than
from qbittorrentapi.search import SearchJobDictionary, SearchStatusesList, SearchResultsDictionary


def test_update_plugins(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_update_plugins()
    else:
        client.search_update_plugins()

    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_update_plugins()
    else:
        client.search.update_plugins()
        time.sleep(2)
        for attempt in range(10):
            try:
                assert (any(entry for entry in reversed(client.log.main())
                            if 'All plugins are already up to date.' in entry['message'])
                        or any(entry for entry in reversed(client.log.main())
                               if 'Updating' in entry['message'])
                        )
                break
            except:
                time.sleep(1)


def test_enable_plugin(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_enable_plugin()
    else:
        for attempt in range(10):
            try:
                plugins = client.search_plugins()
                client.search_enable_plugin(plugins=(p['name'] for p in plugins), enable=False)
                time.sleep(1)
                assert all(not p['enabled'] for p in client.search_plugins())
                client.search_enable_plugin(plugins=(p['name'] for p in plugins), enable=True)
                time.sleep(1)
                assert all(p['enabled'] for p in client.search_plugins())
                break
            except:
                time.sleep(1)

    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search.enable_plugin()
    else:
        plugins = client.search.plugins
        client.search.enable_plugin(plugins=(p['name'] for p in plugins), enable=False)
        time.sleep(1)
        assert all(not p['enabled'] for p in client.search.plugins)
        client.search.enable_plugin(plugins=(p['name'] for p in plugins), enable=True)
        time.sleep(1)
        assert all(p['enabled'] for p in client.search.plugins)


def test_install_uninstall_plugin(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_install_plugin()
        with pytest.raises(NotImplementedError):
            client.search_uninstall_plugin()
    else:
        plugin_name = 'legittorrents'
        legit_torrents_url = 'https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/legittorrents.py'
        client.search_install_plugin(sources=legit_torrents_url)
        time.sleep(2)
        assert any(p['name'] == plugin_name for p in client.search.plugins)
        client.search_uninstall_plugin(names=plugin_name)
        time.sleep(2)
        assert all(p['name'] != plugin_name for p in client.search.plugins)

    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search.install_plugin()
        with pytest.raises(NotImplementedError):
            client.search.uninstall_plugin()
    else:
        plugin_name = 'legittorrents'
        legit_torrents_url = 'https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/legittorrents.py'
        client.search.install_plugin(sources=legit_torrents_url)
        time.sleep(2)
        assert any(p['name'] == plugin_name for p in client.search.plugins)
        client.search.uninstall_plugin(names=plugin_name)
        time.sleep(2)
        assert all(p['name'] != plugin_name for p in client.search.plugins)


def test_categories(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_categories()
    else:
        assert 'All categories' in client.search_categories()

    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search.categories()
    else:
        assert 'All categories' in client.search.categories()


def test_search(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_start()
    else:
        job = client.search_start(pattern='Ubuntu', plugins='enabled', category='all')
        assert isinstance(job, SearchJobDictionary)
        statuses = client.search_status(search_id=job['id'])
        assert isinstance(statuses, SearchStatusesList)
        assert statuses[0]['status'] == 'Running'
        results = client.search_results(search_id=job['id'], limit=1)
        assert isinstance(results, SearchResultsDictionary)
        results = job.results()
        assert isinstance(results, SearchResultsDictionary)
        client.search_stop(search_id=job['id'])
        time.sleep(1)
        statuses = client.search_status(search_id=job['id'])
        assert statuses[0]['status'] == 'Stopped'
        client.search_delete(search_id=job['id'])
        statuses = client.search_status()
        assert not statuses

    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_start()
    else:
        job = client.search.start(pattern='Ubuntu', plugins='enabled', category='all')
        assert isinstance(job, SearchJobDictionary)
        statuses = client.search.status(search_id=job['id'])
        assert isinstance(statuses, SearchStatusesList)
        assert statuses[0]['status'] == 'Running'
        results = client.search.results(search_id=job['id'], limit=1)
        assert isinstance(results, SearchResultsDictionary)
        client.search_stop(search_id=job['id'])
        time.sleep(1)
        statuses = client.search.status(search_id=job['id'])
        assert statuses[0]['status'] == 'Stopped'
        client.search.delete(search_id=job['id'])
        statuses = client.search.status()
        assert not statuses


def test_stop(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_stop(search_id=100)
    else:
        job = client.search_start(pattern='Ubuntu', plugins='enabled', category='all')
        client.search_stop(search_id=job.id)
        time.sleep(1)
        statuses = client.search.status(search_id=job['id'])
        assert statuses[0]['status'] == 'Stopped'

    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_stop(search_id=100)
    else:
        job = client.search_start(pattern='Ubuntu', plugins='enabled', category='all')
        client.search.stop(search_id=job.id)
        time.sleep(1)
        statuses = client.search.status(search_id=job['id'])
        assert statuses[0]['status'] == 'Stopped'

    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_stop(search_id=100)
    else:
        job = client.search_start(pattern='Ubuntu', plugins='enabled', category='all')
        job.stop()
        assert job.status()[0].status == 'Stopped'


def test_delete(client, api_version):
    if is_version_less_than(api_version, '2.1.1', lteq=False):
        with pytest.raises(NotImplementedError):
            client.search_stop(search_id=100)
    else:
        job = client.search_start(pattern='Ubuntu', plugins='enabled', category='all')
        job.delete()
        with pytest.raises(NotFound404Error):
            job.status()
