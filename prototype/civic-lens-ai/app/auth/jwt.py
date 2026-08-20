import json
import base64
import hmac
import hashlib
import time
from typing import Dict, Any, Optional
from app.config import settings

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64_decode(data_str: str) -> bytes:
    padding = '=' * (4 - len(data_str) % 4)
    return base64.urlsafe_b64decode((data_str + padding).encode('utf-8'))

def create_access_token(data: Dict[str, Any], expires_delta_minutes: Optional[int] = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    expire_minutes = expires_delta_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    exp = now + (expire_minutes * 60)
    
    payload = data.copy()
    payload.update({"iat": now, "exp": exp})
    
    header_b64 = _b64_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _b64_encode(json.dumps(payload).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(settings.JWT_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(settings.JWT_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = _b64_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        payload = json.loads(_b64_decode(payload_b64).decode('utf-8'))
        now = int(time.time())
        if "exp" in payload and payload["exp"] < now:
            return None
            
        return payload
    except Exception:
        return None
