import asyncio
import logging

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
