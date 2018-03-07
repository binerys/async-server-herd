import asyncio
import logging

''' Server to Port Mappings '''
SERVER_MAPPINGS = {
  'Goloman': 8000,
  'Hands': 8001,
  'Holiday': 8002,
  'Welsh': 8003,
  'Wilkes': 8004
}

'''
Protocol subclass for async server in proxy herd
'''
class ProxyServer(asyncio.Protocol):
  def __init__(self, id):
    self.id = id

  def connection_made(self, transport):
    self.transport = transport
    self.addresss = transport.get_extra_info('peername')
    self.log = logging.getLogger(
      'ProxyServer-{}_{}_{}'.format(self.id, *self.addresss)
    )
    self.log.debug('connection accepted')
  
  def data_received(self, data):
    self.log.debug('received {!r}'.format(data))
    self.transport.write(data)
    self.log.debug('sent {!r}'.format(data))
  
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
