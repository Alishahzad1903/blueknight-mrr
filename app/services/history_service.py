import logging
from app.repository import reports_repo, edits_repo
from app.services.section_service import NoAccessError

log = logging.getLogger("services.history")


def json_diff(before: dict, after: dict) -> dict:
    """Returns {added, removed, changed} computed at read time — never stored."""
    before_keys = set(before.keys()) if isinstance(before, dict) else set()
    after_keys = set(after.keys()) if isinstance(after, dict) else set()
    return {
        "added": {k: after[k] for k in after_keys - before_keys},
        "removed": {k: before[k] for k in before_keys - after_keys},
        "changed": {
            k: {"before": before[k], "after": after[k]}
            for k in before_keys & after_keys
            if before[k] != after[k]
        },
    }


async def list_history(session, *, report_id, section_key, limit, cursor, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] is None:
        raise NoAccessError()
    edits, next_cursor = await edits_repo.list_edits(session, report_id, section_key, limit, cursor)
    for edit in edits:
        edit["diff"] = json_diff(
            edit.get("content_before") or {},
            edit.get("content_after") or {},
        )
    return edits, next_cursor
