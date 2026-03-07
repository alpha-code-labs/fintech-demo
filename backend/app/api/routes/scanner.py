from fastapi import APIRouter, Query

from app.calculations.scanner import run_scanner

router = APIRouter()


@router.get("/scanner")
def get_scanner(week_ending: str | None = Query(None, description="ISO date (YYYY-MM-DD) for the week to analyze. Defaults to latest.")):
    return run_scanner(week_ending)
