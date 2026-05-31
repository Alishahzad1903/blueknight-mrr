import logging
from app.repository import shares_repo, reports_repo
from app.repository.errors import DuplicateShareError

log = logging.getLogger("services.shares")


class CrossOrgError(Exception):
    pass


class NotOwnerError(Exception):
    pass


async def create_share(session, *, report_id, target_user_id, permission, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] != "owner":
        raise NotOwnerError()
    target_org = await shares_repo.get_user_org(session, target_user_id)
    if target_org is None or target_org != current_user.org_id:
        raise CrossOrgError()
    share = await shares_repo.create_share(session, report_id, target_user_id, permission, current_user.user_id)
    await session.commit()
    log.info(
        "share.created",
        extra={"user_id": current_user.user_id, "report_id": report_id, "operation": "share.create"},
    )
    return share


async def revoke_share(session, *, report_id, share_id, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] != "owner":
        raise NotOwnerError()
    await shares_repo.revoke_share(session, share_id, report_id)
    await session.commit()
    log.info("share.revoked", extra={"user_id": current_user.user_id, "report_id": report_id})


async def list_shares(session, *, report_id, current_user):
    access = await reports_repo.get_report_access(session, report_id, current_user.user_id)
    if not access or access["access"] != "owner":
        raise NotOwnerError()
    return await shares_repo.list_active_shares(session, report_id)
