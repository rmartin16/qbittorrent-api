qBittorrent Web API Client
================================
Python client implementation for qBittorrent Web API. Supports qBittorrent v4.1.0+ (i.e. Web API v2.0+).

  * [Features](#features)
  * [Installation](#installation)
  * [Getting Started](#getting-started)
  * [API Documentation](#api-documentation)
  * [Behavior & Configuration](#behavior--configuration)
  * [Direct API Endpoint Access](#direct-api-endpoint-access)
  * [Interaction Layer Usage](#interaction-layer-usage)
  * [Interaction Layer Notes](#interaction-layer-notes)
  * [Interaction Layer Details](#interaction-layer-details)
  * [Exceptions](#exceptions)
  
The full qBittorrent Web API specification is documented on their [wiki](https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation).

Features
------------
* The entire qBittorent Web API is implemented.
* qBittorrent version checking for an endpoint's existence/features is automatically handled.
* All Python versions are supported.
* If the authentication cookie expires, a new one is automatically requested in line with any API call.

Installation
------------
* Install via pip from [PyPI](https://pypi.org/project/qbittorrent-api/):
  * `pip install qbittorrent-api`
* Install specific release:
  * `pip install git+https://github.com/rmartin16/qbittorrent-api.git@v0.3.2#egg=qbittorrent-api`
* Install direct from master:
  * `pip install git+https://github.com/rmartin16/qbittorrent-api.git#egg=qbittorrent-api`
* Ensure urllib3, requests, and attrdict are installed. (These are installed autuomatically using the methods above.)
* Enable WebUI in qBittorrent: Tools -> Preferences -> Web UI
* If the Web API will be exposed to the Internet (i.e. made available outside your network), please [do it properly](https://github.com/qbittorrent/qBittorrent/wiki/Linux-WebUI-HTTPS-with-Let's-Encrypt-certificates-and-NGINX-SSL-reverse-proxy).

Getting Started
---------------
```python
import qbittorrentapi

# instantiate a Client using the appropriate WebUI configuration
qbt_client = qbittorrentapi.Client(host='localhost:8080', username='admin', password='adminadmin')

# the Client will automatically acquire/maintain a logged in state in line with any request.
# therefore, this is not necessary; however, you many want to test the provided login credentials.
try:
    qbt_client.auth_log_in()
except qbittorrentapi.LoginFailed as e:
    print(e)

# display qBittorrent info
print(f'qBittorrent: {qbt_client.app.version}')
print(f'qBittorrent Web API: {qbt_client.app.web_api_version}')
for k,v in qbt_client.app.build_info.items(): print(f'{k}: {v}')

# retrieve and show all torrents
for torrent in qbt_client.torrents_info():
    print(f'{torrent.hash[-6:]}: {torrent.name} ({torrent.state})')

# pause all torrents
qbt_client.torrents.pause.all()
```

API Documentation
---------------
The Client's methods all document their own description, expected arguments, possible exceptions, and return value.

For best results, use the "most primitive" form of the API call. So, `qbt_client.torrents_pause` instead of `qbt_client.torrents.pause`.

```python
help(qbt_client.torrents_add)
help(qbt_client.torrents_add_trackers)
```

Behavior & Configuration
-------------
* **WARNING**: Using an untrusted (e.g. self-signed) certificate for HTTPS WebUI
  * Instantiate Client with `VERIFY_WEBUI_CERTIFICATE=False` or set environment variable `PYTHON_QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE` to a non-null value.
  * Failure to do this for will cause connections to qBittorrent to fail.
  * As a word of caution, doing this actually does turn off certificate verification. Therefore, for instance, potential man-in-the-middle attacks will not be detected and reported (since the error is suppressed). However, the connection will remain encrypted.
* Host, Username and password Defaults
  * These can be provided when instantiating Client or calling `qbt_client.auth_log_in(username='...', password='...')`.
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
response = qbt_client.<name>_<api method>(<arguments>)
```
Replace `<name>` with one of the eight namespaces (from within the parentheses) above and `<api method>` with a relevant endpoint.

For instance:
```python
torrent_list = qbt_client.torrents_info(status_filter='active')
```

The responses from the API calls are strings (e.g. app/version) or an extended Dictionary or List object (e.g. torrents/trackers).

Each namespace endpoint's method name is [PEP8](https://www.python.org/dev/peps/pep-0008/)-ified. However, they are all aliased to the endpoint's name as implemented in qBittorrent's Web API. So, for example, `qbt_client.app_web_api_version()` and `qbt_client.app_webapiVersion()` are equivalent. This is also true for the API methods' arguments; so, `qbt_client.torrents_add(urls='...', save_path='/torrents')` and `qbt_client.torrents_add(urls='...', savepath='/torrents')` are equivalent. This is intended to allow use of this Client only depending on qBittorrent's own [Web API documentation](https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation).


Interaction Layer Usage
--------------------------------------
The package also contains more robust interfaces to the API endpoints. For each of the eight namespaces, there is an interface to the relevant API endpoints. Of note, I created additional namespaces for torrent categories and torrent tags.

An example for the Application namespace:
```Python
ver = qbt_client.app.version
api_ver = qbt_client.app.api_web_version
prefs = qbt_client.app.preferences
is_dht_enabled = qbt_client.application.preferences.dht
qbt_client.application.preferences = dict(dht=(not is_dht_enabled))
```

For each namespace, all endpoints with a return value and no parameters are implemented as a property. All other endpoints are implemented as methods; some of the methods have extended usage as well.

For example, the log/main endpoint has extended usage:
```python
complete_log = qbt_client.log.main()
normal_log = qbt_client.log.main.normal()
warning_log = qbt_client.log.main.warning()
critical_log = qbt_client.log.main.critical()
```
The most extended namespace is Torrents.
```python
# Gathering torrents
torrent_list = qbt_client.torrents.info()
torrent_list_active = qbt_client.torrents.info.active()
torrent_list_active_partial = qbt_client.torrents.active(limit=100, offset=200)
torrent_list_downloading = qbt_client.torrents.info.downloading()

# Torrent looping
for torrent in torrent_list:
  print(torrent.name)

# Actions for multiple torrents
qbt_client.torrents.pause(hashes=['...', '...'])
qbt_client.torrents.recheck(hashes=['...', '...'])
# or just do all torrent 
qbt_client.torrents.pause.all()
qbt_client.torrents.recheck.all()
qbt_client.torrents.resume.all()
```

Once you have a torrent, there's also a litany of interactions.
```python
hash = torrent.info.hash  # as well the rest of the properties from torrents/info endpoint
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
search_job = qbt_client.search.start(pattern='Ubuntu', categories='all', plugins='all')
while (search_job.status()[0].status != 'Stopped'):
  time.sleep(.1)
print(search_job.results())
search_job.delete()
```

Interaction Layer Notes
-----------------------
* All endpoints are available with and without the endpoint's namespace attached.
  * So, `qbt_client.torrents.torrents_resume()` and `qbt_client.torrents.resume()` are the same.
  * As mentioned in direct API access `qbt_client.app.web_api_version` and `qbt_client.app.webapiVersion` are the same.
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
To see the exceptions an endpoint can raise, use `help(qbt_client.<namespace>_<method>)`.

For example:
```
>>> import qbittorrentapi
>>> help(qbittorrentapi.Client.torrents_add)

Help on function torrents_add in module qbittorrentapi.torrents:

torrents_add(self, urls=None, torrent_files=None, save_path=None, cookie=None, category=None, is_skip_checking=None, is_paused=None, is_root_folder=None, rename=None, upload_limit=None, download_limit=None, use_auto_torrent_management=None, is_sequential_download=None, is_first_last_piece_priority=None, **kwargs)
    Add one or more torrents by URLs and/or torrent files.
    
    Exceptions:
        UnsupportedMediaType415Error if file is not a valid torrent file
        TorrentFileNotFoundError if a torrent file doesn't exist
        TorrentFilePermissionError if read permission is denied to torrent file
    
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
    :param download_limit: download limit in bytes/second
    :param use_auto_torrent_management: True or False to use automatic torrent management
    :param is_sequential_download: True or False for sequential download
    :param is_first_last_piece_priority: True or False for first and last piece download priority
    :return: "Ok." for success and ""Fails." for failure
```


```python
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
```
