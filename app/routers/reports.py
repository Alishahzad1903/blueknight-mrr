from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import get_current_user, CurrentUser
from app.db import get_session
from app.services import section_service
from app.services.section_service import NoAccessError

router = APIRouter(tags=["reports"])


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
):
    try:
        return await section_service.get_report(session, report_id=report_id, current_user=user)
    except NoAccessError:
        raise HTTPException(403, "no access")
