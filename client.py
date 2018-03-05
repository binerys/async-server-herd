import asyncio
import config

async def tcp_echo_client(message, loop):
  reader, writer = await asyncio.open_connection(config.load('LOCAL', 'HOST'),
                                                 config.load('LOCAL', 'PORT'),
                                                 loop=loop)

  print('Send: %r' % message)
  writer.write(message.encode())

  data = await reader.read(100)
  print('Received: %r' % data.decode())

  print('Close the socket')
  writer.close()


message = 'Hello World!'
loop = asyncio.get_event_loop()
loop.run_until_complete(tcp_echo_client(message, loop))
loop.close()
