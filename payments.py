"""
payments.py

Track every expense of the month: mark it as pending, reserved or
paid, and register its movements — abonos (money put aside) and usos
(money spent out of it) — each one with its own note and timestamp.

The status lives in data/pagos.csv and the movements in
data/movimientos.csv.
Neither changes any total: they only tell you what already went out,
what you have gathered and how much is still missing.
"""

from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from common import (
    EXPENSES_FILE,
    MAX_YEAR,
    MIN_YEAR,
    add_movement,
    applies_to_month,
    clear_movements,
    delete_movement,
    normalize_payment_status,
    period_key,
    read_csv,
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
# STATUS OF ONE EXPENSE
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
# MOVEMENTS: ABONOS AND USOS
# ============================================================

@router.post("/movement")
async def register_movement(
    expense_id: str = Form(""),
    amount: str = Form(""),
    note: str = Form(""),
    kind: str = Form("deposit"),
    month: int = Form(0),
    year: int = Form(0)
):

    if not _valid_period(month, year):
        return RedirectResponse(url="/", status_code=303)

    expense_id = (expense_id or "").strip()

    if not expense_id:
        return _back_to_dashboard(month, year)

    amount = to_amount((amount or "").replace("$", "").replace(",", ""))

    if amount:
        add_movement(
            expense_id,
            period_key(month, year),
            amount,
            note,
            kind,
            _expense_amount(expense_id, month, year)
        )

    return _back_to_dashboard(month, year)


@router.post("/movement/delete")
async def remove_movement(
    movement_id: str = Form(""),
    month: int = Form(0),
    year: int = Form(0)
):

    if not _valid_period(month, year):
        return RedirectResponse(url="/", status_code=303)

    movement_id = (movement_id or "").strip()

    if movement_id:
        delete_movement(movement_id)

    return _back_to_dashboard(month, year)


@router.post("/movement/clear")
async def clear_expense_movements(
    expense_id: str = Form(""),
    kind: str = Form(""),
    month: int = Form(0),
    year: int = Form(0)
):

    if not _valid_period(month, year):
        return RedirectResponse(url="/", status_code=303)

    expense_id = (expense_id or "").strip()

    if expense_id:
        clear_movements(
            expense_id,
            period_key(month, year),
            kind or None
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

        expense_id = str(expense.get("id", "")).strip()

        set_payment_status(expense_id, period, status)

        # Starting the month over also clears the movements.
        if status == "pending":
            clear_movements(expense_id, period)

    return _back_to_dashboard(month, year)
