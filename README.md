qBittorrent Web API Client
================================
Python client implementation for qBittorrent Web API. Supports qBittorrent v4.1.0+ (i.e. Web API v2.0+).

[qBittorrent Web API specification](https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation)

Features
------------
* The entire qBittorent Web API is implemented.
* qBittorrent version checking for an endpoint's existence/features is automatically handled.
* All Python versions are supported.
* If the authentication cookie expires, a new one is automatically requested in line with the request.

Installation
------------

*qbittorrent-api* is available on the Python Package Index (PyPI).

https://pypi.org/project/qbittorrent-api/

Install via pip:

```pip install qbittorrent-api```

Install specific release:

```pip install git+https://github.com/rmartin16/qbittorrent-api.git@v0.3.2#egg=qbittorrent-api```

Install direct from master:

```pip install git+https://github.com/rmartin16/qbittorrent-api.git#egg=qbittorrent-api```

Also be sure urllib3, requests, and attrdict are installed.

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
* Using an untrusted certificate for HTTPS WebUI
  * Instantiate Client with `VERIFY_WEBUI_CERTIFICATE=False` or set environment variable `PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE` to a non-null value.
  * Failure to do this for will cause connections to qBittorrent to fail.
  * As a word of caution, doing this actually does turn off certificate verification. Therefore, for instance, potential man-in-the-middle attacks will not be detected and reported (since the error is suppressed). However, the connection will remain encrypted.
* Host, Username and password Defaults
  * These can be provided when instantiating Client or calling `client.auth_log_in(username='...', password='...')`.
  * Alternatively, set environment variables `PYTHON_QBITTORRENTAPI_HOST`, `PYTHON_QBITTORRENTAPI_USERNAME` and `PYTHON_QBITTORRENTAPI_PASSWORD`.
* API Endpoints Not Yet Implemented in the qBittorrent Host
  * By default, if a call is made to endpoint that doesn't yet exist on the host (e.g. the Search endpoints were introduced in Web API v2.1.1), there's a debug logger output and None is returned.
  * To raise UnimplementedError instead, instantiate Client with `RAISE_UNIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True`.
* Disable Logging Debug Output
  * Instantiate Client with `DISABLE_LOGGING_DEBUG_OUTPUT=True` or manually disable logging for the relevant packages:
    * ```logging.getLogger('qbittorrentapi').setLevel(logging.INFO) ```
    * ```logging.getLogger('requests').setLevel(logging.INFO) ```
    * ```logging.getLogger('urllib3').setLevel(logging.INFO) ```

Direct API Endpoint Access
--------------------------
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

The responses from the API calls are strings (e.g. app/version) or an extended Dictionary or List object (e.g. torrents/trackers).

Each namespace endpoint's method name is PEP8-ified. However, they are all aliased to the endpoint's name as implemented in qBittorrent's Web API. So, for example, `client.app_web_api_version()` and `client.app_webapiVersion()` are equivilent.


Interaction Layer Usage
--------------------------------------
The package also contains more robust interfaces to the API endpoints. For each of the eight namespaces, there is an interface to the relevant API endpoints. Of note, I created an additional namespace for torrent categories.

An example for the Application namespace:
```Python
ver = client.app.version
api_ver = client.app.api_web_version
prefs = client.app.preferences
is_dht_enabled = client.application.preferences.dht
client.application.preferences = dict(dht=(not is_dht_enabled))
```

For each namespace, all endpoints with a return value and no parameters are implemented as a property. All other endpoints are implemented as methods; some of the methods have extended usage as well.

For example, the log/main endpoint has extended usage:
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
```

Search extended usage.
```python
search_job = client.search.start(pattern='Ubuntu', categories='all', plugins='all')
while (search_job.status()[0].status != 'Stopped'):
  time.sleep(.1)
print(search_job.results())
search_job.delete()
```

Interaction Layer Notes
-----------------------
* All endpoints are available with and without the endpoint's namespace attached.
  * So, `client.torrents.torrents_resume()` and `client.torrents.resume()` are the same.
  * As mentioned in direct API access `client.app.web_api_version` and `client.app.webapiVersion` are the same.
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
      * Methods
        * info
        * normal
        * warning
        * critical
    * peers
* Sync
  * Methods
    * maindata
      * Methods
        * delta
        * reset_rid
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
    * Note: each of these "methods" supports the all() method
    * info
      * Methods
        * downloading
        * completed
        * paused
        * active
        * inactive
        * resumed
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
    * set_location
    * set_category
    * set_auto_management
    * set_force_feeding
    * set_super_seeding
    * AND all the Torrents methods above
* Torrent Categories
  * Properties
    * categories
  * Methods
    * create_category
    * edit_category
    * remove_categories
* Torrent Tags
  * Properties
    * tags
  * Methods
    * add_tags
    * remove_tags
    * create_tags
    * delete_tags
* RSS
  * Properties
    * rules
  * Methods
    * add_folder
    * add_feed
    * remove_item
    * refresh_item
    * move_item
    * items
      * Methods
        * without_data
        * woth_data
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
To see the exceptions an endpoint can raise, use `help(Client.<namespace>_<method>)`.

For example:
```
>>> from qbittorrentui import Client
>>> help(Client.torrents_add)

Help on function torrents_add in module qbittorrentapi.torrents:

torrents_add(self, urls=None, torrent_files=None, save_path=None, cookie=None, category=None, is_skip_checking=None, is_paused=None, is_root_folder=None, rename=None, upload_limit=None, download_limit=None, use_auto_torrent_management=None, is_sequential_download=None, is_first_last_piece_priority=None, **kwargs)
    Add one or more torrents by URLs and/or torrent files.
    
    Exceptions:
        UnsupportedMediaType415Error if file is not a valid torrent file
        FileNotFoundError if a torrent file doesn't exist
        PermissionError if read permission is denied to torrent file
    
    :param urls: List of URLs (http://, https://, magnet: and bc://bt/)
    :param torrent_files: list of torrent files
    :param save_path: location to save the torrent data
    :param cookie: cookie to retrieve torrents by URL
    :param category: category to assign to torrent(s)
    :param is_skip_checking: skip hash checking
    :param is_paused: True to start torrent(s) paused
    :param is_root_folder: True or False to create root folder
    :param rename: new name for torrent(s)
    :param upload_limit: upload limit in bytes/second
    :param download_limit: donwnload limit in bytes/second
    :param use_auto_torrent_management: True or False to use automatic torrent management
    :param is_sequential_download: True or False for sequential download
    :param is_first_last_piece_priority: True or False for first and last piece download priority
    :return: "Ok." for success and ""Fails." for failure

```


```python
class APIError(Exception):
    pass

class LoginFailed(APIError):
    pass

# connection errors that aren't HTTP errors...like an SSL error or a timeout
class APIConnectionError(APIError):
    pass

# all errors from a successful connection to qbittorrent are returned as HTTP errors
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

# Endpoint call is missing one or more required parameters
class MissingRequiredParameters400Error(HTTP400Error):
    pass

# One or more parameters are malformed
class InvalidRequest400Error(HTTP400Error):
    pass

# Primarily reserved for XSS and host header issues.
class Unauthorized401Error(HTTP401Error):
    pass

# Not logged in or calling an API method that isn't public.
class Forbidden403Error(HTTP403Error):
    pass

# Almost certainly, this means the torrent hash didn't find a torrent...
# Technically, this can happen if the endpoint doesn't exist...but that also means there's a bug in this implementation
class NotFound404Error(HTTP404Error):
    pass

# Returned if parameters don't make sense...
class Conflict409Error(HTTP409Error):
    pass

# torrents/add endpoint will return this for invalid URL(s)
class UnsupportedMediaType415Error(HTTP415Error):
    pass

# Returned if qBittorent craps on itself while processing the request...
class InternalServerError500Error(HTTP500Error):
    pass
```
