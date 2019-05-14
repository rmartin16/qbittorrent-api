qBittorrent v4.1+ Web API Client
================================
Python client implementation for qBittorrent Web API.

qBittorrent v4.1.0 and later is supported. This client interacts with qBittorrent's Web API v2.2+.

[qBittorrent Web API specification](https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation)

Installation
------------

*qbittorrent-api* is available on the Python Package Index (PyPI).

https://pypi.org/project/qbittorrent-api/

You can install *qbittorrent-api* using one of the following techniques:

- Use pip: ```pip install qbittorrent-api```
- Download the .zip or .tar.gz file from PyPI and install
- Download the source from Github and install

https://github.com/rmartin16/qbittorrent-api

Be sure to also install requests and attrdict.

Ensure that WebUI is enabled in qBittorrent: Tools -> Preferences -> Web UI

Getting Started
---------------
```python
from qbittorrentapi import Client
client = Client(host='localhost:8080', username='admin', password='adminadmin')
print("qBittorrent Version: %s" % client.app_version())
help(Client)
```

Configuration
-------------
* Using an untrusted certificate (eg one that is self-signed) for HTTPS WebUI
  * Either set `VERIFY_WEBUI_CERTIFICATE=True` when instantiating Client or set environment variable `PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE` to a non-null value.
  * Failure to do this will cause connections to qBittorrent to fail.
  * As a word of caution, doing this actually does turn off certificate verification. Therefore, for instance, potential man-in-the-middle attacks will not be detected and reported (since the error is suppressed). However, the connection will remain encrypted.
* Host, Username and password Defaults
  * These can be provided when instantiating Client or calling `client.auth_log_in(username='...', password='...')`.
  * Alternatively, set environment variables `PYTHON_QBITTORRENTAPI_HOST`, `PYTHON_QBITTORRENTAPI_USERNAME` and `PYTHON_QBITTORRENTAPI_PASSWORD`.
* API Endpoints Not Yet Implemented in the qBittorerent Host
  * By default, if a call is made to endpoint that doesn't yet exist on the host (eg the Search endpoints API v2.1.1), there's a debug logger output and None is returned.
  * Instantiate Client with `RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True` to raise UnimplementedError instead.
* Disable Logging Debug Output
  * Set `DISABLE_LOGGING_DEBUG_OUTPUT=True` when instantiating Client or disable logging manually:
    * ```logging.getLogger('qbittorrentapi').setLevel(logging.INFO) ```
    * ```logging.getLogger('requests').setLevel(logging.INFO) ```
    * ```logging.getLogger('urllib3').setLevel(logging.INFO) ```

Direct API Endpoint Access
--------------------------
**The interface to the direct API endpoints is stable and backwards compatibility is expected.**

The API is separated in to eight namespaces for the API endpoints:
* Authentication (auth)
* Application (app)
* Log (log)
* Sync (sync)
* Transfer (transfer)
* Torrent Management (torrents)
* RSS (rss)
* Search (search)

To use this package to directly access those endpoints:

```python
response = client.<name>_<api method>(<arguments>)
```
Replace `<name>` with one of the eight namespaces above and `<api method>` with a relevant endpoint.

For instance:
```python
torrent_list = client.torrents_info(status_filter='active')
```

The responses from the API calls will be strings or a dedicated object for the endpoint. In general, the non-string responses are extend Dictionaries and Lists.


Interaction Layer Usage (experimental)
--------------------------------------
**The interaction layer is still undergoing changes. Backwards compatibility will not be guaranteed.**

The package also contains more robust interfaces to the API endpoints. For each of the eight namespaces, there is an interface to the relevant API endpoints.

An example for the Application namespace:
```Python
ver = client.application.version
api_ver = client.application.api_web_version
prefs = client.application.preferences
is_dht_enabled = client.application.preferences.dht
client.application.preferences.dht = not is_dht_enabled
```
For each namespace, any endpoints without parameters or a return value is implemented as a property. All other endpoints are implemented as methods; some of the methods have extended usage as well.

For instance, the log/main endpoint has extended usage:
```python
complete_log = client.log.main()
normal_log = client.log.main.normal()
warning_log = client.log.main.warning()
critical_log = client.log.main.critical()
```
The most extended namespace is Torrents.
```python
# Gathering torrents
torrent_list = client.torrents.info()
torrent_list_active = client.torrents.info.active()
torrent_list_active_partial = client.torrents.active(limit=100, offset=200)
torrent_list_downloading = client.torrents.info.downloading()

# Torrent looping
for torrent in torrent_list:
  print(torrent.name)

# Actions for multiple torrents
client.torrents.pause(hashes=['...', '...'])
client.torrents.recheck(hashes=['...', '...'])
# or just do all torrent 
client.torrents.pause.all()
client.torrents.recheck.all()
client.torrents.resume.all()
```

Once you have a torrent, there's also a litany of interactions.
```python
hash = torrent.info.hash  # as well the rest fo the properties from torrents/info endpoint
properties = torrent.properties
trackers = torrent.trackers
files = torrent.files
# Action methods
torrent.edit_tracker(original_url="...", new_url="...")
torrent.remove_trackers(urls='http://127.0.0.2/')
torrent.rename(new_torrent_name="...")
torrent.resume()
torrent.pause()
torrent.recheck()
torrent.torrents_top_priority()
torrent.set_location(location='/home/user/torrents/')
torrent.set_category(category='video')
# or set them via assignment
torrent.set_location = '/home/user/torrents/'
torrent.set_category = 'video'
```
This continues for all endpoints available to the namespace.

Search also have extended usage.
```python
search_job = client.search.start(pattern='Ubuntu', categories='all', plugins='all')
while True:
  if search_job.status()[0].status == 'Stopped':
    break
print(search_job.results())
search_job.delete()
```

Interaction Layer Notes
-----------------------
* All endpoints are available with and without the endpoint's namespace attached.
  * So, `client.torrents.torrents_resume()` and `client.torrents.resume()` are the same.
  * This also extends to endpoints with spaces in their name. So, `web_api_version` and `webapiVersion` are the same.
* When invoking the API calls, you can use the parameters implemented in the python code or those specified in the API documentation.
  * So, `torrents_rename(hash='...', new_torrent_name="...")` and `torrents_rename(hash='...', name="...")` are the same.

Interaction Layer Details
-------------------------
* Application
  * Properties
    * version
    * web_api_version
    * build_info
    * default_save_path
    * preferences (supports assignment)
  * Methods
    * shutdown
* Log
  * Methods
    * main
    * peers
* Sync
  * Methods
    * maindata
    * torrent_peers
* Transfer
  * Properties
    * info
    * speed_limits_mode (supports assignment)
    * download_limit (supports assignment)
    * upload_limit (supports assignment)
  * Methods
    * set_download_limit
    * set_upload_limit
    * toggle_speed_limits_mode
* Torrents
  * Methods
    * resume
    * pause
    * delete
    * recheck
    * reannounce
    * increase_priority
    * decrease_priority
    * top_priority
    * bottom_priority
    * download_limit
    * set_download_limit
    * set_share_limits
    * upload_limit
    * set_upload_limit
    * set_location
    * set_category
    * set_auto_management
    * toggle_sequential_download
    * toggle_first_last_piece_priority
    * set_force_start
    * set_super_seeding
* Torrent
  * Properties
    * info
    * properties
    * trackers
    * webseeds
    * files
    * piece_states
    * piece_hashes
    * download_limit (supports assignment)
    * upload_limit (supports assignment)
  * Methods
    * add_trackers
    * edit_tracker
    * remove_trackers
    * file_priority
    * filePrio
    * rename
    * set_location (supports assignment)
    * set_category (supports assignment)
    * set_auto_management (supports assignment)
    * set_force_feeding (supports assignment)
    * set_super_seeding (supports assignment)
    * AND all the Torrents methods above
* Torrent Categories
  * Properties
    * categories
  * Methods
    * create_category
    * edit_category
    * remove_categories
* RSS
  * Properties
    * rules
    * items_without_data
    * items_with_data
  * Methods
    * add_folder
    * add_feed
    * remove_item
    * move_item
    * items
    * set_rule
    * rename_rule
    * remove_rule
* Search
  * Properties
    * plugins
  * Methods
    * start
    * stop
    * status
    * results
    * delete
    * categories
    * install_plugin
    * uninstall_plugin
    * enable_plugin
    * update_plugins
* Seach Job
  * Methods
    * stop
    * results
    * status
    * delete

Exceptions
----------
TODO

Change Log
----------
* Version 0.2
   * Introduced the "interaction layer" for transparent interaction with the qBittorrent API.
* Version 0.1.1
   * Complete implementation of each endpoint for qBittorrent Web API v2
