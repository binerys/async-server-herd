import asyncio
import logging
import sys
import argparse

from proxy import ProxyClient
from proxy import SERVER_MAPPINGS

# Parse command-line argument
parser = argparse.ArgumentParser(description='Simple message-sending client')
parser.add_argument('server', metavar='S',
                    help='server to send message to',
                    choices=[*SERVER_MAPPINGS])
parser.add_argument('message', metavar='M', help='a message for the client to send')
args = parser.parse_args()

SERVER_ADDRESS = ('localhost', SERVER_MAPPINGS[args.server])
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s: %(message)s',
    stream=sys.stderr,
)
log = logging.getLogger('client.py')

event_loop = asyncio.get_event_loop()
client_completed = asyncio.Future()
message = args.message
factory_coroutine = event_loop.create_connection(
  lambda: ProxyClient(message, client_completed),
  *SERVER_ADDRESS,
)

log.debug('waiting for client to complete')
try:
  event_loop.run_until_complete(factory_coroutine)
  event_loop.run_until_complete(client_completed)
finally:
  log.debug('closing event loop')
  event_loop.close()
