"""Security and hardening tests for CareCast API v1 (Phase 4).

Acceptance tests covered:
- AT-33: Security headers present on responses
- AT-34: Forced server error returns generic JSON; no traceback, path or SQL
- AT-35: Exceeding rate limit returns 429
- AT-37: No Access-Control-Allow-* and no Set-Cookie in any response
- API DB Read-only guarantee: Write attempt fails
- Body size cap: POST body > 8 KB -> 413 payload_too_large
- Unknown field rejection: extra='forbid'
- Production docs disabled: /docs, /redoc, /openapi.json -> 404
"""

import sqlite3
import pytest
from fastapi.testclient import TestClient
from carecast.api.main import create_app
from carecast.db import connect_ro
from carecast.settings import Settings


class TestSecurityHeadersAT33:
    """AT-33: CSP, X-Content-Type-Options, Referrer-Policy, X-Frame-Options present on responses."""

    def test_security_headers_present(self):
        settings = Settings(env="dev", db_path="data/carecast.db", enable_docs=False)
        app = create_app(settings)
        client = TestClient(app)

        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

        headers = resp.headers
        assert "Content-Security-Policy" in headers
        csp = headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("Referrer-Policy") == "no-referrer"
        assert headers.get("X-Frame-Options") == "DENY"
        assert "geolocation=()" in headers.get("Permissions-Policy", "")
        assert "no-store" in headers.get("Cache-Control", "")
        assert "X-Request-ID" in headers

    def test_hsts_header_when_enabled(self):
        settings = Settings(env="dev", db_path="data/carecast.db", hsts=True)
        app = create_app(settings)
        client = TestClient(app)

        resp = client.get("/api/v1/health")
        assert "Strict-Transport-Security" in resp.headers


class TestNoCorsAndNoCookiesAT37:
    """AT-37: No Access-Control-Allow-* and no Set-Cookie in any response."""

    def test_no_cors_and_no_cookies(self):
        settings = Settings(env="dev", db_path="data/carecast.db")
        app = create_app(settings)
        client = TestClient(app)

        for path in ["/api/v1/health", "/api/v1/meta", "/api/v1/summary?disease=flu"]:
            resp = client.get(path)
            for header_name in resp.headers:
                assert not header_name.lower().startswith("access-control-allow-"), (
                    f"Found CORS header {header_name} in response"
                )
                assert header_name.lower() != "set-cookie", "Found Set-Cookie header in response"


class TestForcedServerErrorAT34:
    """AT-34: Forced server error returns generic JSON; no traceback, path or SQL."""

    def test_forced_error_envelope(self, monkeypatch):
        settings = Settings(env="dev", db_path="data/carecast.db")
        app = create_app(settings)

        # Force an unhandled exception inside a route handler
        from carecast.api import routes

        def mock_error(*args, **kwargs):
            raise RuntimeError("Database query failed: SELECT * FROM secret_path/secret_file.db")

        monkeypatch.setattr(routes, "get_db_data_as_of", mock_error)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/health")
        assert resp.status_code == 500

        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "internal_error"
        assert "request_id" in data["error"]

        # Ensure no traceback, internal path, or SQL leaked
        response_text = resp.text
        assert "secret_path" not in response_text
        assert "Traceback" not in response_text
        assert "SELECT *" not in response_text


class TestRateLimiterAT35:
    """AT-35: Exceeding the limit returns 429 with Retry-After header."""

    def test_rate_limit_exceeded(self):
        # Set small limit of 3 requests per minute
        settings = Settings(
            env="dev",
            db_path="data/carecast.db",
            rate_get_per_min=3,
            rate_post_per_min=2,
        )
        app = create_app(settings)
        client = TestClient(app)

        # First 3 should succeed
        for _ in range(3):
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200

        # 4th request must be rate limited
        resp4 = client.get("/api/v1/health")
        assert resp4.status_code == 429
        assert "Retry-After" in resp4.headers
        data = resp4.json()
        assert data["error"]["code"] == "rate_limited"

    def test_at_35_post_scenario_rate_limit(self):
        """AT-35: Repeated POST /api/v1/scenario triggers 429 when rate_post_per_min is exceeded."""
        settings = Settings(
            env="dev",
            db_path="data/carecast.db",
            rate_get_per_min=10,
            rate_post_per_min=2,
        )
        app = create_app(settings)
        client = TestClient(app)

        payload = {
            "disease": "flu",
            "jurisdiction": "US",
            "surge_pct": 0.0,
        }

        # First 2 POST requests succeed
        for _ in range(2):
            resp = client.post("/api/v1/scenario", json=payload)
            assert resp.status_code == 200

        # 3rd request (rate_post_per_min + 1) must trigger 429 rate_limited
        resp3 = client.post("/api/v1/scenario", json=payload)
        assert resp3.status_code == 429
        assert "Retry-After" in resp3.headers
        data = resp3.json()
        assert data["error"]["code"] == "rate_limited"



class TestBodySizeLimit:
    """Body size cap 8 KB: POST body > 8 KB -> 413 payload_too_large."""

    def test_large_body_returns_413(self):
        settings = Settings(env="dev", db_path="data/carecast.db")
        app = create_app(settings)
        client = TestClient(app)

        large_payload = {
            "disease": "flu",
            "jurisdiction": "US",
            "surge_pct": 20.0,
            "padding": "x" * 9000,
        }
        resp = client.post("/api/v1/scenario", json=large_payload)
        assert resp.status_code == 413
        data = resp.json()
        assert data["error"]["code"] == "payload_too_large"


class TestUnknownFieldsForbidden:
    """Pydantic extra='forbid' rejects unknown fields."""

    def test_extra_field_rejected(self):
        settings = Settings(env="dev", db_path="data/carecast.db")
        app = create_app(settings)
        client = TestClient(app)

        payload = {
            "disease": "flu",
            "jurisdiction": "US",
            "surge_pct": 20.0,
            "malicious_unknown_key": "some_value",
        }
        resp = client.post("/api/v1/scenario", json=payload)
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "validation_error"
        assert "malicious_unknown_key" in data["error"]["fields"]


class TestReadOnlyDBConnectionFailsWrites:
    """Test that the read-only connection used by the API strictly fails on any write attempt."""

    def test_write_attempt_raises_error(self):
        conn = connect_ro("data/carecast.db")
        with pytest.raises(sqlite3.OperationalError, match="(readonly|attempt to write)"):
            conn.execute("INSERT INTO diseases (code, label) VALUES ('test_err', 'Test')")
        conn.close()


class TestDocsDisabledInProd:
    """AT-36: In prod mode: /docs, /redoc, /openapi.json return 404."""

    def test_docs_404_in_prod(self):
        settings = Settings(env="prod", db_path="data/carecast.db", enable_docs=False)
        app = create_app(settings)
        client = TestClient(app)

        for doc_url in ["/docs", "/redoc", "/openapi.json"]:
            resp = client.get(doc_url)
            assert resp.status_code == 404
