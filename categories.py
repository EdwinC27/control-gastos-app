"""
categories.py

Manage the category catalog from the app: create, rename, hide and
delete, without touching the code.

The catalog lives in data/categorias.csv.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from common import (
    EXPENSE_FIELDS,
    EXPENSES_FILE,
    category_usage,
    read_categories,
    read_csv,
    render,
    write_categories,
    write_csv,
)


router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


MAX_LENGTH = 40


# ============================================================
# HELPERS
# ============================================================

def _find(categories, name):
    name = (name or "").strip().lower()

    for category in categories:
        if category["name"].lower() == name:
            return category

    return None


def _rename_in_expenses(previous, new):
    """Move every expense using the old category to the new name."""

    expenses = read_csv(EXPENSES_FILE)
    changed = 0

    for expense in expenses:
        if (expense.get("category") or "").strip() == previous:
            expense["category"] = new
            changed += 1

    if changed:
        write_csv(EXPENSES_FILE, EXPENSE_FIELDS, expenses)

    return changed


def _page(request, errors=None, message="", status_code=200):

    usage = category_usage()

    categories = [
        {**category, "uses": usage.get(category["name"], 0)}
        for category in read_categories()
    ]

    orphans = sorted(
        name
        for name in usage
        if _find(categories, name) is None
    )

    return render(
        request,
        "categories.html",
        {
            "active_page": "categories",
            "categories": categories,
            "orphans": orphans,
            "errors": errors or [],
            "message": message,
            "MAX_LENGTH": MAX_LENGTH,
        },
        status_code
    )


def _validate_name(name, categories, except_for=""):
    """Returns (clean_name, errors)."""

    errors = []

    name = (name or "").strip()

    if not name:
        errors.append("El nombre de la categoría es obligatorio.")

    elif len(name) > MAX_LENGTH:
        errors.append(
            f"El nombre no puede pasar de {MAX_LENGTH} caracteres."
        )

    else:
        duplicate = _find(categories, name)

        if duplicate is not None and duplicate["name"] != except_for:
            errors.append(f"«{name}» ya existe en el catálogo.")

    return name, errors


# ============================================================
# LIST
# ============================================================

@router.get("", response_class=HTMLResponse)
async def categories_page(request: Request):
    return _page(request)


# ============================================================
# ADD
# ============================================================

@router.post("/add")
async def add_category(request: Request, name: str = Form("")):

    categories = read_categories()

    name, errors = _validate_name(name, categories)

    if errors:
        return _page(request, errors, status_code=400)

    categories.append({"name": name, "hidden": "false"})

    write_categories(categories)

    return RedirectResponse(url="/categories", status_code=303)


# ============================================================
# RENAME
# ============================================================

@router.post("/rename")
async def rename_category(
    request: Request,
    name: str = Form(""),
    new_name: str = Form("")
):

    categories = read_categories()

    category = _find(categories, name)

    if category is None:
        return RedirectResponse(url="/categories", status_code=303)

    new_name, errors = _validate_name(
        new_name,
        categories,
        except_for=category["name"]
    )

    if errors:
        return _page(request, errors, status_code=400)

    previous = category["name"]

    if previous == new_name:
        return RedirectResponse(url="/categories", status_code=303)

    category["name"] = new_name

    write_categories(categories)

    changed = _rename_in_expenses(previous, new_name)

    return _page(
        request,
        message=(
            f"«{previous}» ahora se llama «{new_name}». "
            f"Se actualizaron {changed} gasto(s)."
        )
    )


# ============================================================
# HIDE / SHOW
# ============================================================

@router.post("/toggle")
async def toggle_category(name: str = Form("")):

    categories = read_categories()

    category = _find(categories, name)

    if category is not None:
        category["hidden"] = (
            "false" if category["hidden"] == "true" else "true"
        )
        write_categories(categories)

    return RedirectResponse(url="/categories", status_code=303)


# ============================================================
# DELETE
# ============================================================

@router.post("/delete")
async def delete_category(request: Request, name: str = Form("")):

    categories = read_categories()

    category = _find(categories, name)

    if category is None:
        return RedirectResponse(url="/categories", status_code=303)

    uses = category_usage().get(category["name"], 0)

    if uses:
        return _page(
            request,
            errors=[
                f"«{category['name']}» la usan {uses} gasto(s). "
                "Cámbialos de categoría u ocúltala en vez de borrarla."
            ],
            status_code=400
        )

    write_categories([c for c in categories if c is not category])

    return RedirectResponse(url="/categories", status_code=303)


# ============================================================
# ADOPT A LOOSE CATEGORY
# (written in an expense but missing from the catalog)
# ============================================================

@router.post("/adopt")
async def adopt_category(request: Request, name: str = Form("")):

    categories = read_categories()

    name, errors = _validate_name(name, categories)

    if errors:
        return _page(request, errors, status_code=400)

    categories.append({"name": name, "hidden": "false"})

    write_categories(categories)

    return RedirectResponse(url="/categories", status_code=303)
