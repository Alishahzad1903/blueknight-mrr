import logging
from app.repository import sections_repo, reports_repo, edits_repo

log = logging.getLogger("services.sections")


class NoAccessError(Exception):
    pass


class NotEditorError(Exception):
    pass


class StaleVersion(Exception):
    def __init__(self, current_version: int):
        self.current_version = current_version


class EditNotFound(Exception):
    pass


async def get_report(session, *, report_id, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] is None:
        raise NoAccessError()
    return await reports_repo.get_report_with_sections(session, report_id)


async def get_section(session, *, report_id, section_key, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] is None:
        raise NoAccessError()
    return await sections_repo.get_section(session, report_id, section_key)


async def _apply_write(session, *, report_id, section_key, new_content, expected_version, user_id, source):
    result = await sections_repo.write_section(
        session,
        report_id=report_id,
        section_key=section_key,
        new_content=new_content,
        expected_version=expected_version,
        user_id=user_id,
        source=source,
    )
    if result is None:
        current = await sections_repo.get_section(session, report_id, section_key)
        raise StaleVersion(current_version=current["version"] if current else 0)
    await session.commit()
    log.info(
        "section.write",
        extra={
            "user_id": user_id,
            "report_id": report_id,
            "section_key": section_key,
            "version": result["new_version"],
            "source": source,
        },
    )
    return result


async def patch_section(session, *, report_id, section_key, content, if_match_version, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] not in ("owner", "editor"):
        raise NotEditorError()
    return await _apply_write(
        session,
        report_id=report_id,
        section_key=section_key,
        new_content=content,
        expected_version=if_match_version,
        user_id=current_user.user_id,
        source="human",
    )


async def revert_section(session, *, report_id, section_key, edit_id, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] not in ("owner", "editor"):
        raise NotEditorError()
    edit = await edits_repo.get_edit_by_id(session, edit_id)
    if not edit or edit["report_id"] != report_id or edit["section_key"] != section_key:
        raise EditNotFound()
    current = await sections_repo.get_section(session, report_id, section_key)
    return await _apply_write(
        session,
        report_id=report_id,
        section_key=section_key,
        new_content=edit["content_before"],
        expected_version=current["version"],
        user_id=current_user.user_id,
        source="revert",
    )
