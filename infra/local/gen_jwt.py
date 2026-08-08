"""PostgREST용 JWT 발급 (HS256, 표준 라이브러리만 사용).

사용: python3 gen_jwt.py <secret> <role>   # role: anon | service_role
"""
import base64
import hashlib
import hmac
import json
import sys
import time


def b64(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def main() -> None:
    secret, role = sys.argv[1], sys.argv[2]
    now = int(time.time())
    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64(json.dumps({
        "role": role, "iss": "ijari-local",
        "iat": now, "exp": now + 10 * 365 * 86400,
    }).encode())
    sig = b64(hmac.new(secret.encode(), header + b"." + payload, hashlib.sha256).digest())
    print((header + b"." + payload + b"." + sig).decode())


if __name__ == "__main__":
    main()
