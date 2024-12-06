Async Support
=============

``qbittorrent-api`` does not support Python's ``async/await`` functionality for
asynchronous programming. However, many use-cases for this client operate within an
existing asynchronous application. Therefore, in lieu of being able to await this
client's API calls to qBittorrent, it is still possible to call them without blocking.

Each ``asyncio`` Event Loop provides a ``ThreadPoolExecutor`` that can run blocking code
that could interfere with async applications. In Python 3.9, a simple interface was
introduced in ``asyncio`` to run synchronous code in this thread pool.

.. code:: python

    async def fetch_torrents() -> TorrentInfoList:
        return await asyncio.to_thread(qbt_client.torrents_info, category="uploaded")

In this example, you simply specify the method to call, ``torrents_info``, as the first
argument and follow it with the arguments for the method to run in the thread.

Below is a full example demonstrating this that can be run in the Python REPL:

.. code:: python

    import asyncio
    import qbittorrentapi

    qbt_client = qbittorrentapi.Client()

    async def fetch_qbt_info():
        return await asyncio.to_thread(qbt_client.app_build_info)

    print(asyncio.run(fetch_qbt_info()))
