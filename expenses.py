"""
expenses.py

Routes to manage expenses: list, add, edit, duplicate, toggle and
delete. The shared logic lives in common.py.
"""

from datetime import date

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from common import (
    EXPENSE_FIELDS,
    EXPENSES_FILE,
    category_names,
    clear_payments,
    installment_info,
    next_id,
    payment_statuses,
    period_key,
    read_csv,
    render,
    validate_entry,
    write_csv,
)


router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"]
)


# ============================================================
# CSV
# ============================================================

def read_expenses():
    return read_csv(EXPENSES_FILE)


def write_expenses(expenses):
    write_csv(EXPENSES_FILE, EXPENSE_FIELDS, expenses)


# ============================================================
# HELPERS
# ============================================================

def _same_id(expense, expense_id):
    try:
        return int(expense.get("id", "")) == expense_id
    except (ValueError, TypeError):
        return False


def _find(expenses, expense_id):
    for expense in expenses:
        if _same_id(expense, expense_id):
            return expense

    return None


def _sorted(expenses):
    """Active ones first; inside each group, by concept."""

    return sorted(
        expenses,
        key=lambda e: (
            e.get("active") != "true",
            e.get("concept", "").lower()
        )
    )


def _with_installments(expenses):
    """Attach the installment summary to each expense that has one."""

    today = date.today()
    statuses = payment_statuses(period_key(today.month, today.year))

    result = []

    for expense in expenses:

        copy = dict(expense)

        copy["plan"] = installment_info(
            expense,
            today=today,
            current_month_status=statuses.get(str(expense.get("id", "")), "")
        )

        result.append(copy)

    return result


def _list_page(request, errors=None, values=None, status_code=200):

    expenses = _with_installments(_sorted(read_expenses()))

    used = sorted(
        {
            (e.get("category") or "").strip()
            for e in expenses
            if (e.get("category") or "").strip()
        }
    )

    return render(
        request,
        "expenses.html",
        {
            "active_page": "expenses",
            "expenses": expenses,
            # (value, label) for the filter dropdown
            "category_filters": [(name, name) for name in used],
            "catalog": category_names(),
            "errors": errors or [],
            "values": values or {},
            "today": date.today().isoformat(),
        },
        status_code
    )


def _edit_page(request, expense, errors=None, values=None, status_code=200):

    return render(
        request,
        "edit_expense.html",
        {
            "active_page": "expenses",
            "expense": expense,
            "plan": installment_info(expense),
            "errors": errors or [],
            "values": values or {},
        },
        status_code
    )


# ============================================================
# LIST
# ============================================================

@router.get("", response_class=HTMLResponse)
async def expenses_page(request: Request):
    return _list_page(request)


# ============================================================
# ADD
# ============================================================

@router.post("/add")
async def add_expense(
    request: Request,
    concept: str = Form(""),
    category: str = Form(""),
    amount: str = Form(""),
    type: str = Form(""),
    frequency: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    installments: str = Form(""),
    notes: str = Form("")
):
    values = {
        "concept": concept,
        "category": category,
        "amount": amount,
        "type": type,
        "frequency": frequency,
        "start_date": start_date,
        "end_date": end_date,
        "installments": installments,
        "notes": notes,
    }

    data, errors = validate_entry(values, is_expense=True)

    if errors:
        return _list_page(request, errors, values, 400)

    expenses = read_expenses()

    data["id"] = next_id(expenses)
    data["active"] = "true"

    expenses.append(data)

    write_expenses(expenses)

    return RedirectResponse(url="/expenses", status_code=303)


# ============================================================
# EDIT
# ============================================================

@router.get("/edit/{expense_id}", response_class=HTMLResponse)
async def edit_expense_page(request: Request, expense_id: int):

    expense = _find(read_expenses(), expense_id)

    if expense is None:
        return RedirectResponse(url="/expenses", status_code=303)

    return _edit_page(request, expense)


@router.post("/edit/{expense_id}")
async def edit_expense(
    request: Request,
    expense_id: int,
    concept: str = Form(""),
    category: str = Form(""),
    amount: str = Form(""),
    type: str = Form(""),
    frequency: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    installments: str = Form(""),
    active: str = Form("true"),
    notes: str = Form("")
):
    expenses = read_expenses()

    expense = _find(expenses, expense_id)

    if expense is None:
        return RedirectResponse(url="/expenses", status_code=303)

    values = {
        "concept": concept,
        "category": category,
        "amount": amount,
        "type": type,
        "frequency": frequency,
        "start_date": start_date,
        "end_date": end_date,
        "installments": installments,
        "active": active,
        "notes": notes,
    }

    data, errors = validate_entry(
        values,
        is_expense=True,
        extra_categories=[expense.get("category", "")]
    )

    if errors:
        return _edit_page(request, expense, errors, values, 400)

    expense.update(data)

    expense["active"] = "true" if active.strip().lower() == "true" else "false"

    write_expenses(expenses)

    return RedirectResponse(url="/expenses", status_code=303)


# ============================================================
# TOGGLE ACTIVE
# ============================================================

@router.post("/toggle/{expense_id}")
async def toggle_expense(expense_id: int):

    expenses = read_expenses()

    expense = _find(expenses, expense_id)

    if expense is not None:

        expense["active"] = (
            "false" if expense.get("active") == "true" else "true"
        )

        write_expenses(expenses)

    return RedirectResponse(url="/expenses", status_code=303)


# ============================================================
# DUPLICATE
# ============================================================

@router.post("/duplicate/{expense_id}")
async def duplicate_expense(expense_id: int):

    expenses = read_expenses()

    expense = _find(expenses, expense_id)

    if expense is None:
        return RedirectResponse(url="/expenses", status_code=303)

    copy = dict(expense)

    copy["id"] = next_id(expenses)
    copy["concept"] = f"{expense.get('concept', '')} (copia)"[:120]
    copy["active"] = "true"

    expenses.append(copy)

    write_expenses(expenses)

    return RedirectResponse(
        url=f"/expenses/edit/{copy['id']}",
        status_code=303
    )


# ============================================================
# DELETE
# ============================================================

@router.post("/delete/{expense_id}")
async def delete_expense(expense_id: int):

    expenses = [
        expense
        for expense in read_expenses()
        if not _same_id(expense, expense_id)
    ]

    write_expenses(expenses)

    clear_payments(expense_id)

    return RedirectResponse(url="/expenses", status_code=303)
