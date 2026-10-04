"""
movements.py

The Movimientos tab: every abono and uso of a month in one place,
with its own filters, its totals and a form to register new ones.

The data lives in data/movimientos.csv (see common.py).
"""

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from common import (
    EXPENSES_FILE,
    MAX_YEAR,
    MIN_YEAR,
    MONTH_NAMES,
    MOVEMENT_KIND_LABELS,
    PAYMENT_STATUS_LABELS,
    applies_to_month,
    movement_kind_for,
    movements_of,
    payment_entries,
    period_key,
    read_csv,
    render,
    to_amount,
)


router = APIRouter(
    prefix="/movements",
    tags=["Movements"]
)


def _normalize_period(month, year):
    """Fall back to the current month or year when the input is invalid."""

    today = date.today()

    if month is None or not 1 <= month <= 12:
        month = today.month

    if year is None or not MIN_YEAR <= year <= MAX_YEAR:
        year = today.year

    return month, year


def _expenses_of_month(month, year, period):
    """
    The expenses that apply to the month, by id, plus the ones you can
    still register a movement for.

    An expense already paid is left out of the list: there is nothing
    left to register on it.
    """

    by_id = {}
    options = []

    statuses = payment_entries(period)

    for expense in read_csv(EXPENSES_FILE):

        expense_id = str(expense.get("id", "")).strip()

        by_id[expense_id] = expense

        if not applies_to_month(expense, month, year):
            continue

        status = statuses.get(expense_id, {}).get("status", "pending")

        if status == "paid":
            continue

        kind = movement_kind_for(expense_id, period)

        options.append(
            {
                "id": expense_id,
                "concept": expense.get("concept", ""),
                "category": expense.get("category", ""),
                "amount": to_amount(expense.get("amount")),
                "status": status,
                "status_label": PAYMENT_STATUS_LABELS[status],
                "kind": kind,
                "kind_label": MOVEMENT_KIND_LABELS[kind],
            }
        )

    options.sort(key=lambda e: e["concept"].lower())

    return by_id, options


def _totals(movements):

    deposits = [m for m in movements if m["kind"] == "deposit"]
    spends = [m for m in movements if m["kind"] == "spend"]

    return {
        "deposits": sum(m["amount"] for m in deposits),
        "spends": sum(m["amount"] for m in spends),
        "n_deposits": len(deposits),
        "n_spends": len(spends),
    }


@router.get("", response_class=HTMLResponse)
async def movements_page(
    request: Request,
    month: int | None = None,
    year: int | None = None,
    expense: str | None = None
):

    month, year = _normalize_period(month, year)

    if month == 1:
        previous_month, previous_year = 12, year - 1
    else:
        previous_month, previous_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    period = period_key(month, year)

    expenses_by_id, options = _expenses_of_month(month, year, period)

    only = (expense or "").strip()

    movements = movements_of(period, only or None)

    # Each movement carries the concept and category of its expense.
    for movement in movements:

        source = expenses_by_id.get(movement["expense_id"], {})

        movement["concept"] = (
            source.get("concept") or f"Gasto #{movement['expense_id']}"
        )
        movement["category"] = source.get("category", "")

    categories = sorted(
        {m["category"] for m in movements if m["category"]}
    )

    focus = expenses_by_id.get(only, {}) if only else {}

    return render(
        request,
        "movements.html",
        {
            "active_page": "movements",

            "month": month,
            "year": year,
            "month_name": MONTH_NAMES[month],

            "previous_month": previous_month,
            "previous_year": previous_year,
            "previous_month_name": MONTH_NAMES[previous_month],
            "next_month": next_month,
            "next_year": next_year,

            "movements": movements,
            "totals": _totals(movements),

            "expense_options": options,
            "category_filters": [(name, name) for name in categories],

            "focus_id": only,
            "focus": focus,
        }
    )
