<div align="center">

qBittorrent Web API Client
==========================

Python client implementation for qBittorrent Web API

[![GitHub Workflow Status (branch)](https://img.shields.io/github/checks-status/rmartin16/qbittorrent-api/main?style=flat-square)](https://github.com/rmartin16/qbittorrent-api/actions?query=branch%3Amain) [![Codecov branch](https://img.shields.io/codecov/c/gh/rmartin16/qbittorrent-api/main?style=flat-square)](https://app.codecov.io/gh/rmartin16/qbittorrent-api) [![PyPI](https://img.shields.io/pypi/v/qbittorrent-api?style=flat-square)](https://pypi.org/project/qbittorrent-api/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/qbittorrent-api?style=flat-square)](https://pypi.org/project/qbittorrent-api/)

</div>

Currently supports qBittorrent [v4.6.7](https://github.com/qbittorrent/qBittorrent/releases/tag/release-4.6.7) (Web API v2.9.3) released on Sept 16, 2024.

User Guide and API Reference available on [Read the Docs](https://qbittorrent-api.readthedocs.io/).

Features
------------
* The entire qBittorrent [Web API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)) is implemented.
* qBittorrent version checking for an endpoint's existence/features is automatically handled.
* If the authentication cookie expires, a new one is automatically requested in line with any API call.

Installation
------------
Install via pip from [PyPI](https://pypi.org/project/qbittorrent-api/)
```bash
python -m pip install qbittorrent-api
```

Getting Started
---------------
```python
import qbittorrentapi

# instantiate a Client using the appropriate WebUI configuration
conn_info = dict(
    host="localhost",
    port=8080,
    username="admin",
    password="adminadmin",
)
qbt_client = qbittorrentapi.Client(**conn_info)

# the Client will automatically acquire/maintain a logged-in state
# in line with any request. therefore, this is not strictly necessary;
# however, you may want to test the provided login credentials.
try:
    qbt_client.auth_log_in()
except qbittorrentapi.LoginFailed as e:
    print(e)

# if the Client will not be long-lived or many Clients may be created
# in a relatively short amount of time, be sure to log out:
qbt_client.auth_log_out()

# or use a context manager:
with qbittorrentapi.Client(**conn_info) as qbt_client:
    if qbt_client.torrents_add(urls="...") != "Ok.":
        raise Exception("Failed to add torrent.")

# display qBittorrent info
print(f"qBittorrent: {qbt_client.app.version}")
print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
for k, v in qbt_client.app.build_info.items():
    print(f"{k}: {v}")

# retrieve and show all torrents
for torrent in qbt_client.torrents_info():
    print(f"{torrent.hash[-6:]}: {torrent.name} ({torrent.state})")

# stop all torrents
qbt_client.torrents.stop.all()
```
