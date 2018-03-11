''' Server to Port Mappings '''
SERVER_MAPPINGS = {
  'Goloman': 17920,
  'Hands': 17921,
  'Holiday': 17922,
  'Welsh': 17923,
  'Wilkes': 17924
}

INVERSE_SERVER_MAPPINGS = {v: k for k, v in SERVER_MAPPINGS.items()}

SERVER_NETWORK = {
  'Goloman': ['Hands', 'Wilkes', 'Holiday'],
  'Hands': ['Goloman', 'Wilkes'],
  'Holiday': ['Goloman', 'Wilkes', 'Welsh'],
  'Welsh': ['Holiday'],
  'Wilkes': ['Goloman', 'Hands', 'Holiday']
}

SERVER_URL = 'lnxsrv09.seas.ucla.edu'
HOP_COUNT = 2

