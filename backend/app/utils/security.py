"""Security-related helper functions shared across services."""

import hashlib


def hash_token(token: str) -> str:
    """Return a deterministic SHA-256 hex digest of a token.

    Refresh tokens are opaque, high-entropy JWTs, so a deterministic hash
    (rather than a salted bcrypt hash) is used to allow lookup by hash
    while never storing the raw token value.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
