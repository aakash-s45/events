# read .env file
import os
from dotenv import load_dotenv
from os import getenv

load_dotenv()

DEBUG = True
APP_NAME = getenv('APP_NAME')
APP_URL = getenv('APP_URL')
APP_VERSION = getenv('APP_VERSION')
APP_EMAIL = getenv('APP_EMAIL')
BASE_ROUTE = getenv('BASE_ROUTE')

# Authentication credentials
BASIC_AUTH_USER = getenv('BASIC_AUTH_USER')
BASIC_AUTH_PASS = getenv('BASIC_AUTH_PASS')
AUTH_TOKEN = getenv('AUTH_TOKEN')

# Kafka settings
KAFKA_BROKERS = getenv('KAFKA_BROKERS')

# DB config
DB_HOST = getenv('DB_HOST')
DB_PORT = getenv('DB_PORT')
DB_USER = getenv('DB_USER')
DB_PASS = getenv('DB_PASS')
DB_NAME = getenv('DB_NAME')

# API keys

MUSICBRAINZ_BASE_URL = getenv('MUSICBRAINZ_BASE_URL')
THE_LAST_FM_BASE_URL = getenv('THE_LAST_FM_BASE_URL')
COVERT_ART_ARCHIVE_BASE_URL = getenv('COVERT_ART_ARCHIVE_BASE_URL')
THE_MUSIC_DB_KEY = getenv('THE_MUSIC_DB_KEY')
LAST_FM_API_KEY = getenv('LAST_FM_API_KEY')

MB_RATE_LIMIT = int(getenv('MB_RATE_LIMIT', 2))
LFM_RATE_LIMIT = int(getenv('LFM_RATE_LIMIT', 2))