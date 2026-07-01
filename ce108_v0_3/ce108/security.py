from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time
from typing import Any
from .config import APP_SECRET, TOKEN_TTL_SECONDS
PBKDF2_ITERATIONS = 310_000

def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError('パスワードは8文字以上にしてください。')
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, PBKDF2_ITERATIONS)
    return 'pbkdf2_sha256${}${}${}'.format(PBKDF2_ITERATIONS, base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode())

def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split('$', 3)
        if algorithm != 'pbkdf2_sha256': return False
        salt = base64.urlsafe_b64decode(salt_b64)
        expected = base64.urlsafe_b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')

def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode((value + '=' * (-len(value) % 4)).encode())

def create_access_token(user_id: int, role: str) -> str:
    payload = {'sub': int(user_id), 'role': role, 'iat': int(time.time()), 'exp': int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64url(json.dumps(payload, separators=(',', ':')).encode())
    signature = _b64url(hmac.new(APP_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f'{body}.{signature}'

def decode_access_token(token: str) -> dict[str, Any]:
    try:
        body, signature = token.split('.', 1)
        expected = _b64url(hmac.new(APP_SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): raise ValueError
        payload = json.loads(_b64url_decode(body))
        if int(payload['exp']) < int(time.time()): raise ValueError
        return payload
    except Exception as exc:
        raise ValueError('無効なアクセストークンです。') from exc

def verify_line_signature(raw_body: bytes, signature: str, channel_secret: str) -> bool:
    if not channel_secret or not signature: return False
    expected = base64.b64encode(hmac.new(channel_secret.encode(), raw_body, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(expected, signature)
