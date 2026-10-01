"""
payments.py

Track every expense of the month: mark it as pending, reserved or
paid, and record the abonos (partial amounts already put aside).

Both live in data/pagos.csv and change no total: they only tell you
what already went out, what you have gathered and how much is still
missing.
"""

from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from common import (
    EXPENSES_FILE,
    MAX_YEAR,
    MIN_YEAR,
    add_payment_saved,
    applies_to_month,
    normalize_payment_status,
    period_key,
    read_csv,
    set_payment_saved,
    set_payment_status,
    to_amount,
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


def _expense_amount(expense_id, month, year):
    """The amount of an expense, when it applies to that month."""

    expense_id = str(expense_id).strip()

    for expense in read_csv(EXPENSES_FILE):

        if str(expense.get("id", "")).strip() != expense_id:
            continue

        if not applies_to_month(expense, month, year):
            return None

        return to_amount(expense.get("amount"))

    return None


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
        set_payment_status(
            expense_id,
            period_key(month, year),
            normalize_payment_status(status)
        )

    return _back_to_dashboard(month, year)


# ============================================================
# ABONOS (money put aside little by little)
# ============================================================

@router.post("/saved")
async def save_abono(
    expense_id: str = Form(""),
    amount: str = Form(""),
    action: str = Form("add"),
    month: int = Form(0),
    year: int = Form(0)
):

    if not _valid_period(month, year):
        return RedirectResponse(url="/", status_code=303)

    expense_id = (expense_id or "").strip()

    if not expense_id:
        return _back_to_dashboard(month, year)

    period = period_key(month, year)
    limit = _expense_amount(expense_id, month, year)

    if action == "reset":
        set_payment_saved(expense_id, period, 0, None)

    elif action == "full" and limit:
        set_payment_saved(expense_id, period, limit, limit)

    else:
        amount = to_amount((amount or "").replace("$", "").replace(",", ""))

        if amount:
            add_payment_saved(expense_id, period, amount, limit)

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

        expense_id = str(expense.get("id", "")).strip()

        set_payment_status(expense_id, period, status)

        # Starting the month over also clears the abonos.
        if status == "pending":
            set_payment_saved(expense_id, period, 0, None)

    return _back_to_dashboard(month, year)
