import os
from dotenv import load_dotenv


load_dotenv()


POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
POSTGRES_IP = os.environ.get('POSTGRES_IP')
POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT'))
POSTGRES_DB = os.environ.get('POSTGRES_DB')

API_PORT = int(os.environ.get('API_PORT'))
