qBittorrent Web API v2 Client
========
Python client implementation for qBittorrent Web API v2 first available in qBittorrent v4.1.

API Documentation: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation

Change Log
--------
* Version 0.1
   * Complete implementation of each endpoint for qBittorrent Web API v2
   
TO DO
--------
* Create automated test scripts
* Create interaction layer to allow for more fluid access to endpoints. That way, developers don't have to hit individual endpoints and can instead transparently interact with qBittorrent.

Installation
------------

*qbittorrent* is available on the Python Package Index(PyPI).

https://pypi.python.org/pypi/qbittorrentapi

You can install *qbittorrentapi* using one of the following techniques:

- Use pip: `pip install qbittorrentapi`
- Download the .zip or .tar.gz file from PyPI and install
- Download the source from Github and install

https://github.com/rmartin16/qbittorrent-api

Be sure to also install requests and attrdict.

Getting Started
--------

`>>>` `import qbittorrentapi`

`>>>` `client = qbittorrentapi.Client(host='http://localhost:8080', username='admin', password='adminadmin')`

`>>>` `print("qBittorrent Version: %s" % client.app_version())`

`>>>` `help(qbittorrentapi.Client)`