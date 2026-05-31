import hashlib
import json
import re
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from fastapi.responses import JSONResponse
from app.auth.deps import get_current_user, CurrentUser
from app.db import get_session
from app.services import section_service, history_service, ai_rewrite_service
from app.services.section_service import NoAccessError, NotEditorError, StaleVersion, EditNotFound
from app.services.ai_rewrite_service import LLMError
from app.schemas.sections import PatchSectionRequest, AIRewriteRequest
from app.dependencies import get_llm_client
from app.repository import idempotency_repo

router = APIRouter(tags=["sections"])

ETAG_RE = re.compile(r'^"(\d+)"$')


@router.get("/reports/{report_id}/sections/{section_key}")
async def get_section(
    report_id: int,
    section_key: str,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
):
    try:
        section = await section_service.get_section(
            session, report_id=report_id, section_key=section_key, current_user=user
        )
    except NoAccessError:
        raise HTTPException(403, "no access")
    if section is None:
        raise HTTPException(404, "section not found")
    response.headers["ETag"] = f'"{section["version"]}"'
    return section


@router.patch("/reports/{report_id}/sections/{section_key}")
async def patch_section(
    report_id: int,
    section_key: str,
    body: PatchSectionRequest,
    response: Response,
    if_match: str = Header(default=None, alias="If-Match"),
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
):
    if not if_match:
        raise HTTPException(400, "If-Match header required")
    m = ETAG_RE.match(if_match.strip())
    if not m:
        raise HTTPException(400, "If-Match must be a quoted integer")
    expected_version = int(m.group(1))
    try:
        result = await section_service.patch_section(
            session,
            report_id=report_id,
            section_key=section_key,
            content=body.content,
            if_match_version=expected_version,
            current_user=user,
        )
    except NotEditorError:
        raise HTTPException(403, "not an editor")
    except StaleVersion as e:
        raise HTTPException(
            412,
            detail={"error": "stale_version", "current_version": e.current_version},
        )
    response.headers["ETag"] = f'"{result["new_version"]}"'
    return {"version": result["new_version"]}


@router.get("/reports/{report_id}/sections/{section_key}/history")
async def get_history(
    report_id: int,
    section_key: str,
    limit: int = 50,
    cursor: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
):
    limit = min(max(limit, 1), 200)
    try:
        edits, next_cursor = await history_service.list_history(
            session,
            report_id=report_id,
            section_key=section_key,
            limit=limit,
            cursor=cursor,
            current_user=user,
        )
    except NoAccessError:
        raise HTTPException(403, "no access")
    return {"edits": edits, "next_cursor": next_cursor}


@router.post("/reports/{report_id}/sections/{section_key}/revert/{edit_id}")
async def revert_section(
    report_id: int,
    section_key: str,
    edit_id: int,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
):
    try:
        result = await section_service.revert_section(
            session,
            report_id=report_id,
            section_key=section_key,
            edit_id=edit_id,
            current_user=user,
        )
    except NotEditorError:
        raise HTTPException(403, "not an editor")
    except EditNotFound:
        raise HTTPException(404, "edit not found")
    except StaleVersion:
        raise HTTPException(409, "concurrent modification, retry")
    return {"version": result["new_version"]}


def _hash(method: str, path: str, body: dict) -> str:
    raw = f"{method}:{path}:{json.dumps(body, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/reports/{report_id}/sections/{section_key}/ai-rewrite")
async def ai_rewrite(
    report_id: int,
    section_key: str,
    body: AIRewriteRequest,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    llm=Depends(get_llm_client),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    req_hash = _hash(
        "POST",
        f"/reports/{report_id}/sections/{section_key}/ai-rewrite",
        body.model_dump(),
    )

    if idempotency_key:
        cached = await idempotency_repo.get_cached(session, idempotency_key, user.user_id)
        if cached:
            if cached["request_hash"] != req_hash:
                raise HTTPException(422, "idempotency key reused with different body")
            return JSONResponse(
                content=cached["response_body"], status_code=cached["status_code"]
            )

    try:
        result = await ai_rewrite_service.ai_rewrite(
            session,
            report_id=report_id,
            section_key=section_key,
            instruction=body.instruction,
            llm_client=llm,
            current_user=user,
        )
    except NotEditorError:
        raise HTTPException(403, "not an editor")
    except LLMError:
        raise HTTPException(502, "LLM provider error")
    if result is None:
        raise HTTPException(404, "section not found")

    response_body = {"version": result["new_version"]}
    if idempotency_key:
        await idempotency_repo.store(
            session, idempotency_key, user.user_id, req_hash, 200, response_body
        )
    return response_body
