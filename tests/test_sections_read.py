"""GET section returns ETag; full access matrix (owner/editor/viewer/stranger/no-token)."""


async def test_get_section_returns_etag(client, auth_header):
    r = await client.get(
        "/reports/1/sections/executive_summary",
        headers=auth_header(1),
    )
    assert r.status_code == 200
    assert r.headers.get("ETag") == '"1"'
    assert r.json()["version"] == 1


async def test_get_section_not_found(client, auth_header):
    r = await client.get("/reports/1/sections/does_not_exist", headers=auth_header(1))
    assert r.status_code == 404


async def test_owner_can_read(client, auth_header):
    r = await client.get("/reports/1/sections/executive_summary", headers=auth_header(1))
    assert r.status_code == 200


async def test_editor_can_read(client, auth_header):
    # Grant user 2 edit access
    await client.post(
        "/reports/1/shares",
        json={"target_user_id": 2, "permission": "edit"},
        headers=auth_header(1),
    )
    r = await client.get("/reports/1/sections/executive_summary", headers=auth_header(2))
    assert r.status_code == 200


async def test_viewer_can_read(client, auth_header):
    await client.post(
        "/reports/1/shares",
        json={"target_user_id": 3, "permission": "view"},
        headers=auth_header(1),
    )
    r = await client.get("/reports/1/sections/executive_summary", headers=auth_header(3))
    assert r.status_code == 200


async def test_stranger_cannot_read(client, auth_header):
    # user 4 is org 2, no share
    r = await client.get(
        "/reports/1/sections/executive_summary",
        headers=auth_header(4, org_id=2),
    )
    assert r.status_code == 403


async def test_no_token_returns_401(client):
    r = await client.get("/reports/1/sections/executive_summary")
    assert r.status_code == 401


async def test_get_report_with_sections(client, auth_header):
    r = await client.get("/reports/1", headers=auth_header(1))
    assert r.status_code == 200
    body = r.json()
    assert "sections" in body
    assert len(body["sections"]) >= 3


async def test_patch_missing_if_match_returns_400(client, auth_header):
    r = await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": "new"}},
        headers=auth_header(1),
    )
    assert r.status_code == 400


async def test_patch_malformed_if_match_returns_400(client, auth_header):
    r = await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": "new"}},
        headers={**auth_header(1), "If-Match": "notquoted"},
    )
    assert r.status_code == 400


async def test_patch_viewer_returns_403(client, auth_header):
    await client.post(
        "/reports/1/shares",
        json={"target_user_id": 3, "permission": "view"},
        headers=auth_header(1),
    )
    r = await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": "viewer"}},
        headers={**auth_header(3), "If-Match": '"1"'},
    )
    assert r.status_code == 403


async def test_patch_happy_path_bumps_version_and_etag(client, auth_header):
    r = await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": "updated"}},
        headers={**auth_header(1), "If-Match": '"1"'},
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.headers["ETag"] == '"2"'


async def test_patch_stale_version_returns_412_with_current(client, auth_header):
    # First patch succeeds → version = 2
    await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": "first"}},
        headers={**auth_header(1), "If-Match": '"1"'},
    )
    # Second patch with same If-Match → 412
    r = await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": "stale"}},
        headers={**auth_header(1), "If-Match": '"1"'},
    )
    assert r.status_code == 412
    detail = r.json()["detail"]
    assert detail["error"] == "stale_version"
    assert detail["current_version"] == 2
