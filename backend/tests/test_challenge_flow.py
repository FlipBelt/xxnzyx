from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register_participant(client: TestClient, suffix: str) -> dict[str, object]:
    phone = f"139{int(suffix, 16) % 100_000_000:08d}"
    response = client.post(
        "/api/v1/registrations",
        json={
            "activity_slug": "flipbelt-40s-demo",
            "channel": "h5",
            "external_id": phone,
            "name": f"测试用户{suffix[:2]}",
            "phone": phone,
            "number_plate": f"T{suffix[:6].upper()}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_registration_score_rank_and_draw_flow() -> None:
    suffix_one = uuid4().hex
    suffix_two = uuid4().hex
    with TestClient(app) as client:
        activity_response = client.get("/api/v1/activity/current")
        assert activity_response.status_code == 200
        activity = activity_response.json()
        assert activity["challenge_duration_seconds"] == 40
        assert len(activity["score_items"]) == 8
        group_qr = next(item for item in activity["media_assets"] if item["kind"] == "group_qr")
        assert group_qr["url"] == "/assets/测试群二维码.jpg"

        participant_one = register_participant(client, suffix_one)
        participant_two = register_participant(client, suffix_two)
        participant_token = participant_one["access_token"]

        me_response = client.get(
            "/api/v1/me", headers={"Authorization": f"Bearer {participant_token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["status"] == "registered"

        admin_response = client.post(
            "/api/v1/admin/login", json={"username": "admin", "password": "admin123"}
        )
        assert admin_response.status_code == 200, admin_response.text
        admin_headers = {"Authorization": f"Bearer {admin_response.json()['access_token']}"}

        score_item_ids = {item["code"]: item["id"] for item in activity["score_items"]}
        full_score_items = [
            {"score_item_id": score_item_ids["hidden_bonus"], "quantity": 1},
            {"score_item_id": score_item_ids["light_clothing"], "quantity": 2},
            {"score_item_id": score_item_ids["trekking_pole"], "quantity": 1},
            {"score_item_id": score_item_ids["water_bottle"], "quantity": 1},
            {"score_item_id": score_item_ids["earphones"], "quantity": 1},
            {"score_item_id": score_item_ids["phone_model"], "quantity": 1},
            {"score_item_id": score_item_ids["energy_gel"], "quantity": 20},
            {"score_item_id": score_item_ids["salt_pills"], "quantity": 20},
        ]
        lower_score_items = [
            {"score_item_id": score_item_ids["hidden_bonus"], "quantity": 0},
            {"score_item_id": score_item_ids["light_clothing"], "quantity": 1},
            {"score_item_id": score_item_ids["trekking_pole"], "quantity": 1},
            {"score_item_id": score_item_ids["water_bottle"], "quantity": 1},
            {"score_item_id": score_item_ids["earphones"], "quantity": 1},
            {"score_item_id": score_item_ids["phone_model"], "quantity": 1},
            {"score_item_id": score_item_ids["energy_gel"], "quantity": 10},
            {"score_item_id": score_item_ids["salt_pills"], "quantity": 10},
        ]

        first_score_response = client.post(
            "/api/v1/admin/scores",
            headers=admin_headers,
            json={"registration_id": participant_one["registration_id"], "items": full_score_items},
        )
        assert first_score_response.status_code == 201, first_score_response.text
        assert first_score_response.json()["total_score"] == 95
        assert first_score_response.json()["reward"]["title"] == "能装王者"

        updated_score_items = [
            {**item, "quantity": 0} if item["score_item_id"] == score_item_ids["hidden_bonus"] else item
            for item in full_score_items
        ]
        update_score_response = client.post(
            "/api/v1/admin/scores",
            headers=admin_headers,
            json={"registration_id": participant_one["registration_id"], "items": updated_score_items},
        )
        assert update_score_response.status_code == 201, update_score_response.text
        assert update_score_response.json()["total_score"] == 89

        registrations_response = client.get("/api/v1/admin/registrations", headers=admin_headers)
        assert registrations_response.status_code == 200, registrations_response.text
        scored_registration = next(
            item for item in registrations_response.json()["items"]
            if item["id"] == participant_one["registration_id"]
        )
        assert sum(detail["quantity"] for detail in scored_registration["score_details"]) == 46

        second_score_response = client.post(
            "/api/v1/admin/scores",
            headers=admin_headers,
            json={"registration_id": participant_two["registration_id"], "items": lower_score_items},
        )
        assert second_score_response.status_code == 201, second_score_response.text
        assert second_score_response.json()["total_score"] == 53

        leaderboard_response = client.get("/api/v1/leaderboard")
        assert leaderboard_response.status_code == 200
        entries = leaderboard_response.json()["entries"]
        assert entries[0]["score"] >= entries[1]["score"]

        me_scored_response = client.get(
            "/api/v1/me", headers={"Authorization": f"Bearer {participant_token}"}
        )
        assert me_scored_response.status_code == 200
        me_scored = me_scored_response.json()
        assert me_scored["score"] == 89
        assert me_scored["draw_qualified"] is True
        assert me_scored["rank"] == me_scored["official_rank"]
        assert me_scored["display_rank"] is None
        assert me_scored["display_title"] == "能装王者"

        draw_response = client.post("/api/v1/admin/draw", headers=admin_headers)
        assert draw_response.status_code == 200, draw_response.text
        assert len(draw_response.json()["results"]) == 2
