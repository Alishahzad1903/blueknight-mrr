import logging
from app.llm.client import LLMMessage
from app.middleware.request_id import request_id_var
from app.services.section_service import _apply_write, NotEditorError
from app.repository import reports_repo, sections_repo

log = logging.getLogger("services.ai_rewrite")


class LLMError(Exception):
    pass


async def ai_rewrite(session, *, report_id, section_key, instruction, llm_client, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] not in ("owner", "editor"):
        raise NotEditorError()
    section = await sections_repo.get_section(session, report_id, section_key)
    if section is None:
        return None
    messages = [
        LLMMessage(role="system", content="You rewrite report sections. Return JSON."),
        LLMMessage(
            role="user",
            content=f"Instruction: {instruction}\n\nCurrent content: {section['content']}",
        ),
    ]
    try:
        response = await llm_client.call(
            operation="report.section.ai_rewrite",
            request_id=request_id_var.get(),
            messages=messages,
        )
    except Exception as e:
        raise LLMError(str(e)) from e
    # LLM call succeeded — now open the DB transaction
    new_content = {"text": response.content}
    return await _apply_write(
        session,
        report_id=report_id,
        section_key=section_key,
        new_content=new_content,
        expected_version=section["version"],
        user_id=current_user.user_id,
        source="ai_rewrite",
    )
