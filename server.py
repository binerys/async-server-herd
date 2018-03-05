import asyncio
import config
import argparse

async def request_handler(reader, writer):
  data = await reader.read(100)
  message = data.decode()
  addr = writer.get_extra_info('peername')
  print("Received %r from %r" % (message, addr))

  print("Send: %r" % message)
  writer.write(data)
  await writer.drain()

  print("Close the client socket")
  writer.close()

loop = asyncio.get_event_loop()
coro = asyncio.start_server(request_handler,
                            config.load('LOCAL', 'HOST'),
                            config.load('LOCAL', 'PORT'),
                            loop=loop)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
parser = argparse.ArgumentParser(description='Simple message-receiving server')
parser.add_argument('name', metavar='N', help='Server name/id')
args = parser.parse_args()

server_id = args.name
print('Serving on {}'.format(server_id))

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
