import asyncio
import config
import argparse
import json
import re
import time

server_id = ""
VALID_REQUESTS = ['IAMAT', 'WHATSAT']
'''
locations format:
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

def iamat_handler(parsed_message):
  location = {}
  client = parsed_message[1]
  raw_coord = parsed_message[2]
  time = parsed_message[3]
  if not time.replace('.', '', 1).isdigit():
    # Log Error
    return None

  coord = location_parser(raw_coord)
  if coord is not None:
    location['latitude'] = coord['latitude']
    location['longitude'] = coord['longitude']
  else:
    # Log Error
    return None

  location['name'] = client
  location['time'] = time

  locations[client] = location

  # [TODO] IAMAT RESPONSE
  client_time = float(time)
  server_time = time.time()
  time_difference = server_time - client_time
    
  return True

def request_parser(message):
  parsed_message = message.split()

  if (len(parsed_message) == 4):
    request = parsed_message[0]
    if (request not in VALID_REQUESTS):
      # Log Error
      return None
    elif (request == 'IAMAT'):
      return iamat_handler(parsed_message)
    elif (request == 'WHATSAT'):
      return "WHATSAT"
  else:
    # Log error
    return None


async def request_handler(reader, writer):
  data = await reader.read(100)
  message = data.decode()
  addr = writer.get_extra_info('peername')
  print("Received %r from %r" % (message, addr))

  server_response = request_parser(message)
  if server_response is not None:
    success_message = "Successfully updated locations: {}".format(json.dumps(locations))
    print(success_message)
    writer.write(str.encode(success_message))
    
  else:
    failure_message = "(?) {}".format(message)
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
