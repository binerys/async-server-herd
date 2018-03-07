import asyncio
import config
import argparse
import json
import re

# Client locations
'''
{
  "Client_Name": {
    "name": "Client_Name",
    "latitude": "...",
    "longitude: "...",
    "time": "...
  }
}
'''
locations = {}

def location_parser(raw_coords):
  LAT_LONG_RE = r'((?:\+{1}|-{1})[0-9]{1,3}(?:\.[0-9]{1,10})?)'
  matches = re.findall(LAT_LONG_RE, raw_coords)

  if (len(matches) == 2):
    latitude = matches[0]
    longitude = matches[1]
  else:
    return None

  return {'latitude': latitude, 'longitude': longitude}


def request_parser(message):
  valid_requests = ['IAMAT', 'WHATSAT']
  location = {}
  parsed_message = message.split()

  if (len(parsed_message) == 4):
    request = parsed_message[0]
    if (request not in valid_requests):
      # Log Error
      return False

    client = parsed_message[1]
    raw_coord = parsed_message[2]
    time = parsed_message[3]
    if not time.replace('.', '', 1).isdigit():
      # Log Error
      return False

    coord = location_parser(raw_coord)
    if coord is not None:
      location['latitude'] = coord['latitude']
      location['longitude'] = coord['longitude']
    else:
      # Log Error
      return False

    location['name'] = client
    location['time'] = time

    locations[client] = location
    return True
  else:
    # Log error
    return False


async def request_handler(reader, writer):
  data = await reader.read(100)
  message = data.decode()
  addr = writer.get_extra_info('peername')
  print("Received %r from %r" % (message, addr))

  if (request_parser(message)):
    success_message = "Successfully updated locations: {}".format(json.dumps(locations))
    print(success_message)
    writer.write(str.encode(success_message))
    
  else:
    failure_message = "(?) Unsuccessfully parsed: {}".format(message)
    print(failure_message)
    writer.write(str.encode(failure_message))

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
