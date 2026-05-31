"""History pagination: 3 edits, limit=2 returns 2 + cursor; cursor returns remaining 1."""


async def _patch(client, auth_header, version: int, text_val: str):
    r = await client.patch(
        "/reports/1/sections/executive_summary",
        json={"content": {"text": text_val}},
        headers={**auth_header(1), "If-Match": f'"{version}"'},
    )
    assert r.status_code == 200, r.text
    return r.json()["version"]


async def test_history_pagination(client, auth_header):
    # Make 3 edits: v1→2, v2→3, v3→4
    v = 1
    for i in range(3):
        v = await _patch(client, auth_header, v, f"edit_{i}")

    assert v == 4  # sanity

    # Page 1 — limit=2, should return 2 most-recent edits + a cursor
    r = await client.get(
        "/reports/1/sections/executive_summary/history?limit=2",
        headers=auth_header(1),
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["edits"]) == 2
    assert body["next_cursor"] is not None

    # Edits come back newest-first (DESC)
    assert body["edits"][0]["version_after"] > body["edits"][1]["version_after"]

    # Page 2 — using cursor, should return 1 edit + no cursor
    r2 = await client.get(
        f'/reports/1/sections/executive_summary/history?limit=2&cursor={body["next_cursor"]}',
        headers=auth_header(1),
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert len(body2["edits"]) == 1
    assert body2["next_cursor"] is None

    # All 3 unique version_afters together
    all_versions = {e["version_after"] for e in body["edits"] + body2["edits"]}
    assert all_versions == {2, 3, 4}


async def test_history_default_order_newest_first(client, auth_header):
    v = 1
    for i in range(2):
        v = await _patch(client, auth_header, v, f"e{i}")

    r = await client.get(
        "/reports/1/sections/executive_summary/history",
        headers=auth_header(1),
    )
    edits = r.json()["edits"]
    assert len(edits) == 2
    assert edits[0]["version_after"] > edits[1]["version_after"]


async def test_history_stranger_forbidden(client, auth_header):
    r = await client.get(
        "/reports/1/sections/executive_summary/history",
        headers=auth_header(4, org_id=2),
    )
    assert r.status_code == 403
