from __future__ import annotations
import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = Path(os.getenv('CE108_DB_PATH', str(DATA_DIR / 'ce108.db')))
APP_SECRET = os.getenv('CE108_APP_SECRET', 'change-me-in-production')
TOKEN_TTL_SECONDS = int(os.getenv('CE108_TOKEN_TTL_SECONDS', '43200'))
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LIFF_ID = os.getenv('LIFF_ID', '')
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', 'http://localhost:8000')
