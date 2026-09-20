"""
payments.py

Mark every expense of the month as paid, reserved or pending
(the "planned vs. real" part of the dashboard).

The status lives in data/pagos.csv and does not change any total: it
only tells you what already went out and how much is still missing.
"""

from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from common import (
    EXPENSES_FILE,
    MAX_YEAR,
    MIN_YEAR,
    applies_to_month,
    normalize_payment_status,
    period_key,
    read_csv,
    save_payment_status,
)


router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


def _back_to_dashboard(month, year):
    return RedirectResponse(
        url=f"/?month={month}&year={year}#month-payments",
        status_code=303
    )


def _valid_period(month, year):
    return 1 <= month <= 12 and MIN_YEAR <= year <= MAX_YEAR


# ============================================================
# ONE EXPENSE
# ============================================================

@router.post("/status")
async def set_status(
    expense_id: str = Form(""),
    status: str = Form("pending"),
    month: int = Form(0),
    year: int = Form(0)
):

    if not _valid_period(month, year):
        return RedirectResponse(url="/", status_code=303)

    expense_id = (expense_id or "").strip()

    if expense_id:
        save_payment_status(
            expense_id,
            period_key(month, year),
            normalize_payment_status(status)
        )

    return _back_to_dashboard(month, year)


# ============================================================
# THE WHOLE MONTH
# ============================================================

@router.post("/status-all")
async def set_all_statuses(
    status: str = Form("pending"),
    month: int = Form(0),
    year: int = Form(0)
):

    if not _valid_period(month, year):
        return RedirectResponse(url="/", status_code=303)

    period = period_key(month, year)
    status = normalize_payment_status(status)

    for expense in read_csv(EXPENSES_FILE):

        if not applies_to_month(expense, month, year):
            continue

        save_payment_status(str(expense.get("id", "")).strip(), period, status)

    return _back_to_dashboard(month, year)
