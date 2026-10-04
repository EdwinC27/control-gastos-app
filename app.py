"""
app.py

Application entry point and dashboard.

Run:   python app.py
Open:  http://127.0.0.1:2004
"""

from datetime import date

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from common import (
    EXPENSES_FILE,
    INCOME_FILE,
    MAX_YEAR,
    MIN_YEAR,
    MONTH_NAMES,
    STATIC_DIR,
    applies_to_month,
    movements_by_expense,
    ensure_files,
    installment_info,
    is_active,
    normalize_expense_type,
    payment_entries,
    payment_statuses,
    spend_totals,
    period_key,
    read_csv,
    render,
    to_amount,
)
from categories import router as categories_router
from expenses import router as expenses_router
from income import router as income_router
from movements import router as movements_router
from payments import router as payments_router


ensure_files()


app = FastAPI(
    title="Control de Gastos",
    description="Personal app to track income and expenses.",
    version="3.0.0"
)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(expenses_router)
app.include_router(income_router)
app.include_router(payments_router)
app.include_router(movements_router)
app.include_router(categories_router)


# Financial status thresholds (% of income still available)
POSITIVE_THRESHOLD = 15.0
BALANCED_THRESHOLD = 5.0


# ============================================================
# ERRORS
# ============================================================

@app.exception_handler(PermissionError)
async def locked_file(request: Request, exc: PermissionError):
    """
    On Windows the CSV cannot be saved while it is open in Excel.
    """

    return HTMLResponse(
        "<h1>No se pudo guardar</h1>"
        "<p>El archivo de datos está bloqueado. Si lo tienes abierto "
        "en Excel, ciérralo e inténtalo de nuevo.</p>"
        "<p><a href='/'>Volver al dashboard</a></p>",
        status_code=503
    )


# ============================================================
# CALCULATIONS
# ============================================================

def entries_of_month(records, month, year):
    """Records that apply to the month, with their amount as a number."""

    result = []

    for record in records:

        if applies_to_month(record, month, year):

            copy = dict(record)
            copy["value"] = to_amount(copy.get("amount"))

            result.append(copy)

    return result


def total(entries):
    return sum(entry["value"] for entry in entries)


def yearly_trend(expenses, income, year):
    """Income, expenses and available money for every month of the year."""

    trend = []

    for month in range(1, 13):

        total_income = total(entries_of_month(income, month, year))
        total_expenses = total(entries_of_month(expenses, month, year))

        trend.append(
            {
                "month": MONTH_NAMES[month],
                "income": total_income,
                "expenses": total_expenses,
                "available": total_income - total_expenses,
            }
        )

    return trend


def normalize_period(month, year):
    """Fall back to the current month or year when the input is invalid."""

    today = date.today()

    if month is None or not 1 <= month <= 12:
        month = today.month

    if year is None or not MIN_YEAR <= year <= MAX_YEAR:
        year = today.year

    return month, year


def financial_status(total_income, total_expenses, available_percent):
    """
    Positivo    -> 15% or more of the income is left  (green)
    Equilibrado -> between 5% and 15%                 (yellow)
    Déficit     -> less than 5%                       (red)
    """

    if total_income <= 0 and total_expenses <= 0:
        return "Sin movimientos", "badge-neutral", "neutral"

    if total_income <= 0:
        return "Déficit", "badge-danger", "danger"

    if available_percent >= POSITIVE_THRESHOLD:
        return "Positivo", "badge-success", "ok"

    if available_percent >= BALANCED_THRESHOLD:
        return "Equilibrado", "badge-warning", "warning"

    return "Déficit", "badge-danger", "danger"


def payment_summary(month_expenses):
    """
    Totals of the monthly "planned vs. real" checklist.

    An expense already paid or reserved counts in full. A pending one
    counts twice: what has been gathered so far (its abonos) and what
    is still missing.
    """

    summary = {
        "paid": 0.0,
        "reserved": 0.0,
        "saved": 0.0,
        "pending": 0.0,
        "used": 0.0,
        "n_paid": 0,
        "n_reserved": 0,
        "n_saved": 0,
        "n_pending": 0,
    }

    for expense in month_expenses:

        status = expense.get("payment_status", "pending")

        if status == "paid":
            summary["paid"] += expense["value"]
            summary["n_paid"] += 1

        elif status == "reserved":
            summary["reserved"] += expense["value"]
            summary["n_reserved"] += 1

        else:
            summary["saved"] += expense["saved"]
            summary["pending"] += expense["remaining"]
            summary["n_pending"] += 1

            if expense["saved"] > 0:
                summary["n_saved"] += 1

        if status == "reserved":
            summary["used"] += expense["used"]

    summary["covered"] = (
        summary["paid"] + summary["reserved"] + summary["saved"]
    )

    summary["total"] = summary["covered"] + summary["pending"]

    # What is left of the money already set aside.
    summary["unused"] = summary["reserved"] - summary["used"]

    summary["covered_percent"] = (
        summary["covered"] / summary["total"] * 100
        if summary["total"] > 0 else 0.0
    )

    return summary


def installment_plans(expenses):
    """Expenses paid in installments, with progress, balance and end date."""

    today = date.today()
    statuses = payment_statuses(period_key(today.month, today.year))

    plans = []

    for expense in expenses:

        if not is_active(expense):
            continue

        info = installment_info(
            expense,
            today=today,
            current_month_status=statuses.get(str(expense.get("id", "")), "")
        )

        if info is None:
            continue

        plans.append(
            {
                "id": expense.get("id", ""),
                "concept": expense.get("concept", ""),
                "category": expense.get("category", ""),
                **info,
            }
        )

    # Live plans first, and within those the ones ending sooner.
    plans.sort(key=lambda plan: (plan["finished"], plan["end_date"]))

    return plans


def category_breakdown(month_expenses, total_expenses):
    """How much each category represents of the month's spending."""

    totals = {}

    for expense in month_expenses:

        category = (expense.get("category") or "").strip() or "Otros"

        totals[category] = totals.get(category, 0) + expense["value"]

    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)

    return [
        {
            "category": category,
            "amount": amount,
            "percent": (
                amount / total_expenses * 100 if total_expenses > 0 else 0
            ),
        }
        for category, amount in ordered
    ]


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    month: int | None = None,
    year: int | None = None
):

    month, year = normalize_period(month, year)

    # ---- previous and next month ---------------------------------
    if month == 1:
        previous_month, previous_year = 12, year - 1
    else:
        previous_month, previous_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    # ---- data of the month ---------------------------------------
    all_expenses = read_csv(EXPENSES_FILE)
    all_income = read_csv(INCOME_FILE)

    month_expenses = entries_of_month(all_expenses, month, year)
    month_income = entries_of_month(all_income, month, year)

    # ---- payment status and abonos of every expense of the month -
    period = period_key(month, year)
    entries = payment_entries(period)
    movements = movements_by_expense(period)
    spent = spend_totals(period)

    for expense in month_expenses:

        expense_id = str(expense.get("id", ""))

        entry = entries.get(expense_id, {})

        status = entry.get("status", "pending")
        saved = min(max(0.0, entry.get("saved", 0.0)), expense["value"])

        expense["movements"] = movements.get(expense_id, [])

        expense["payment_status"] = status
        expense["saved"] = saved if status == "pending" else expense["value"]

        expense["remaining"] = (
            max(0.0, expense["value"] - saved) if status == "pending" else 0.0
        )

        expense["saved_percent"] = (
            expense["saved"] / expense["value"] * 100
            if expense["value"] > 0 else 0.0
        )

        # Money already spent out of what was put aside. It changes no
        # total: the expense stays reserved, this only tracks where it
        # went.
        expense["used"] = spent.get(expense_id, 0.0)
        expense["unused"] = expense["value"] - expense["used"]

        expense["used_percent"] = (
            max(0.0, min(expense["used"] / expense["value"] * 100, 100.0))
            if expense["value"] > 0 else 0.0
        )

    month_expenses.sort(key=lambda e: e["value"], reverse=True)
    month_income.sort(key=lambda e: e["value"], reverse=True)

    total_expenses = total(month_expenses)
    total_income = total(month_income)
    available = total_income - total_expenses

    payments = payment_summary(month_expenses)

    # ---- committed income ----------------------------------------
    without_income = total_income <= 0

    if not without_income:
        committed_percent = total_expenses / total_income * 100
        available_percent = available / total_income * 100
    else:
        committed_percent = 0.0
        available_percent = 0.0

    # ---- financial status (and the color of the bar) -------------
    status_label, status_class, status_level = financial_status(
        total_income,
        total_expenses,
        available_percent
    )

    if without_income:
        bar_percent = 100.0 if total_expenses > 0 else 0.0
    else:
        bar_percent = max(0.0, min(committed_percent, 100.0))

    # ---- fixed and extraordinary ---------------------------------
    total_fixed = sum(
        expense["value"]
        for expense in month_expenses
        if normalize_expense_type(expense.get("type")) == "fixed"
    )

    total_extraordinary = sum(
        expense["value"]
        for expense in month_expenses
        if normalize_expense_type(expense.get("type")) == "extraordinary"
    )

    # ---- comparison with the previous month ----------------------
    previous_total = total(
        entries_of_month(all_expenses, previous_month, previous_year)
    )

    if previous_total > 0:
        expenses_change = (
            (total_expenses - previous_total) / previous_total * 100
        )
    else:
        expenses_change = None

    # ---- installment plans ---------------------------------------
    plans = installment_plans(all_expenses)

    plans_balance = sum(plan["balance"] for plan in plans)

    # ---- spending by category ------------------------------------
    breakdown = category_breakdown(month_expenses, total_expenses)

    # ---- data for the charts (read by static/dashboard.js) -------
    chart_data = {
        "categories": [
            {"category": item["category"], "amount": item["amount"]}
            for item in breakdown
        ],
        "income_vs_expenses": {
            "income": total_income,
            "expenses": total_expenses,
        },
        "trend": yearly_trend(all_expenses, all_income, year),
    }

    return render(
        request,
        "index.html",
        {
            "active_page": "dashboard",

            "month": month,
            "year": year,
            "period": period,
            "month_name": MONTH_NAMES[month],

            "previous_month": previous_month,
            "previous_year": previous_year,
            "previous_month_name": MONTH_NAMES[previous_month],
            "next_month": next_month,
            "next_year": next_year,

            "expenses": month_expenses,
            "income": month_income,

            "total_expenses": total_expenses,
            "total_income": total_income,
            "available": available,

            "without_income": without_income,
            "committed_percent": committed_percent,
            "bar_percent": bar_percent,
            "status_level": status_level,
            "available_percent": available_percent,

            "status_label": status_label,
            "status_class": status_class,
            "positive_threshold": POSITIVE_THRESHOLD,
            "balanced_threshold": BALANCED_THRESHOLD,

            "payments": payments,

            "plans": plans,
            "plans_balance": plans_balance,

            "total_fixed": total_fixed,
            "total_extraordinary": total_extraordinary,

            "previous_total": previous_total,
            "expenses_change": expenses_change,

            "breakdown": breakdown,
            "largest_expenses": month_expenses[:5],

            "chart_data": chart_data,
        }
    )


if __name__ == "__main__":

    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=2004, reload=True)
