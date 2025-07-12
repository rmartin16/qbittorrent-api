Introduction
============

.. |github ci| image:: https://img.shields.io/github/checks-status/rmartin16/qbittorrent-api/main?style=flat-square
   :target: https://github.com/rmartin16/qbittorrent-api/actions?query=branch%3Amain
.. |codecov| image:: https://img.shields.io/codecov/c/gh/rmartin16/qbittorrent-api/main?style=flat-square
   :target: https://app.codecov.io/gh/rmartin16/qbittorrent-api

.. |pypi| image:: https://img.shields.io/pypi/v/qbittorrent-api?style=flat-square
   :target: https://pypi.org/project/qbittorrent-api/
.. |pypi versions| image:: https://img.shields.io/pypi/pyversions/qbittorrent-api?style=flat-square
   :target: https://pypi.org/project/qbittorrent-api/
.. |pypi downloads| image:: https://img.shields.io/pypi/dw/qbittorrent-api?color=blue&style=flat-square
   :target: https://pypi.org/project/qbittorrent-api/

|github ci| |codecov|

|pypi| |pypi versions| |pypi downloads|

Python client implementation for qBittorrent Web API.

Currently supports qBittorrent `v5.1.2 <https://github.com/qbittorrent/qBittorrent/releases/tag/release-5.1.2>`_ (Web API v2.11.4) released on Jul 2, 2025.

Features
--------
- The entire qBittorrent `Web API <https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)>`_ is implemented.
- qBittorrent version checking for an endpoint's existence/features is automatically handled.
- If the authentication cookie expires, a new one is automatically requested in line with any API call.

Installation
------------
* Install via pip from `PyPI <https://pypi.org/project/qbittorrent-api/>`_:

.. code:: console

    python -m pip install qbittorrent-api

* Install a specific release (e.g. ``v2024.3.60``):

.. code:: console

    python -m pip install qbittorrent-api==2024.3.60

* Install direct from ``main``:

.. code:: console

    pip install git+https://github.com/rmartin16/qbittorrent-api.git@main#egg=qbittorrent-api

* Enable WebUI in qBittorrent: Tools -> Preferences -> Web UI
* If the Web API will be exposed to the Internet, follow the `recommendations <https://github.com/qbittorrent/qBittorrent/wiki/Linux-WebUI-HTTPS-with-Let's-Encrypt-certificates-and-NGINX-SSL-reverse-proxy>`_.

Getting Started
---------------
.. code:: python

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

Usage
-----
First, the Web API endpoints are organized in to eight namespaces.

* Authentication (``auth``)
* Application (``app``)
* Log (``log``)
* Sync (``sync``)
* Transfer (``transfer``)
* Torrent Management (``torrents``)
* RSS (``rss``)
* Search (``search``)

Second, this client has two modes of interaction with the qBittorrent Web API.

Each Web API endpoint is implemented one-to-one as a method of the instantiated client.

.. code:: python

    import qbittorrentapi
    qbt_client = qbittorrentapi.Client(host='localhost:8080', username='admin', password='adminadmin')
    qbt_client.app_version()
    qbt_client.rss_rules()
    qbt_client.torrents_info()
    qbt_client.torrents_resume(torrent_hashes='...')
    # and so on

However, a more robust interface to the endpoints is available via each namespace. This
is intended to provide a more seamless and intuitive interface to the Web API.

.. code:: python

    import qbittorrentapi
    qbt_client = qbittorrentapi.Client(host='localhost:8080', username='admin', password='adminadmin')
    # changing a preference
    is_dht_enabled = qbt_client.app.preferences.dht
    qbt_client.app.preferences = dict(dht=not is_dht_enabled)
    # stopping all torrents
    qbt_client.torrents.stop.all()
    # retrieve different views of the log
    qbt_client.log.main.warning()
    qbt_client.log.main.normal()

Finally, some of the objects returned by the client support methods of their own. This is
most pronounced for torrents themselves.

.. code:: python

    import qbittorrentapi
    qbt_client = qbittorrentapi.Client(host='localhost:8080', username='admin', password='adminadmin')

    for torrent in qbt_client.torrents.info.active():
        torrent.set_location(location='/home/user/torrents/')
        torrent.reannounce()
        torrent.upload_limit = -1
