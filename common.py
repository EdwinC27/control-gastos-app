"""
common.py

Shared code used by app.py, expenses.py, income.py, payments.py
and categories.py.

Everything that used to be duplicated lives here: paths, CSV reading
and writing, validation, the rule that decides whether an entry
applies to a given month, installment plans, the monthly payment
status, the editable category catalog and the Jinja filters.

User facing strings stay in Spanish on purpose: the app is in Spanish.
"""

import calendar
import csv
import math
import os
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
BACKUP_DIR = DATA_DIR / "backups"

for _folder in (DATA_DIR, TEMPLATES_DIR, STATIC_DIR):
    _folder.mkdir(exist_ok=True)

EXPENSES_FILE = DATA_DIR / "gastos.csv"
INCOME_FILE = DATA_DIR / "ingresos.csv"
PAYMENTS_FILE = DATA_DIR / "pagos.csv"
CATEGORIES_FILE = DATA_DIR / "categorias.csv"

EXPENSE_FIELDS = [
    "id",
    "concept",
    "category",
    "amount",
    "type",
    "frequency",
    "start_date",
    "end_date",
    "installments",
    "active",
    "notes",
]

INCOME_FIELDS = [
    "id",
    "concept",
    "amount",
    "frequency",
    "start_date",
    "end_date",
    "active",
    "notes",
]

# Payment status of one expense in one month.
PAYMENT_FIELDS = [
    "expense_id",
    "period",
    "status",
    "saved",
    "updated",
]

CATEGORY_FIELDS = [
    "name",
    "hidden",
]

# Column names used by older versions of the app (or typed by hand in
# Excel). They are translated on read, so existing files keep working.
LEGACY_COLUMNS = {
    "concepto": "concept",
    "categoria": "category",
    "monto": "amount",
    "tipo": "type",
    "frecuencia": "frequency",
    "fecha_inicio": "start_date",
    "fecha_fin": "end_date",
    "num_pagos": "installments",
    "activo": "active",
    "notas": "notes",
    "gasto_id": "expense_id",
    "periodo": "period",
    "estado": "status",
    "actualizado": "updated",
    "nombre": "name",
    "oculta": "hidden",
}


# ============================================================
# CATALOGS
# ============================================================

# Categories the catalog starts with. From then on they are managed
# from /categories.
DEFAULT_CATEGORIES = [
    "Vivienda",
    "Terreno",
    "Salud",
    "Alimentación",
    "Transporte",
    "Servicios",
    "Educación",
    "Entretenimiento",
    "Mascotas",
    "Seguros",
    "Deudas",
    "Otros",
]

# (value stored in the CSV, label shown to the user)
EXPENSE_TYPES = [
    ("fixed", "Gasto fijo"),
    ("extraordinary", "Gasto extraordinario"),
]

FREQUENCIES = [
    ("monthly", "Mensual"),
    ("yearly", "Anual"),
    ("one_time", "Único"),
]

# Statuses of the monthly "planned vs. real" checklist.
PAYMENT_STATUSES = [
    ("pending", "Falta por juntar"),
    ("reserved", "Apartado"),
    ("paid", "Pagado"),
]

EXPENSE_TYPE_VALUES = [value for value, _ in EXPENSE_TYPES]
FREQUENCY_VALUES = [value for value, _ in FREQUENCIES]
PAYMENT_STATUS_VALUES = [value for value, _ in PAYMENT_STATUSES]

EXPENSE_TYPE_LABELS = dict(EXPENSE_TYPES)
FREQUENCY_LABELS = dict(FREQUENCIES)
PAYMENT_STATUS_LABELS = dict(PAYMENT_STATUSES)

# Frequencies that can be paid in installments.
FREQUENCIES_WITH_INSTALLMENTS = ("monthly", "yearly")

MAX_INSTALLMENTS = 600

MONTH_NAMES = [
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

# [(1, "Enero"), (2, "Febrero"), ...]
MONTHS = list(enumerate(MONTH_NAMES))[1:]

MIN_YEAR = 2000
MAX_YEAR = 2100

# Accepted spellings for each stored value, including the Spanish ones
# written by older versions of the app.
_FREQUENCY_ALIASES = {
    "monthly": "monthly",
    "mensual": "monthly",
    "yearly": "yearly",
    "annual": "yearly",
    "anual": "yearly",
    "one_time": "one_time",
    "onetime": "one_time",
    "unico": "one_time",
    "único": "one_time",
}

_EXPENSE_TYPE_ALIASES = {
    "fixed": "fixed",
    "fijo": "fixed",
    "extraordinary": "extraordinary",
    "extraordinario": "extraordinary",
}

_PAYMENT_STATUS_ALIASES = {
    "pending": "pending",
    "pendiente": "pending",
    "reserved": "reserved",
    "apartado": "reserved",
    "paid": "paid",
    "pagado": "paid",
}


# ============================================================
# CONVERSIONS
# ============================================================

def to_amount(value):
    """Convert a value to float. Returns 0.0 when it cannot."""

    try:
        number = float(value or 0)
    except (ValueError, TypeError):
        return 0.0

    if not math.isfinite(number):
        return 0.0

    return number


def parse_amount(value):
    """
    Turn what the user typed into a float.
    Returns None when it is not a valid number.
    """

    text = str(value if value is not None else "")
    text = text.strip().replace("$", "").replace(",", "")

    if not text:
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    if not math.isfinite(number):
        return None

    return number


def parse_int(value):
    """Convert to int. Returns None when it is not a valid integer."""

    text = str(value if value is not None else "").strip()

    if not text:
        return None

    try:
        return int(float(text))
    except ValueError:
        return None


def parse_date(text):
    """Convert 'YYYY-MM-DD' to date. Returns None when invalid."""

    try:
        return datetime.strptime(
            (text or "").strip(),
            "%Y-%m-%d"
        ).date()
    except (ValueError, TypeError, AttributeError):
        return None


def normalize_frequency(value):
    """
    Returns 'monthly', 'yearly' or 'one_time'.
    Returns '' when the value is not recognized.
    """

    return _FREQUENCY_ALIASES.get((value or "").strip().lower(), "")


def normalize_expense_type(value):
    """Returns 'fixed', 'extraordinary' or ''."""

    return _EXPENSE_TYPE_ALIASES.get((value or "").strip().lower(), "")


def normalize_payment_status(value):
    """Returns 'pending', 'reserved' or 'paid'."""

    return _PAYMENT_STATUS_ALIASES.get(
        (value or "").strip().lower(),
        "pending"
    )


def add_months(value, months):
    """Add months to a date, clamping to the end of the month."""

    total = value.month - 1 + months

    year = value.year + total // 12
    month = total % 12 + 1

    day = min(value.day, calendar.monthrange(year, month)[1])

    return date(year, month, day)


def add_years(value, years):
    """Add years to a date (handles February 29th)."""

    return add_months(value, years * 12)


# ============================================================
# CSV (safe reading and writing)
# ============================================================

def _create_if_missing(path, fields):
    if not path.exists():
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            csv.writer(handle).writerow(fields)


def _normalize_values(record, fields):
    """Rewrite stored values to their canonical form."""

    if "frequency" in fields and record.get("frequency"):
        record["frequency"] = normalize_frequency(record["frequency"])

    if "type" in fields and record.get("type"):
        record["type"] = normalize_expense_type(record["type"])

    if "status" in fields and record.get("status"):
        record["status"] = normalize_payment_status(record["status"])

    return record


def _needs_migration(path, fields, records):
    """True when the header or any stored value is outdated."""

    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        header = [(c or "").strip() for c in next(csv.reader(handle), [])]

    if header != fields:
        return True

    for record in records:

        original = dict(record)

        if _normalize_values(dict(record), fields) != original:
            return True

    return False


def _migrate(path, fields):
    """
    Bring an older file up to date: translate the Spanish column names
    and values written by previous versions, keeping the data intact.
    A backup is taken automatically before the file is rewritten.
    """

    if not path.exists():
        return

    records = read_csv(path)

    if not _needs_migration(path, fields, records):
        return

    for record in records:

        _normalize_values(record, fields)

        for field in fields:
            record.setdefault(field, "")

    write_csv(path, fields, records)


def ensure_files():
    """Create the CSV files and migrate older ones."""

    for path, fields in (
        (EXPENSES_FILE, EXPENSE_FIELDS),
        (INCOME_FILE, INCOME_FIELDS),
        (PAYMENTS_FILE, PAYMENT_FIELDS),
    ):
        _create_if_missing(path, fields)
        _migrate(path, fields)

    ensure_categories()

    _migrate(CATEGORIES_FILE, CATEGORY_FIELDS)


def read_csv(path):
    """
    Read a CSV file into a list of dictionaries.

    Legacy Spanish column names are translated on the fly and 'active'
    is always normalized to 'true' or 'false' (which also fixes files
    holding 'True'/'False').
    """

    path = Path(path)

    if not path.exists():
        return []

    records = []

    with open(path, "r", encoding="utf-8-sig", newline="") as handle:

        for row in csv.DictReader(handle):

            record = {}

            for key, value in row.items():

                if key is None:
                    continue

                key = key.strip()
                key = LEGACY_COLUMNS.get(key, key)

                record[key] = value.strip() if isinstance(value, str) else ""

            # Skip completely empty rows (typical of Excel)
            if not any(record.values()):
                continue

            if "active" in record:
                record["active"] = (
                    "true"
                    if record.get("active", "").lower() == "true"
                    else "false"
                )

            records.append(record)

    return records


def _daily_backup(path):
    """
    Save a copy of the file, as it was, the first time it changes each
    day. Keeps the last 30 backups.
    """

    if not path.exists():
        return

    BACKUP_DIR.mkdir(exist_ok=True)

    target = BACKUP_DIR / f"{path.stem}_{date.today():%Y-%m-%d}.csv"

    if not target.exists():
        shutil.copy2(path, target)

    backups = sorted(BACKUP_DIR.glob(f"{path.stem}_*.csv"))

    for old in backups[:-30]:
        old.unlink(missing_ok=True)


def write_csv(path, fields, records):
    """
    Rewrite the CSV safely: write a temporary file first and then
    replace the original, so a failure halfway through cannot leave a
    corrupted file behind.

    Saved with a BOM (utf-8-sig) so Excel shows accents correctly when
    the CSV is opened directly.
    """

    path = Path(path)

    _daily_backup(path)

    descriptor, temporary_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f"{path.stem}_",
        suffix=".tmp"
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=fields,
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(records)

        os.replace(temporary_path, path)

    except BaseException:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


def next_id(records):
    """Return the next available ID."""

    ids = []

    for record in records:
        try:
            ids.append(int(record["id"]))
        except (ValueError, TypeError, KeyError):
            pass

    return max(ids) + 1 if ids else 1


# ============================================================
# CATEGORIES (catalog editable from the app)
# ============================================================

def read_categories():
    """List of {'name': ..., 'hidden': 'true'/'false'}."""

    categories = []

    for row in read_csv(CATEGORIES_FILE):

        name = (row.get("name") or "").strip()

        if not name:
            continue

        categories.append(
            {
                "name": name,
                "hidden": (
                    "true"
                    if (row.get("hidden") or "").strip().lower() == "true"
                    else "false"
                ),
            }
        )

    return categories


def write_categories(categories):
    write_csv(CATEGORIES_FILE, CATEGORY_FIELDS, categories)


def ensure_categories():
    """
    Build the catalog the first time, using the default categories plus
    any category already written in the expenses file.
    """

    if CATEGORIES_FILE.exists():
        return

    names = list(DEFAULT_CATEGORIES)

    for expense in read_csv(EXPENSES_FILE):

        category = (expense.get("category") or "").strip()

        if category and category not in names:
            names.append(category)

    write_categories([{"name": name, "hidden": "false"} for name in names])


def category_names(include_hidden=False):
    """Catalog names, in the order they are stored."""

    return [
        category["name"]
        for category in read_categories()
        if include_hidden or category["hidden"] != "true"
    ]


def category_options(current=""):
    """
    Categories offered in a form.

    Includes the visible ones plus the category the expense already had,
    even when it is hidden or no longer in the catalog.
    """

    names = category_names()

    current = (current or "").strip()

    if current and current not in names:
        names = names + [current]

    return names


def allowed_categories(extra=()):
    """Categories accepted on save (hidden ones included)."""

    allowed = set(category_names(include_hidden=True))

    for name in extra:
        name = (name or "").strip()
        if name:
            allowed.add(name)

    return allowed


def category_usage():
    """{'Salud': 3, ...} with how many expenses use each category."""

    usage = {}

    for expense in read_csv(EXPENSES_FILE):

        name = (expense.get("category") or "").strip()

        if name:
            usage[name] = usage.get(name, 0) + 1

    return usage


# ============================================================
# INSTALLMENT PLANS
# ============================================================

def normalize_installments(value):
    """
    Return the number of payments as an int, or None when the field is
    empty or does not apply.
    """

    number = parse_int(value)

    if number is None or number <= 0:
        return None

    return min(number, MAX_INSTALLMENTS)


def payment_date(start_date, frequency, index):
    """Date of payment number 'index' (0 = the first one)."""

    if frequency == "yearly":
        return add_years(start_date, index)

    return add_months(start_date, index)


def final_payment_date(start_date, frequency, installments):
    """Date of the last payment. None when it does not apply."""

    if start_date is None or not installments:
        return None

    if frequency not in FREQUENCIES_WITH_INSTALLMENTS:
        return None

    try:
        return payment_date(start_date, frequency, installments - 1)
    except (ValueError, OverflowError):
        return None


def _payments_elapsed(start_date, frequency, installments, today):
    """How many payments are already behind us, before the current month."""

    elapsed = 0

    for index in range(installments):

        moment = payment_date(start_date, frequency, index)

        if (moment.year, moment.month) < (today.year, today.month):
            elapsed += 1

    return elapsed


def installment_info(expense, today=None, current_month_status=""):
    """
    Summary of an expense paid in installments.

    Payments made are counted by date (the months already gone). When
    this month's payment is already marked as paid, it counts too.

    Returns None when the expense is not paid in installments.
    """

    installments = normalize_installments(expense.get("installments"))

    if not installments:
        return None

    frequency = normalize_frequency(expense.get("frequency"))

    if frequency not in FREQUENCIES_WITH_INSTALLMENTS:
        return None

    start_date = parse_date(expense.get("start_date"))

    if start_date is None:
        return None

    today = today or date.today()

    last_date = final_payment_date(start_date, frequency, installments)

    paid = _payments_elapsed(start_date, frequency, installments, today)

    # This month's payment counts once it is marked as paid.
    if (
        current_month_status == "paid"
        and paid < installments
        and applies_to_month(expense, today.month, today.year)
    ):
        paid += 1

    paid = max(0, min(paid, installments))

    remaining = installments - paid
    amount = to_amount(expense.get("amount"))

    return {
        "installments": installments,
        "paid": paid,
        "remaining": remaining,
        "amount": amount,
        "total": amount * installments,
        "paid_so_far": amount * paid,
        "balance": amount * remaining,
        "end_date": last_date.isoformat() if last_date else "",
        "percent": (paid / installments * 100) if installments else 0.0,
        "finished": remaining == 0,
    }


# ============================================================
# MONTHLY PAYMENT STATUS (planned vs. real)
# ============================================================

def period_key(month, year):
    """(10, 2026) -> '2026-10'"""

    return f"{int(year):04d}-{int(month):02d}"


def read_payments():
    return read_csv(PAYMENTS_FILE)


def write_payments(payments):
    write_csv(PAYMENTS_FILE, PAYMENT_FIELDS, payments)


def payment_entries(period):
    """
    {'6': {'status': 'paid', 'saved': 0.0}, ...} for one month.

    'saved' is how much has been put aside for that expense so far
    (partial payments, "abonos").
    """

    entries = {}

    for payment in read_payments():

        if (payment.get("period") or "").strip() != period:
            continue

        expense_id = (payment.get("expense_id") or "").strip()

        if not expense_id:
            continue

        entries[expense_id] = {
            "status": normalize_payment_status(payment.get("status")),
            "saved": max(0.0, to_amount(payment.get("saved"))),
        }

    return entries


def payment_statuses(period):
    """{'6': 'paid', '9': 'reserved', ...} for one month."""

    return {
        expense_id: entry["status"]
        for expense_id, entry in payment_entries(period).items()
    }


def _update_payment(expense_id, period, status=None, saved=None):
    """
    Create or update the payment row of an expense in one month.

    A row holding nothing worth remembering (pending and no money put
    aside) is dropped instead of stored, so the file does not grow for
    nothing.

    Returns the resulting row as a dict.
    """

    expense_id = str(expense_id).strip()

    current = {"status": "pending", "saved": 0.0}
    rest = []

    for payment in read_payments():

        same = (
            (payment.get("expense_id") or "").strip() == expense_id
            and (payment.get("period") or "").strip() == period
        )

        if same:
            current = {
                "status": normalize_payment_status(payment.get("status")),
                "saved": max(0.0, to_amount(payment.get("saved"))),
            }
        else:
            rest.append(payment)

    if status is not None:
        current["status"] = normalize_payment_status(status)

    if saved is not None:
        current["saved"] = max(0.0, to_amount(saved))

    if current["status"] != "pending" or current["saved"] > 0:
        rest.append(
            {
                "expense_id": expense_id,
                "period": period,
                "status": current["status"],
                "saved": f"{current['saved']:.2f}" if current["saved"] else "",
                "updated": date.today().isoformat(),
            }
        )

    write_payments(rest)

    return current


def set_payment_status(expense_id, period, status):
    """Mark an expense as pending, reserved or paid, keeping its abonos."""

    return _update_payment(expense_id, period, status=status)


def set_payment_saved(expense_id, period, saved, limit=None):
    """
    Set how much has been put aside for an expense this month.

    The amount is clamped between 0 and 'limit' (the expense amount),
    and once the whole amount is gathered the expense is marked as
    reserved on its own.
    """

    saved = max(0.0, to_amount(saved))

    if limit is not None and limit > 0:
        saved = min(saved, limit)

    status = None

    if limit is not None and limit > 0 and saved >= limit:
        status = "reserved"

    return _update_payment(expense_id, period, status=status, saved=saved)


def add_payment_saved(expense_id, period, amount, limit=None):
    """
    Add an abono to what is already put aside (a negative amount
    corrects a mistake). Returns the resulting row.
    """

    current = payment_entries(period).get(str(expense_id).strip(), {})

    return set_payment_saved(
        expense_id,
        period,
        current.get("saved", 0.0) + to_amount(amount),
        limit
    )


def clear_payments(expense_id):
    """Drop the payment history of a deleted expense."""

    expense_id = str(expense_id).strip()

    payments = [
        payment
        for payment in read_payments()
        if (payment.get("expense_id") or "").strip() != expense_id
    ]

    write_payments(payments)


# ============================================================
# DOES IT APPLY TO THIS MONTH? (same rule for expenses and income)
# ============================================================

def is_active(record):
    return str(record.get("active", "")).strip().lower() == "true"


def applies_to_month(record, month, year):
    """
    Decide whether an expense or income should be counted in a month.

    - Inactive: never.
    - Before the start month or after the end month: no.
    - Monthly: every month.
    - Yearly: only in the month of the start date.
    - One time: only in the month and year of the start date.
    """

    if not is_active(record):
        return False

    start_date = parse_date(record.get("start_date"))

    if start_date is None:
        return False

    first_of_month = date(year, month, 1)

    if first_of_month < start_date.replace(day=1):
        return False

    end_date = parse_date(record.get("end_date"))

    if end_date is not None and first_of_month > end_date.replace(day=1):
        return False

    frequency = normalize_frequency(record.get("frequency"))

    if frequency == "monthly":
        return True

    if frequency == "yearly":
        return month == start_date.month

    if frequency == "one_time":
        return month == start_date.month and year == start_date.year

    return False


# ============================================================
# FORM VALIDATION
# ============================================================

def validate_entry(values, *, is_expense, extra_categories=()):
    """
    Validate the data of an expense or an income.

    Returns (clean_data, errors). When 'errors' is empty, 'clean_data'
    is ready to be stored.

    'extra_categories' keeps an old category that is no longer in the
    catalog (for example one typed by hand in the CSV).

    Error messages are in Spanish because the user reads them.
    """

    errors = []

    # ---- concept -------------------------------------------------
    concept = (values.get("concept") or "").strip()

    if not concept:
        errors.append("El concepto es obligatorio.")
    elif len(concept) > 120:
        errors.append("El concepto no puede pasar de 120 caracteres.")

    # ---- amount --------------------------------------------------
    amount = parse_amount(values.get("amount"))

    if amount is None or amount <= 0:
        errors.append("El monto debe ser un número mayor que 0.")

    # ---- frequency -----------------------------------------------
    frequency = normalize_frequency(values.get("frequency"))

    if not frequency:
        errors.append("Selecciona una frecuencia válida.")

    # ---- dates ---------------------------------------------------
    start_date = parse_date(values.get("start_date"))

    if start_date is None:
        errors.append(
            "La fecha de inicio es obligatoria y debe ser válida."
        )
    elif not MIN_YEAR <= start_date.year <= MAX_YEAR:
        errors.append(
            f"El año de inicio debe estar entre {MIN_YEAR} y {MAX_YEAR}."
        )

    end_text = (values.get("end_date") or "").strip()
    end_date = None

    if end_text:
        end_date = parse_date(end_text)

        if end_date is None:
            errors.append("La fecha de finalización no es válida.")

        elif start_date and end_date < start_date:
            errors.append(
                "La fecha de finalización no puede ser "
                "anterior a la fecha de inicio."
            )

    # ---- notes ---------------------------------------------------
    notes = (values.get("notes") or "").strip()

    if len(notes) > 500:
        errors.append("Las notas no pueden pasar de 500 caracteres.")

    data = {
        "concept": concept,
        "amount": f"{amount:.2f}" if amount is not None else "",
        "frequency": frequency,
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "notes": notes,
    }

    # ---- expenses only: category, type and installments ----------
    if is_expense:

        category = (values.get("category") or "").strip()

        if category not in allowed_categories(extra_categories):
            errors.append("Selecciona una categoría válida.")

        expense_type = normalize_expense_type(values.get("type"))

        if not expense_type:
            errors.append("Selecciona un tipo de gasto válido.")

        data["category"] = category
        data["type"] = expense_type

        # ---- number of payments ----------------------------------
        installments_text = (values.get("installments") or "").strip()
        installments = None

        if installments_text:

            installments = parse_int(installments_text)

            if installments is None or installments < 1:
                errors.append(
                    "El número de pagos debe ser un entero mayor que 0."
                )
                installments = None

            elif installments > MAX_INSTALLMENTS:
                errors.append(
                    f"El número de pagos no puede pasar de {MAX_INSTALLMENTS}."
                )
                installments = None

            elif frequency not in FREQUENCIES_WITH_INSTALLMENTS:
                errors.append(
                    "El número de pagos solo aplica a gastos "
                    "mensuales o anuales."
                )
                installments = None

        data["installments"] = str(installments) if installments else ""

        # With installments the app owns the end date.
        if installments and start_date:

            computed = final_payment_date(start_date, frequency, installments)

            if computed is None or computed.year > MAX_YEAR:
                errors.append(
                    "Con ese número de pagos la fecha final "
                    "queda fuera de rango."
                )
            else:
                data["end_date"] = computed.isoformat()

    return data, errors


# ============================================================
# JINJA FILTERS
# ============================================================

def money_mxn(value):
    """1234.5 -> $1,234.50   |   -1234.5 -> -$1,234.50"""

    number = round(to_amount(value), 2)
    text = f"${abs(number):,.2f}"

    return f"-{text}" if number < 0 else text


def percent(value):
    """12.345 -> 12.3%"""

    return f"{to_amount(value):,.1f}%"


def date_mx(value):
    """2026-09-20 -> 20/09/2026"""

    moment = parse_date(value)

    if moment is None:
        return value or ""

    return moment.strftime("%d/%m/%Y")


def month_year(value):
    """2027-03-01 -> Marzo 2027"""

    moment = parse_date(value)

    if moment is None:
        return value or ""

    return f"{MONTH_NAMES[moment.month]} {moment.year}"


def frequency_label(value):
    """monthly -> Mensual"""

    return FREQUENCY_LABELS.get(normalize_frequency(value), value or "")


def expense_type_label(value):
    """fixed -> Gasto fijo"""

    return EXPENSE_TYPE_LABELS.get(
        normalize_expense_type(value),
        value or ""
    )


def payment_status_label(value):
    """paid -> Pagado"""

    return PAYMENT_STATUS_LABELS.get(
        normalize_payment_status(value),
        "Falta por juntar"
    )


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.filters.update(
    {
        "mxn": money_mxn,
        "pct": percent,
        "date_mx": date_mx,
        "month_year": month_year,
        "frequency_label": frequency_label,
        "expense_type_label": expense_type_label,
        "payment_status_label": payment_status_label,
    }
)

templates.env.globals.update(
    {
        "category_options": category_options,
        "EXPENSE_TYPES": EXPENSE_TYPES,
        "FREQUENCIES": FREQUENCIES,
        "PAYMENT_STATUSES": PAYMENT_STATUSES,
        "MONTHS": MONTHS,
        "MIN_YEAR": MIN_YEAR,
        "MAX_YEAR": MAX_YEAR,
        "MAX_INSTALLMENTS": MAX_INSTALLMENTS,
    }
)


def render(request, name, context=None, status_code=200):
    """Shortcut to return a template."""

    return templates.TemplateResponse(
        request=request,
        name=name,
        context=context or {},
        status_code=status_code,
    )


ensure_files()
