import asyncio
import logging
import json
import re
import time

''' Server to Port Mappings '''
SERVER_MAPPINGS = {
  'Goloman': 8000,
  'Hands': 8001,
  'Holiday': 8002,
  'Welsh': 8003,
  'Wilkes': 8004
}

''' Valid Requests '''
VALID_REQUESTS = ['IAMAT', 'WHATSAT']

'''
Protocol subclass for async server in proxy herd
'''
class ProxyServer(asyncio.Protocol):
  locations = {}

  def __init__(self, id):
    self.id = id
    '''
    locations format:
    {
      "Client_Name": {
        "name": "Client_Name",
        "coordinates": "...",
        "latitude": "...",
        "longitude: "...",
        "time": "...
      }
    }
    '''

  def location_parser(self, raw_coords):
    LAT_LONG_RE = r'((?:\+{1}|-{1})[0-9]{1,3}(?:\.[0-9]{1,10})?)'
    matches = re.findall(LAT_LONG_RE, raw_coords)

    if (len(matches) == 2):
      latitude = matches[0]
      longitude = matches[1]
    else:
      return None

    return {'latitude': latitude, 'longitude': longitude}

  """
  create_AT_response

  :param client_name: The name of the client as a string. Assumes client exists
                      in locations dict
  
  :returns: A response string
  """
  def create_AT_response(self, client_name):
    client = self.locations[client_name]
    client_name = client['name']
    client_time = client['time']
    client_coordinates = client['coordinates']

    # Calculate time difference
    client_time = float(client_time)
    server_time = time.time()
    difference = server_time - client_time
    if (difference > 0):
      time_difference = '+{}'.format(str(difference))
    else:
      time_difference = str(difference)
    
    response = 'AT {server} {difference} {client} {coordinates} {time}'.format(
      server=self.id,
      difference=time_difference,
      client=client_name,
      coordinates=client_coordinates,
      time=client_time
    )

    return response

    
  def iamat_handler(self, request):
    parsed_request = request.split()
    if (len(parsed_request) != 4):
      self.log.debug('Invalid IAMAT request: {}'.format(parsed_request))
      return None

    location = {}
    client = parsed_request[1]
    raw_coord = parsed_request[2]
    client_time = parsed_request[3]
    if not client_time.replace('.', '', 1).isdigit():
      self.log.debug('{} is not a valid time'.format(client_time))
      return None

    coord = self.location_parser(raw_coord)
    if coord is not None:
      location['latitude'] = coord['latitude']
      location['longitude'] = coord['longitude']
    else:
      self.log.debug('{} is not a proper coordinate'.format(raw_coord))
      return None

    location['name'] = client
    location['coordinates'] = raw_coord
    location['time'] = client_time

    self.locations[client] = location
    self.log.debug('Updated locations: {}'.format(json.dumps(self.locations)))

    # [TODO] Propagate received location to other servers

    # Set response to client
    response = self.create_AT_response(client)
    return response

  def whatsat_handler(self, request):
    parsed_request = request.split()
    if (len(parsed_request) != 4):
      self.log.debug('Invalid WHATSAT request: {}'.format(parsed_request))
      return None

    client_name = parsed_request[1]

    if (not parsed_request[2].isdigit() or not parsed_request[3].isdigit()):
      self.log.debug('Radius/Information amount must be a valid number')
      return None

    radius = int(parsed_request[2])
    info_amt = int(parsed_request[3])

    if (radius > 50):
      self.log.debug('Radius {} must be less than 50km'.format(radius))
      return None
    
    if (info_amt > 20):
      self.log.debug('Information amount {} must be less than 20'.format(info_amt))
      return None

    # Check if we have the client's information
    if client_name in self.locations.keys():
      at_response = self.create_AT_response(client_name)
      places_response = '[PLACES TODO]'

      
      response = '{at_response}\n{places_response}'.format(
        at_response=at_response,
        places_response=places_response
      )
      return response
    else:
      # [TODO] Request information from other servers
      return '[server todo]'

    return True

  def request_handler(self, request):
    parsed_request = request.split()

    if (len(parsed_request) > 1):
      request_type = parsed_request[0]
      if (request_type not in VALID_REQUESTS):
        self.log.debug('{} is not a valid request'.format(request_type))
        return None
      elif (request_type == 'IAMAT'):
        return self.iamat_handler(request)
      elif (request_type == 'WHATSAT'):
        return self.whatsat_handler(request)
    else:
      self.log.debug('{} improperly formatted request'.format(request))
      return None

  def connection_made(self, transport):
    self.transport = transport
    self.addresss = transport.get_extra_info('peername')
    self.log = logging.getLogger(
      'ProxyServer-{}_{}_{}'.format(self.id, *self.addresss)
    )
    self.log.debug('connection accepted')
  
  def data_received(self, data):
    request = data.decode()
    server_response = self.request_handler(request)
    if server_response is not None:
      response = '{}'.format(server_response)
    else:
      response = '(?) {}'.format(request)
    
    self.log.debug(response)
    self.transport.write(response.encode())
    self.log.debug('sent {}'.format(response))
  
  def eof_received(self):
    self.log.debug('received EOF')
    if self.transport.can_write_eof():
      self.transport.write_eof()

  def connection_lost(self, error):
    if error:
      self.log.error('ERROR: {}'.format(error))
    else:
      self.log.debug('closing')
    super().connection_lost(error)

'''
Protocol subclass for async proxy client
'''
class ProxyClient(asyncio.Protocol):

  def __init__(self, message, future):
    super().__init__()
    self.message = message
    self.log = logging.getLogger('ProxyClient')
    self.f = future

  def connection_made(self, transport):
    self.transport = transport
    self.address = transport.get_extra_info('peername')
    self.log.debug(
        'connecting to {} port {}'.format(*self.address)
    )
    transport.write(self.message.encode())
    self.log.debug('sending {!r}'.format(self.message))

    if transport.can_write_eof():
        transport.write_eof()

  def data_received(self, data):
    self.log.debug('received:\n{}'.format(data.decode()))

  def eof_received(self):
    self.log.debug('received EOF')
    self.transport.close()
    if not self.f.done():
        self.f.set_result(True)

  def connection_lost(self, exc):
    self.log.debug('server closed connection')
    self.transport.close()
    if not self.f.done():
        self.f.set_result(True)
    super().connection_lost(exc)
