import logging
from app.repository import reports_repo, edits_repo
from app.services.section_service import NoAccessError

log = logging.getLogger("services.history")


async def list_history(session, *, report_id, section_key, limit, cursor, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] is None:
        raise NoAccessError()
    return await edits_repo.list_edits(session, report_id, section_key, limit, cursor)
