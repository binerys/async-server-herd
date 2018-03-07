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
    location['time'] = client_time

    self.locations[client] = location
    self.log.debug('Updated locations: {}'.format(json.dumps(self.locations)))

    # [TODO] Propagate received location to other servers

    # Set response to client
    client_time = float(client_time)
    server_time = time.time()
    time_difference = server_time - client_time
    if (time_difference > 0):
      time_difference = '+{}'.format(str(time_difference))

    response = 'AT {server} {difference} {request}'.format(server=self.id,
                                                          difference=time_difference,
                                                          request=' '.join(parsed_request[1:]))
    return response

  def request_handler(self, request):
    parsed_request = request.split()
    self.log.debug('parsed_request: {}'.format(parsed_request))
    if (len(parsed_request) > 1):
      request_type = parsed_request[0]
      if (request_type not in VALID_REQUESTS):
        self.log.debug('{} is not a valid request'.format(request_type))
        return None
      elif (request_type == 'IAMAT'):
        return self.iamat_handler(request)
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
    self.log.debug('received {!r}'.format(data))

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
