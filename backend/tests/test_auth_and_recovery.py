from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import AdminUser
from app.services.security import create_access_token, hash_password


def payload() -> dict[str, str]:
    suffix = uuid4().hex
    phone = f"138{int(suffix, 16) % 100_000_000:08d}"
    return {
        "activity_slug": "flipbelt-40s-demo", "channel": "h5", "external_id": phone,
        "name": "本地回归选手", "phone": phone, "number_plate": f"R-{suffix[:10]}",
    }


def admin_headers(client: TestClient) -> dict[str, str]:
    result = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"})
    assert result.status_code == 200
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


@pytest.mark.parametrize("path", ["/admin/me", "/admin/dashboard", "/admin/registrations", "/admin/config"])
def test_admin_always_requires_authentication(path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_AUTH_ENABLED", "false")
    with TestClient(app) as client:
        assert client.get(f"/api/v1{path}").status_code == 401
        assert client.get(f"/api/v1{path}", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_participant_token_cannot_access_admin() -> None:
    with TestClient(app) as client:
        result = client.post("/api/v1/registrations", json=payload()).json()
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        assert client.get("/api/v1/admin/dashboard", headers=headers).status_code == 403


def test_retry_and_manual_registration_recover_the_original_record() -> None:
    with TestClient(app) as client:
        data = payload()
        first = client.post("/api/v1/registrations", json=data)
        retry = client.post("/api/v1/registrations", json=data)
        assert first.status_code == retry.status_code == 201
        assert retry.json()["already_registered"] is True
        assert retry.json()["registration_id"] == first.json()["registration_id"]
        mismatch = client.post("/api/v1/registrations", json={**data, "name": "其他人"})
        assert mismatch.status_code == 409
        assert "access_token" not in mismatch.json()

        manual = payload()
        headers = admin_headers(client)
        created = client.post(
            "/api/v1/admin/registrations", headers=headers,
            json={key: manual[key] for key in ("name", "phone", "number_plate")},
        )
        assert created.status_code == 201, created.text
        recovered = client.post("/api/v1/registrations", json=manual)
        assert recovered.status_code == 201, recovered.text
        assert recovered.json()["registration_id"] == created.json()["id"]
        token = recovered.json()["access_token"]
        me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["registration_id"] == created.json()["id"]
        rows = client.get(f"/api/v1/admin/registrations?keyword={manual['phone']}", headers=headers)
        assert len(rows.json()["items"]) == 1


def test_recovery_requires_full_matching_details() -> None:
    with TestClient(app) as client:
        data = payload()
        original = client.post("/api/v1/registrations", json=data).json()
        phone_only = {"channel": "h5", "external_id": data["phone"]}
        assert client.post("/api/v1/participant/login", json=phone_only).status_code == 422
        login_data = {key: data[key] for key in ("channel", "external_id", "activity_slug", "name", "number_plate")}
        assert client.post("/api/v1/participant/login", json={**login_data, "number_plate": "wrong"}).status_code == 409
        resumed = client.post("/api/v1/participant/login", json=login_data)
        assert resumed.status_code == 200
        assert resumed.json()["registration_id"] == original["registration_id"]


def test_scorer_cannot_change_configuration_or_delete_scores() -> None:
    username = f"scorer-{uuid4().hex[:10]}"
    async def create_scorer() -> None:
        async with AsyncSessionLocal() as session:
            session.add(AdminUser(
                username=username, display_name="回归录分员", password_hash=hash_password("local-test-only"), role="scorer"
            ))
            await session.commit()
    with TestClient(app) as client:
        client.portal.call(create_scorer)
        login = client.post("/api/v1/admin/login", json={"username": username, "password": "local-test-only"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.get("/api/v1/admin/config", headers=headers).status_code == 200
        settings = client.get("/api/v1/activity/current").json()
        assert client.put("/api/v1/admin/config/activity", headers=headers, json=settings).status_code == 403
        assert client.delete("/api/v1/admin/scores", headers=headers).status_code == 403
        assert client.post("/api/v1/admin/draw", headers=headers).status_code == 403
        async def deactivate_scorer() -> None:
            async with AsyncSessionLocal() as session:
                admin = await session.scalar(select(AdminUser).where(AdminUser.username == username))
                assert admin is not None
                admin.is_active = False
                await session.commit()
        client.portal.call(deactivate_scorer)
        assert client.get("/api/v1/admin/config", headers=headers).status_code == 401


def test_production_requires_an_independent_signing_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production")
    with pytest.raises(ValidationError) as invalid:
        Settings(_env_file=None, app_env="production", jwt_secret="fixture-secret-too-short")
    assert "fixture-secret-too-short" not in str(invalid.value)
    Settings(_env_file=None, app_env="production", jwt_secret="synthetic-validation-value-32-characters")


def test_production_refuses_the_documented_development_password(monkeypatch: pytest.MonkeyPatch) -> None:
    with TestClient(app) as client:
        monkeypatch.setattr(get_settings(), "app_env", "production")
        response = client.post("/api/v1/admin/login", json={"username": "admin", "password": "admin123"})
        assert response.status_code == 401
        assert "access_token" not in response.json()


def test_invalid_and_expired_subjects_return_unauthorized() -> None:
    settings = get_settings()
    with TestClient(app) as client:
        for claims in [
            {"sub": "admin:not-an-id", "role": "admin", "exp": 4_000_000_000},
            {"sub": "admin:1", "role": "admin", "exp": 0},
        ]:
            token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
            assert client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
        assert client.get(
            "/api/v1/admin/me", headers={"Authorization": f"Bearer {create_access_token('participant:1', 'participant')}"}
        ).status_code == 403


def test_concurrent_retries_share_one_registration_on_postgresql() -> None:
    import asyncio

    from httpx import ASGITransport, AsyncClient

    if not get_settings().database_url.startswith("postgresql"):
        pytest.skip("并发事务在与生产一致的PostgreSQL上验证")

    async def simultaneous_requests(data: dict[str, str]) -> list[dict[str, object]]:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://local-test") as client:
            responses = await asyncio.gather(*[client.post("/api/v1/registrations", json=data) for _ in range(5)])
            assert all(response.status_code == 201 for response in responses), [response.status_code for response in responses]
            return [response.json() for response in responses]

    with TestClient(app) as client:
        data = payload()
        results = client.portal.call(simultaneous_requests, data)
        assert len({result["registration_id"] for result in results}) == 1
        rows = client.get(f"/api/v1/admin/registrations?keyword={data['phone']}", headers=admin_headers(client))
        assert len(rows.json()["items"]) == 1
