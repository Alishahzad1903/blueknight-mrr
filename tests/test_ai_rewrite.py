"""AI rewrite: happy path bumps version; LLM failure → 502, zero rows written."""
from sqlalchemy import text


async def test_ai_rewrite_happy_path(client, auth_header, llm, db_session):
    r = await client.post(
        "/reports/1/sections/executive_summary/ai-rewrite",
        json={"instruction": "make it punchier"},
        headers=auth_header(1),
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2

    # LLM was called exactly once with the right metadata
    assert llm.call_count == 1
    assert llm.last_call["operation"] == "report.section.ai_rewrite"
    # request_id was propagated from middleware (not the default "-")
    assert llm.last_call["request_id"] not in ("", "-")

    # Edit row written with source=ai_rewrite
    row = (await db_session.execute(
        text(
            "SELECT source FROM report_section_edits "
            "WHERE report_id=1 AND section_key='executive_summary'"
        )
    )).first()
    assert row is not None
    assert row[0] == "ai_rewrite"


async def test_ai_rewrite_llm_failure_returns_502_no_db_write(client, auth_header, llm, db_session):
    before = (await db_session.execute(
        text(
            "SELECT count(*) FROM report_section_edits "
            "WHERE report_id=1 AND section_key='executive_summary'"
        )
    )).scalar()

    llm.inject_exception(RuntimeError("provider down"))
    r = await client.post(
        "/reports/1/sections/executive_summary/ai-rewrite",
        json={"instruction": "fail"},
        headers=auth_header(1),
    )
    assert r.status_code == 502

    after = (await db_session.execute(
        text(
            "SELECT count(*) FROM report_section_edits "
            "WHERE report_id=1 AND section_key='executive_summary'"
        )
    )).scalar()
    assert after == before, f"rows changed on LLM failure: before={before} after={after}"


async def test_ai_rewrite_stranger_forbidden(client, auth_header, llm):
    r = await client.post(
        "/reports/1/sections/executive_summary/ai-rewrite",
        json={"instruction": "rewrite"},
        headers=auth_header(4, org_id=2),
    )
    assert r.status_code == 403
    assert llm.call_count == 0  # LLM never called


async def test_ai_rewrite_missing_section_returns_404(client, auth_header, llm):
    r = await client.post(
        "/reports/1/sections/nonexistent/ai-rewrite",
        json={"instruction": "rewrite"},
        headers=auth_header(1),
    )
    assert r.status_code == 404
