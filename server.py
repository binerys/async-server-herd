import logging
import sys
import argparse
import asyncio

from proxy_server import ProxyServer
from server_config import SERVER_MAPPINGS
from server_config import SERVER_URL

# Obtain server id from command-line
parser = argparse.ArgumentParser(description='Simple message-receiving server')
parser.add_argument('id', metavar='I', help='Server id', choices=[*SERVER_MAPPINGS])
args = parser.parse_args()

'''Logging Configuration'''
logging.basicConfig(
  level=logging.DEBUG,
  format='%(asctime)-15s - %(name)s: %(message)s',
  filename='{}.log'.format(args.id),
)
log = logging.getLogger('server.py')

''' Setup Server '''
SERVER_ADDRESS = (SERVER_URL, SERVER_MAPPINGS[args.id])
event_loop = asyncio.get_event_loop()
server_factory = event_loop.create_server(lambda: ProxyServer(args.id, event_loop), *SERVER_ADDRESS)
server = event_loop.run_until_complete(server_factory)
log.debug('starting up on {} port {}'.format(*SERVER_ADDRESS))

try:
  event_loop.run_forever()
except KeyboardInterrupt:
  pass

log.debug('closing server')
server.close()
event_loop.run_until_complete(server.wait_closed())
log.debug('closing event loop')
event_loop.close()
