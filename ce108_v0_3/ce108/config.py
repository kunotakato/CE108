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
NOTE_OCR_PROVIDER = os.getenv('NOTE_OCR_PROVIDER', 'disabled').strip().lower()
NOTE_OCR_MAX_BYTES = int(os.getenv('NOTE_OCR_MAX_BYTES', '10485760'))

def csv_env(name: str, default: str = '') -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]

LOCAL_CORS_ORIGINS = [
    'http://localhost:8501',
    'http://127.0.0.1:8501',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
DEPLOYED_CORS_ORIGINS = [
    'https://ce108-mobile.onrender.com',
]
CORS_ORIGINS = list(dict.fromkeys((csv_env('CE108_CORS_ORIGINS') or LOCAL_CORS_ORIGINS) + DEPLOYED_CORS_ORIGINS))
