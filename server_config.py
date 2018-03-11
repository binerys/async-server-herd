''' Server to Port Mappings '''
SERVER_MAPPINGS = {
  'Goloman': 8000,
  'Hands': 8001,
  'Holiday': 8002,
  'Welsh': 8003,
  'Wilkes': 8004
}

INVERSE_SERVER_MAPPINGS = {v: k for k, v in SERVER_MAPPINGS.items()}

SERVER_NETWORK = {
  'Goloman': ['Hands', 'Wilkes', 'Holiday'],
  'Hands': ['Goloman', 'Wilkes'],
  'Holiday': ['Goloman', 'Wilkes', 'Welsh'],
  'Welsh': ['Holiday'],
  'Wilkes': ['Goloman', 'Hands', 'Holiday']
}

SERVER_URL = 'localhost'
HOP_COUNT = 2

