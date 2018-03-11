import asyncio
import aiohttp
from threading import Thread
import queue

"""
  fetch_request
  Wrapper function for async fetch function. The thread will run this function
  until complemetion

  :param loop: The event loop created for the thread
  :param url: The url for the request
  :param params: The paramaters for the request as a dictionary
  :param result: A queue to store the result of the request
  
  :returns: The result queue with the request data. If the request fails, None
            is returned
"""
def fetch_request(loop, url, params, result):
  async def fetch(url, params, result):
    async with aiohttp.ClientSession() as session:
      async with session.get(url, params=params) as resp:
        if (resp.status != 200):
          #[TODO] make this logged
          print('API Request failed with status {} {}'.format(resp.status, resp.reason))
          return None
        
        data = await resp.text()
        result.put(data)
  
  asyncio.set_event_loop(loop)
  loop.run_until_complete(fetch(url, params, result))
  loop.close()

def get_json(url, params):
  fetch_thread_loop = asyncio.new_event_loop()
  result = queue.Queue()
  fetch_thread = Thread(target=fetch_request, args=(fetch_thread_loop, url, params, result))
  fetch_thread.start()

  return result.get()
