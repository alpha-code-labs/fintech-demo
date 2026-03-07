from fastapi import APIRouter

from app.calculations.briefing import get_weekly_briefing

router = APIRouter()


@router.get("/briefing")
def briefing():
    return get_weekly_briefing()
