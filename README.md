qBittorrent Web API Client
================================
[![PyPI](https://img.shields.io/pypi/v/qbittorrent-api)](https://pypi.org/project/qbittorrent-api/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/qbittorrent-api) [![Travis (.org) branch](https://img.shields.io/travis/rmartin16/qbittorrent-api/master)](https://travis-ci.org/github/rmartin16/qbittorrent-api) [![Codecov branch](https://img.shields.io/codecov/c/gh/rmartin16/qbittorrent-api/master)](https://codecov.io/gh/rmartin16/qbittorrent-api) [![Coverity Scan](https://img.shields.io/coverity/scan/21227)](https://scan.coverity.com/projects/rmartin16-qbittorrent-api) ![PyPI - Implementation](https://img.shields.io/pypi/implementation/qbittorrent-api)

Python client implementation for qBittorrent Web API. Supports qBittorrent v4.1.0+ (i.e. Web API v2.0+).

Currently supports up to qBittorrent [v4.2.5](https://github.com/qbittorrent/qBittorrent/releases/tag/release-4.2.5) (Web API v2.5.1) released on April 24, 2020.
  
The full qBittorrent Web API specification is documented on their [wiki](https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation).

[Find the full documentation for this client on RTD.](https://qbittorrent-api.readthedocs.io/)

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
* Ensure urllib3, requests, and attrdict are installed. (These are installed automatically using the methods above.)
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
