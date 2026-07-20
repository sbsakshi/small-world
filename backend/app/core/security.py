import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_session_token() -> str:
    # Opaque token; the session row (not the token) carries identity + expiry,
    # so sessions are revocable server-side (decision: cookie sessions, not JWT).
    return secrets.token_urlsafe(32)
