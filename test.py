from time import time

# UPDATE ENVIRONMENT VARS FIRST
qb_address = 'http://localhost:8080'
username = 'admin'
password = 'adminadmin'

from qbittorrentapi import Client
qbapi_client = Client(host=qb_address, username=username, password=password, VERBOSE_RESPONSE_LOGGING=True)  #, SIMPLE_RESPONSES=True)

from qbittorrent import Client
pyqb_client = Client(qb_address)
pyqb_client.login(username, password)

import logging
# logging.getLogger('urllib3').setLevel(level=logging.DEBUG)
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] {%(name)s:%(lineno)d} %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info('qbittorrent-api timing')
print(f'Version: {qbapi_client.app_version(SIMPLE_RESPONSES=True)}')
exit()
print(f'Log: {qbapi_client.log.main()}')
_ = qbapi_client.torrents.info()
loop_start = time()
logger.info('Starting loop...')
for count, torrent in enumerate(qbapi_client.torrents.info()):
	torrent_start = time()
	logger.info('Torrent %d' % count)
	logger.info(' -> File count: %d' % len(qbapi_client.torrents_files(torrent['hash'], SIMPLE_RESPONSE=True)))
	logger.info(' -> Time: %.3f' % (time() - torrent_start))
	print(type(qbapi_client.torrents_piece_states(torrent['hash'])))
logger.info('Total time: %.3f' % (time() - loop_start))

logger.info('')
logger.info('python-qbittorrent timing')
_ = pyqb_client.torrents()
loop_start = time()
logger.info('Starting loop...')
for count, torrent in enumerate(pyqb_client.torrents()):
	torrent_start = time()
	logger.info('Torrent %d' % count)
	logger.info(' -> File count: %d' % len(pyqb_client.get_torrent_files(torrent["hash"])))
	logger.info(' -> Time: %.3f' % (time() - torrent_start))
logger.info('Total time: %.3f' % (time() - loop_start))

