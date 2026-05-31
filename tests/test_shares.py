"""Shares CRUD: happy path, cross-org, duplicate, idempotent revoke."""
import pytest
from sqlalchemy import text


async def test_create_share_happy_path(client, auth_header, db_session):
    r = await client.post(
        "/reports/1/shares",
        json={"target_user_id": 2, "permission": "edit"},
        headers=auth_header(1),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["target_user_id"] == 2
    assert body["permission"] == "edit"
    assert body["granted_by_user_id"] == 1

    # DB has the row
    row = (await db_session.execute(
        text("SELECT permission FROM report_shares WHERE id = :id"),
        {"id": body["id"]},
    )).first()
    assert row[0] == "edit"


async def test_create_share_cross_org_rejected(client, auth_header):
    # user 4 is org 2; owner (user 1) is org 1 → 403
    r = await client.post(
        "/reports/1/shares",
        json={"target_user_id": 4, "permission": "view"},
        headers=auth_header(1),
    )
    assert r.status_code == 403


async def test_create_share_non_owner_rejected(client, auth_header):
    r = await client.post(
        "/reports/1/shares",
        json={"target_user_id": 3, "permission": "view"},
        headers=auth_header(2),  # user 2 is not the owner
    )
    assert r.status_code == 403


async def test_create_share_duplicate_returns_409(client, auth_header):
    payload = {"target_user_id": 2, "permission": "view"}
    r1 = await client.post("/reports/1/shares", json=payload, headers=auth_header(1))
    assert r1.status_code == 201
    r2 = await client.post("/reports/1/shares", json=payload, headers=auth_header(1))
    assert r2.status_code == 409


async def test_list_shares_owner_sees_active(client, auth_header):
    await client.post(
        "/reports/1/shares",
        json={"target_user_id": 2, "permission": "view"},
        headers=auth_header(1),
    )
    r = await client.get("/reports/1/shares", headers=auth_header(1))
    assert r.status_code == 200
    assert len(r.json()["shares"]) == 1


async def test_list_shares_non_owner_forbidden(client, auth_header):
    r = await client.get("/reports/1/shares", headers=auth_header(2))
    assert r.status_code == 403


async def test_delete_share_idempotent(client, auth_header, db_session):
    r = await client.post(
        "/reports/1/shares",
        json={"target_user_id": 2, "permission": "view"},
        headers=auth_header(1),
    )
    share_id = r.json()["id"]

    # First delete → 204
    r1 = await client.delete(f"/reports/1/shares/{share_id}", headers=auth_header(1))
    assert r1.status_code == 204

    # Second delete → also 204 (idempotent)
    r2 = await client.delete(f"/reports/1/shares/{share_id}", headers=auth_header(1))
    assert r2.status_code == 204

    # revoked_at set exactly once (one row, not two)
    row = (await db_session.execute(
        text("SELECT count(*) FROM report_shares WHERE id=:id AND revoked_at IS NOT NULL"),
        {"id": share_id},
    )).scalar()
    assert row == 1


async def test_no_token_returns_401(client):
    r = await client.post("/reports/1/shares", json={"target_user_id": 2, "permission": "view"})
    assert r.status_code == 401
