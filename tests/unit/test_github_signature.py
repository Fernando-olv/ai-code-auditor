import hashlib
import hmac

from app.services.webhook_service import verify_github_signature


def _signature_256(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_github_signature_accepts_valid_signature() -> None:
    body = b'{"hello":"world"}'
    secret = "test_secret"
    assert verify_github_signature(body, _signature_256(body, secret), secret) is True


def test_verify_github_signature_rejects_invalid_signature() -> None:
    body = b"{}"
    secret = "test_secret"
    assert verify_github_signature(body, "sha256=deadbeef", secret) is False


def test_verify_github_signature_rejects_missing_or_bad_header() -> None:
    body = b"{}"
    secret = "test_secret"
    assert verify_github_signature(body, "", secret) is False
    assert verify_github_signature(body, "sha1=abc", secret) is False


def test_verify_github_signature_rejects_empty_secret() -> None:
    body = b"{}"
    assert verify_github_signature(body, "sha256=abc", "") is False
