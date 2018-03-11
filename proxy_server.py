import asyncio
import logging
import json
import re
import time

from async_fetch import get_json
from proxy_client import ProxyClient

from server_config import SERVER_URL
from server_config import SERVER_NETWORK
from server_config import SERVER_MAPPINGS
from server_config import HOP_COUNT
from server_config import INVERSE_SERVER_MAPPINGS

''' Valid Requests '''
VALID_REQUESTS = ['IAMAT', 'WHATSAT', 'AT']

NEARBY_PLACES_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?'
API_KEY = 'AIzaSyCSWg4zx4MKKqJkTin0ff-1_ByYgFhrJ4s'

'''
Protocol subclass for async server in proxy herd
'''
class ProxyServer(asyncio.Protocol):
  """
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
  """
  locations = {}
  
  def __init__(self, id, loop):
    self.id = id
    self.loop = loop

  async def send_message(self, loop, future, server_id, message):
    try:
      await loop.create_connection(
        lambda: ProxyClient(message, future),
        host=SERVER_URL,
        port=SERVER_MAPPINGS[server_id]
      )
    except OSError:
      self.log.debug('[CONNECTION REFUSED] Failed to connect to {}'.format(server_id))

  def propagate_at_message(self, server_sender, client_name, client_location, client_time, hop_count=HOP_COUNT, exclude=None):
    server_network = list(SERVER_NETWORK[server_sender])
    message = 'AT {server_sender} {hop_count} {client_name} {client_location} {client_time}'.format(
      server_sender=server_sender,
      hop_count=hop_count,
      client_name=client_name,
      client_location=client_location,
      client_time=client_time
    )
    if exclude is not None:
      server_network.remove(exclude)

    loop = asyncio.get_event_loop()
    for recipient in server_network:
      self.log.debug('[IN PROGRESS] {}->{}: Sending message - {}'.format(server_sender, recipient, message))
      client_response_future = asyncio.Future()
      future = loop.create_task(self.send_message(loop, client_response_future, recipient, message))

  def get_nearby_places(self, latitude, longitude, radius, info_amt):
    params = {
      'key': API_KEY,
      'location': '{lat},{long}'.format(lat=latitude, long=longitude),
      'radius': radius*1000
    }
    data = get_json(NEARBY_PLACES_URL, params)
    if data is None:
      return None
    
    google_api = json.loads(data)
    modified_results = google_api['results'][0:info_amt]
    google_api['results'] = modified_results
    return json.dumps(google_api, indent=3)


  def location_parser(self, raw_coords):
    LAT_LONG_RE = r'((?:\+{1}|-{1})[0-9]{1,3}(?:\.[0-9]{1,10})?)'
    matches = re.findall(LAT_LONG_RE, raw_coords)

    if (len(matches) == 2):
      latitude = matches[0].replace('+', '', 1)
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
      self.log.debug('[ERROR] Invalid IAMAT request: {}'.format(parsed_request))
      return None

    location = {}
    client = parsed_request[1]
    raw_coord = parsed_request[2]
    client_time = parsed_request[3]
    if not client_time.replace('.', '', 1).isdigit():
      self.log.debug('[ERROR] {} is not a valid time'.format(client_time))
      return None

    coord = self.location_parser(raw_coord)
    if coord is not None:
      location['latitude'] = coord['latitude']
      location['longitude'] = coord['longitude']
    else:
      self.log.debug('[ERROR] {} is not a proper coordinate'.format(raw_coord))
      return None

    location['name'] = client
    location['coordinates'] = raw_coord
    location['time'] = client_time

    self.locations[client] = location
    self.log.debug('[LOCATIONS] Updated locations: {}'.format(json.dumps(self.locations)))

    self.log.debug('[PROPAGATE] {} Propagating fresh location update'.format(self.id))
    self.propagate_at_message(self.id, client, raw_coord, client_time)
    
    # Set response to client
    response = self.create_AT_response(client)
    return response

  def whatsat_handler(self, request):
    parsed_request = request.split()
    if (len(parsed_request) != 4):
      self.log.debug('[ERROR] Invalid WHATSAT request: {}'.format(parsed_request))
      return None

    client_name = parsed_request[1]

    if (not parsed_request[2].isdigit() or not parsed_request[3].isdigit()):
      self.log.debug('[ERROR] Radius/Information amount must be a valid number')
      return None

    radius = int(parsed_request[2])
    info_amt = int(parsed_request[3])

    if (radius > 50):
      self.log.debug('[ERROR] Radius {} must be less than 50km'.format(radius))
      return None
    
    if (info_amt > 20):
      self.log.debug('[ERROR] Information amount {} must be less than 20'.format(info_amt))
      return None

    # Check if we have the client's information
    if client_name in self.locations.keys():
      client = self.locations[client_name]
      at_response = self.create_AT_response(client_name)
      places_response = self.get_nearby_places(
        client['latitude'],
        client['longitude'],
        radius,
        info_amt
      )

      if places_response is None:
        self.log.debug('[GOOGLE PLACES API ERROR]')
        return None



      response = '{at_response}\n{places_response}\n\n'.format(
        at_response=at_response,
        places_response=places_response
      )

      return response
    else:
      self.log.debug('[ERROR] {} location not found'.format(client_name))
      return None

    return True
  
  def at_handler(self, request):
    
    parsed_request = request.split()
    if (len(parsed_request) != 6):
      self.log.debug('[ERROR] Invalid AT Request: {}'.format(parsed_request))
      return None
    

    location = {}
    server_sender = parsed_request[1]
    hop_count = int(parsed_request[2])
    client_name = parsed_request[3]
    raw_coord = parsed_request[4]
    client_time = parsed_request[5]

    self.log.debug('[PROPAGATION] Received location update from {}'.format(server_sender))

    coord = self.location_parser(raw_coord)
    if coord is not None:
      location['latitude'] = coord['latitude']
      location['longitude'] = coord['longitude']
      location['coordinates'] = raw_coord
    else:
      self.log.debug('[ERROR] {} is not a proper coordinate'.format(raw_coord))
      return None
    
    location['name'] = client_name
    location['time'] = client_time

    self.locations[client_name] = location
    self.log.debug('[LOCATION] Updated Server {} locations:\n{}'.format(self.id, json.dumps(self.locations)))
    
    # Propagate to the received information
    
    self.log.debug('[PROPAGATION] {} passing forward location update'.format(self.id))
    if hop_count != 0:
      self.propagate_at_message(self.id, client_name, raw_coord, client_time, hop_count=hop_count-1, exclude=server_sender)
    else:
      self.log.debug('[FLOODING COMPLETE] at Server {}'.format(self.id))
    
    return ''

  def request_handler(self, request):
    parsed_request = request.split()

    if (len(parsed_request) > 1):
      request_type = parsed_request[0]
      if (request_type not in VALID_REQUESTS):
        self.log.debug('[ERROR] {} is not a valid request'.format(request_type))
        return None
      elif (request_type == 'IAMAT'):
        return self.iamat_handler(request)
      elif (request_type == 'WHATSAT'):
        return self.whatsat_handler(request)
      elif (request_type == 'AT'):
        return self.at_handler(request)
    else:
      self.log.debug('[ERROR] {} improperly formatted request'.format(request))
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

  def connection_lost(self, error):
    if error:
      self.log.error('ERROR: {}'.format(error))
    else:
      self.log.debug('closing Server {}'.format(self.id))
    super().connection_lost(error)
