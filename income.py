"""
income.py

Routes to manage income entries: list, add, edit, duplicate, toggle
and delete. The shared logic lives in common.py.
"""

from datetime import date

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from common import (
    INCOME_FIELDS,
    INCOME_FILE,
    next_id,
    read_csv,
    render,
    validate_entry,
    write_csv,
)


router = APIRouter(
    prefix="/income",
    tags=["Income"]
)


# ============================================================
# CSV
# ============================================================

def read_income():
    return read_csv(INCOME_FILE)


def write_income(entries):
    write_csv(INCOME_FILE, INCOME_FIELDS, entries)


# ============================================================
# HELPERS
# ============================================================

def _same_id(entry, entry_id):
    try:
        return int(entry.get("id", "")) == entry_id
    except (ValueError, TypeError):
        return False


def _find(entries, entry_id):
    for entry in entries:
        if _same_id(entry, entry_id):
            return entry

    return None


def _sorted(entries):
    """Active ones first; inside each group, by concept."""

    return sorted(
        entries,
        key=lambda e: (
            e.get("active") != "true",
            e.get("concept", "").lower()
        )
    )


def _list_page(request, errors=None, values=None, status_code=200):
    return render(
        request,
        "income.html",
        {
            "active_page": "income",
            "entries": _sorted(read_income()),
            "errors": errors or [],
            "values": values or {},
            "today": date.today().isoformat(),
        },
        status_code
    )


def _edit_page(request, entry, errors=None, values=None, status_code=200):
    return render(
        request,
        "edit_income.html",
        {
            "active_page": "income",
            "entry": entry,
            "errors": errors or [],
            "values": values or {},
        },
        status_code
    )


# ============================================================
# LIST
# ============================================================

@router.get("", response_class=HTMLResponse)
async def income_page(request: Request):
    return _list_page(request)


# ============================================================
# ADD
# ============================================================

@router.post("/add")
async def add_income(
    request: Request,
    concept: str = Form(""),
    amount: str = Form(""),
    frequency: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    notes: str = Form("")
):
    values = {
        "concept": concept,
        "amount": amount,
        "frequency": frequency,
        "start_date": start_date,
        "end_date": end_date,
        "notes": notes,
    }

    data, errors = validate_entry(values, is_expense=False)

    if errors:
        return _list_page(request, errors, values, 400)

    entries = read_income()

    data["id"] = next_id(entries)
    data["active"] = "true"

    entries.append(data)

    write_income(entries)

    return RedirectResponse(url="/income", status_code=303)


# ============================================================
# EDIT
# ============================================================

@router.get("/edit/{entry_id}", response_class=HTMLResponse)
async def edit_income_page(request: Request, entry_id: int):

    entry = _find(read_income(), entry_id)

    if entry is None:
        return RedirectResponse(url="/income", status_code=303)

    return _edit_page(request, entry)


@router.post("/edit/{entry_id}")
async def edit_income(
    request: Request,
    entry_id: int,
    concept: str = Form(""),
    amount: str = Form(""),
    frequency: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    active: str = Form("true"),
    notes: str = Form("")
):
    entries = read_income()

    entry = _find(entries, entry_id)

    if entry is None:
        return RedirectResponse(url="/income", status_code=303)

    values = {
        "concept": concept,
        "amount": amount,
        "frequency": frequency,
        "start_date": start_date,
        "end_date": end_date,
        "active": active,
        "notes": notes,
    }

    data, errors = validate_entry(values, is_expense=False)

    if errors:
        return _edit_page(request, entry, errors, values, 400)

    entry.update(data)

    entry["active"] = "true" if active.strip().lower() == "true" else "false"

    write_income(entries)

    return RedirectResponse(url="/income", status_code=303)


# ============================================================
# TOGGLE ACTIVE
# ============================================================

@router.post("/toggle/{entry_id}")
async def toggle_income(entry_id: int):

    entries = read_income()

    entry = _find(entries, entry_id)

    if entry is not None:

        entry["active"] = "false" if entry.get("active") == "true" else "true"

        write_income(entries)

    return RedirectResponse(url="/income", status_code=303)


# ============================================================
# DUPLICATE
# ============================================================

@router.post("/duplicate/{entry_id}")
async def duplicate_income(entry_id: int):

    entries = read_income()

    entry = _find(entries, entry_id)

    if entry is None:
        return RedirectResponse(url="/income", status_code=303)

    copy = dict(entry)

    copy["id"] = next_id(entries)
    copy["concept"] = f"{entry.get('concept', '')} (copia)"[:120]
    copy["active"] = "true"

    entries.append(copy)

    write_income(entries)

    return RedirectResponse(url=f"/income/edit/{copy['id']}", status_code=303)


# ============================================================
# DELETE
# ============================================================

@router.post("/delete/{entry_id}")
async def delete_income(entry_id: int):

    entries = [
        entry
        for entry in read_income()
        if not _same_id(entry, entry_id)
    ]

    write_income(entries)

    return RedirectResponse(url="/income", status_code=303)
