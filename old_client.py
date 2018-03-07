import asyncio
import config
import argparse

async def send_request(message, loop):
  reader, writer = await asyncio.open_connection(config.load('LOCAL', 'HOST'),
                                                 config.load('LOCAL', 'PORT'),
                                                 loop=loop)

  print('Send: %r' % message)
  writer.write(message.encode())

  data = await reader.read(100)
  print('Received: %r' % data.decode())

  print('Close the socket')
  writer.close()


parser = argparse.ArgumentParser(description='Simple message-sending client')
parser.add_argument('message', metavar='M', help='a message for the client to send')
args = parser.parse_args()

message = args.message
loop = asyncio.get_event_loop()
loop.run_until_complete(send_request(message, loop))
loop.close()
