"""Revert: new row has source='revert'; content_after == original content_before; history unchanged."""
from sqlalchemy import text


async def test_revert_writes_correct_audit_row(client, auth_header, db_session):
    # Make one edit: v1 → v2
    patch_r = await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": "patched_value"}},
        headers={**auth_header(1), "If-Match": '"1"'},
    )
    assert patch_r.status_code == 200

    # Fetch the edit id
    hist_r = await client.get(
        "/reports/1/sections/executive_summary/history",
        headers=auth_header(1),
    )
    edit = hist_r.json()["edits"][0]
    edit_id = edit["id"]
    original_content_before = edit["content_before"]

    # Revert to that edit
    revert_r = await client.post(
        f"/reports/1/sections/executive_summary/revert/{edit_id}",
        headers=auth_header(1),
    )
    assert revert_r.status_code == 200
    new_version = revert_r.json()["version"]
    assert new_version == 3

    # New edit row has source='revert'
    revert_row = (await db_session.execute(
        text(
            "SELECT source, content_after FROM report_section_edits "
            "WHERE report_id=1 AND section_key='executive_summary' AND source='revert'"
        )
    )).mappings().first()
    assert revert_row is not None
    assert revert_row["source"] == "revert"

    # content_after of the revert == content_before of the original edit
    assert revert_row["content_after"] == original_content_before

    # Original edit row is still there (history is append-only)
    total = (await db_session.execute(
        text(
            "SELECT count(*) FROM report_section_edits "
            "WHERE report_id=1 AND section_key='executive_summary'"
        )
    )).scalar()
    assert total == 2  # original patch + revert


async def test_revert_bad_edit_id_returns_404(client, auth_header):
    r = await client.post(
        "/reports/1/sections/executive_summary/revert/99999",
        headers=auth_header(1),
    )
    assert r.status_code == 404


async def test_revert_viewer_forbidden(client, auth_header):
    # Create edit so there is something to revert
    await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": "v2"}},
        headers={**auth_header(1), "If-Match": '"1"'},
    )
    hist_r = await client.get(
        "/reports/1/sections/executive_summary/history",
        headers=auth_header(1),
    )
    edit_id = hist_r.json()["edits"][0]["id"]

    # Grant view access to user 3
    await client.post(
        "/reports/1/shares",
        json={"target_user_id": 3, "permission": "view"},
        headers=auth_header(1),
    )
    r = await client.post(
        f"/reports/1/sections/executive_summary/revert/{edit_id}",
        headers=auth_header(3),
    )
    assert r.status_code == 403
