from dotenv import load_dotenv
import os


load_dotenv('venv/.env')

GROUP_ID = os.environ.get('GROUP_ID')
GROUP_TOKEN = os.environ.get('GROUP_TOKEN')
API_VERSION = os.environ.get('API_VERSION')
