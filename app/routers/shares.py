from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import get_current_user, CurrentUser
from app.db import get_session
from app.services import share_service
from app.services.share_service import CrossOrgError, NotOwnerError
from app.repository.errors import DuplicateShareError
from app.schemas.shares import CreateShareRequest, ShareResponse

router = APIRouter(prefix="/reports/{report_id}/shares", tags=["shares"])


@router.post("", status_code=201, response_model=ShareResponse)
async def create_share(
    report_id: int,
    body: CreateShareRequest,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
):
    try:
        share = await share_service.create_share(
            session,
            report_id=report_id,
            target_user_id=body.target_user_id,
            permission=body.permission,
            current_user=user,
        )
        return share
    except NotOwnerError:
        raise HTTPException(403, "not owner")
    except CrossOrgError:
        raise HTTPException(403, "cross-org share not allowed")
    except DuplicateShareError:
        raise HTTPException(409, "share already exists")


@router.delete("/{share_id}", status_code=204)
async def delete_share(
    report_id: int,
    share_id: int,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
):
    try:
        await share_service.revoke_share(
            session, report_id=report_id, share_id=share_id, current_user=user
        )
    except NotOwnerError:
        raise HTTPException(403, "not owner")
    return None


@router.get("")
async def list_shares(
    report_id: int,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
):
    try:
        shares = await share_service.list_shares(session, report_id=report_id, current_user=user)
        return {"shares": shares}
    except NotOwnerError:
        raise HTTPException(403, "not owner")
