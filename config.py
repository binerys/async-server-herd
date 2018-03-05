import configparser

def load(domain, key):
  config = configparser.ConfigParser()
  config.read('config.ini')
  return config[domain][key]


