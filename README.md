qBittorrent Web API v2 Client
=============================
Python client implementation for qBittorrent Web API.

qBittorrent v4.1.0 and later is supported.

qBittorrent Web API specification: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation

Installation
------------

*qbittorrent-api* is available on the Python Package Index(PyPI).

https://pypi.org/project/qbittorrent-api/

You can install *qbittorrent-api* using one of the following techniques:

- Use pip: :code:`pip install qbittorrent-api`
- Download the .zip or .tar.gz file from PyPI and install
- Download the source from Github and install

https://github.com/rmartin16/qbittorrent-api

Be sure to also install requests and attrdict.

Ensure that the WebUI is enabled in qBittorrent: Tools -> Preferences -> Web UI

Getting Started
---------------

```python
if (isAwesome){
  return true
}
```

Change Log
----------
* Version 0.1.1
   * Complete implementation of each endpoint for qBittorrent Web API v2
* Version 0.1.4
   * Introduced the "interaction layer" for transparent interaction with the qBittorrent API.
