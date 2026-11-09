import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app


def setup_score(client: TestClient) -> tuple[dict, dict, dict]:
    login = client.post('/api/v1/admin/login', json={'username': 'admin', 'password': 'admin123'})
    assert login.status_code == 200
    headers = {'Authorization': f"Bearer {login.json()['access_token']}"}
    activity = client.get('/api/v1/admin/config', headers=headers).json()
    code = uuid4().hex[:12]
    entrant = {'name': '回归选手', 'phone': f'137{int(code, 16) % 100_000_000:08d}', 'number_plate': f'PG-{code}'}
    registration = client.post('/api/v1/admin/registrations', json=entrant, headers=headers)
    assert registration.status_code == 201, registration.text
    row = registration.json()
    hidden_bonus = next(item for item in activity['score_items'] if item['code'] == 'hidden_bonus')
    submission = {
        'activity_id': activity['id'], 'registration_id': row['id'], 'operation_id': str(uuid4()),
        'expected_version': row['score_version'], 'rules_version': activity['rules_version'],
        'items': [{'score_item_id': hidden_bonus['id'], 'quantity': 1}],
    }
    return headers, entrant, submission


def test_retry_keeps_original_receipt_and_rejects_stale_writes() -> None:
    with TestClient(app) as client:
        headers, entrant, draft = setup_score(client)
        url = '/api/v1/admin/score-submissions'
        registration_id = draft['registration_id']
        receipt_url = f"{url}/{registration_id}/{draft['operation_id']}"
        assert client.get(receipt_url).status_code == 401
        assert client.get(receipt_url, headers=headers).json() == {'receipt': None}
        first = client.post(url, json=draft, headers=headers)
        assert first.status_code == 200, first.text
        original = first.json()
        assert client.get(receipt_url, headers=headers).json() == {'receipt': original}

        stale = {**draft, 'operation_id': str(uuid4())}
        assert client.post(url, json=stale, headers=headers).status_code == 409
        modified = [{**draft['items'][0], 'quantity': 2}]
        assert client.post(url, json={**draft, 'items': modified}, headers=headers).status_code == 409
        refreshed = {**stale, 'expected_version': original['version'], 'items': modified}
        assert client.post(url, json={**refreshed, 'rules_version': '0' * 64}, headers=headers).status_code == 409
        assert client.post(url, json={**refreshed, 'activity_id': -1}, headers=headers).status_code == 409
        second = client.post(url, json=refreshed, headers=headers)
        assert second.status_code == 200, second.text
        assert second.json()['version'] != original['version']
        assert client.post(url, json=draft, headers=headers).json() == original
        current = client.get(f'/api/v1/admin/registrations/{registration_id}', headers=headers).json()
        assert current['score_version'] == second.json()['version']
        assert current['score'] == second.json()['total_score']
        duplicate = client.post('/api/v1/admin/registrations', json=entrant, headers=headers)
        assert duplicate.json() == current
        conflict = client.post('/api/v1/admin/registrations', json={**entrant, 'name': '另一个人'}, headers=headers)
        assert conflict.status_code == 409


def test_concurrent_guarded_submissions_on_postgresql() -> None:
    if not get_settings().database_url.startswith('postgresql'):
        pytest.skip('并发事务在 PostgreSQL 上验证')

    async def submit_simultaneously(headers: dict, draft: dict) -> None:
        url = '/api/v1/admin/score-submissions'
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://local-test', headers=headers) as client:
            competing = {**draft, 'operation_id': str(uuid4()), 'items': [{**draft['items'][0], 'quantity': 2}]}
            responses = await asyncio.gather(client.post(url, json=draft), client.post(url, json=competing))
            assert sorted(response.status_code for response in responses) == [200, 409]
            saved = draft if responses[0].status_code == 200 else competing
            receipt = next(response.json() for response in responses if response.status_code == 200)
            replays = await asyncio.gather(*[client.post(url, json=saved) for _ in range(4)])
            assert all(response.status_code == 200 and response.json() == receipt for response in replays)

    with TestClient(app) as client:
        headers, _, draft = setup_score(client)
        client.portal.call(submit_simultaneously, headers, draft)
