from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.rate_limit import RateLimiter


class _Auth:
    def authenticate(self, _authorization=None):
        return {"sub": "personal"}


class _Client:
    async def search(self, _query):
        return []


def _settings():
    return Settings(
        mem0_api_key="test",
        memory_vault_id="vault_test",
        action_api_key="action-secret",
        change_token_secret="x" * 32,
        environment="production",
    )


def test_memory_responses_are_not_cacheable_and_have_security_headers():
    app = create_app(_settings(), mem0_client=_Client(), authenticator=_Auth())
    with TestClient(app) as client:
        response = client.post(
            "/v1/memories/search",
            json={"query": "safe"},
            headers={"Authorization": "Bearer test"},
        )
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_rate_limiter_is_bounded_per_subject_and_operation():
    limiter = RateLimiter(read_limit=1, write_limit=2, window=60)
    assert limiter.allow("personal", "read")
    assert not limiter.allow("personal", "read")
    assert limiter.allow("personal", "write")
    assert limiter.allow("personal", "write")
    assert not limiter.allow("personal", "write")
    assert limiter.allow("other", "read")
