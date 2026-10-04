// ============================================================
// CONTROL DE GASTOS
// General JavaScript (loaded on every page)
// ============================================================

(function () {

    "use strict";


    // ========================================================
    // LIGHT / DARK THEME
    // The "dark-mode" class lives on <html>. The inline script in
    // base.html applies it before painting to avoid the flash, so
    // here we only handle the button.
    // ========================================================

    var THEME_KEY = "theme";

    function saveTheme(value) {
        try {
            localStorage.setItem(THEME_KEY, value);
        } catch (error) {
            // If the browser blocks localStorage the theme simply is
            // not remembered between visits.
        }
    }

    function isDark() {
        return document.documentElement.classList.contains("dark-mode");
    }

    function updateThemeButton() {

        var icon = document.querySelector("[data-theme-icon]");
        var label = document.querySelector("[data-theme-label]");

        if (icon) {
            icon.textContent = isDark() ? "☀️" : "🌙";
        }

        if (label) {
            label.textContent = isDark() ? "Modo claro" : "Modo oscuro";
        }

    }

    function setUpTheme() {

        var button = document.getElementById("themeToggle");

        updateThemeButton();

        if (!button) {
            return;
        }

        button.addEventListener("click", function () {

            document.documentElement.classList.toggle("dark-mode");

            saveTheme(isDark() ? "dark" : "light");

            updateThemeButton();

            // Lets the charts redraw with the new colors
            document.dispatchEvent(
                new CustomEvent("themechange", {
                    detail: { dark: isDark() }
                })
            );

        });

    }


    // ========================================================
    // CONFIRM BEFORE DELETING
    // Any <form data-confirm="message"> asks for confirmation, and so
    // does a single <button data-confirm="message"> inside a form that
    // does other things too.
    // ========================================================

    function setUpConfirmations() {

        document
            .querySelectorAll("form[data-confirm]")
            .forEach(function (form) {

                form.addEventListener("submit", function (event) {

                    if (!window.confirm(form.dataset.confirm)) {
                        event.preventDefault();
                    }

                });

            });

        document
            .querySelectorAll("button[data-confirm]")
            .forEach(function (button) {

                button.addEventListener("click", function (event) {

                    if (!window.confirm(button.dataset.confirm)) {
                        event.preventDefault();
                    }

                });

            });

    }


    // ========================================================
    // PREVENT DOUBLE SUBMIT
    // POST forms only (add / edit / delete).
    // ========================================================

    function setUpSingleSubmit() {

        document.querySelectorAll("form").forEach(function (form) {

            if (form.method.toLowerCase() !== "post") {
                return;
            }

            form.addEventListener("submit", function (event) {

                var button = form.querySelector('button[type="submit"]');

                if (!button) {
                    return;
                }

                // Checked after the other handlers have run: if the user
                // cancelled the confirmation, nothing gets blocked.
                setTimeout(function () {

                    if (event.defaultPrevented) {
                        return;
                    }

                    button.disabled = true;
                    button.dataset.locked = "1";

                }, 0);

            });

        });

        // Going back with the browser button can restore the page with
        // the submit button still disabled.
        window.addEventListener("pageshow", function (event) {

            if (!event.persisted) {
                return;
            }

            document
                .querySelectorAll("button[data-locked]")
                .forEach(function (button) {
                    button.disabled = false;
                    delete button.dataset.locked;
                });

        });

    }


    // ========================================================
    // MONTH PICKER (dashboard)
    // Changing the month or the year reloads the dashboard.
    // ========================================================

    function setUpMonthPicker() {

        var month = document.getElementById("month");
        var year = document.getElementById("year");

        [month, year].forEach(function (field) {

            if (!field || !field.form) {
                return;
            }

            field.addEventListener("change", function () {

                if (field.checkValidity()) {
                    field.form.submit();
                }

            });

        });

    }


    // ========================================================
    // DATES: the end date cannot be before the start date
    // ========================================================

    function setUpDates() {

        var start = document.getElementById("start_date");
        var end = document.getElementById("end_date");

        if (!start || !end) {
            return;
        }

        function sync() {
            end.min = start.value || "";
        }

        start.addEventListener("change", sync);

        sync();

    }


    // ========================================================
    // INSTALLMENTS
    // Typing the number of payments fills in the end date
    // (the server computes it again on save).
    // ========================================================

    var MONTH_NAMES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];

    function twoDigits(number) {
        return (number < 10 ? "0" : "") + number;
    }

    function setUpInstallments() {

        var installments = document.getElementById("installments");
        var start = document.getElementById("start_date");
        var end = document.getElementById("end_date");
        var frequency = document.getElementById("frequency");

        if (!installments || !start || !end || !frequency) {
            return;
        }

        var hint = document.querySelector("[data-installments-hint]");
        var endHint = document.querySelector("[data-end-date-hint]");

        var defaultHint = hint ? hint.innerHTML : "";

        function refresh() {

            var total = parseInt(installments.value, 10);

            var hasPlan = (
                total > 0
                && (frequency.value === "monthly" || frequency.value === "yearly")
            );

            end.readOnly = hasPlan;
            end.classList.toggle("is-calculated", hasPlan);

            if (endHint) {
                endHint.hidden = !hasPlan;
            }

            if (!hasPlan) {

                if (hint) {
                    hint.innerHTML = defaultHint;
                }

                return;
            }

            var parts = (start.value || "").split("-");

            if (parts.length !== 3) {
                return;
            }

            var year = parseInt(parts[0], 10);
            var month = parseInt(parts[1], 10);
            var day = parseInt(parts[2], 10);

            if (!year || !month || !day) {
                return;
            }

            var steps = (frequency.value === "yearly")
                ? (total - 1) * 12
                : (total - 1);

            var months = (month - 1) + steps;

            var endYear = year + Math.floor(months / 12);
            var endMonth = (months % 12) + 1;

            var lastDay = new Date(endYear, endMonth, 0).getDate();
            var endDay = Math.min(day, lastDay);

            end.value = (
                endYear + "-" + twoDigits(endMonth) + "-" + twoDigits(endDay)
            );

            if (hint) {
                hint.textContent = (
                    "Son " + total + " pagos: el último cae en "
                    + MONTH_NAMES[endMonth - 1] + " " + endYear + "."
                );
            }

        }

        [installments, start, frequency].forEach(function (field) {
            field.addEventListener("change", refresh);
            field.addEventListener("input", refresh);
        });

        refresh();

    }


    // ========================================================
    // MOVEMENT KIND (Movimientos tab)
    // The kind is not a choice: it follows the state of the expense.
    // This only previews what the server will store.
    // ========================================================

    function setUpMovementKind() {

        var expense = document.getElementById("expense_id");
        var preview = document.querySelector("[data-movement-kind]");

        if (!expense || !preview) {
            return;
        }

        function refresh() {

            var option = expense.options[expense.selectedIndex];
            var kind = option ? option.dataset.kind : "";

            if (!kind) {
                preview.innerHTML = '<span class="text-light">Elige un gasto</span>';
                return;
            }

            preview.innerHTML = (
                '<span class="movement-kind movement-kind--' + kind + '">'
                + option.dataset.kindLabel
                + "</span> "
                + '<span class="text-light">porque está en «'
                + option.dataset.statusLabel
                + '»</span>'
            );

        }

        expense.addEventListener("change", refresh);

        refresh();

    }


    // ========================================================
    // UTILITIES
    // ========================================================

    function formatMoney(value) {

        var number = Number(value);

        if (Number.isNaN(number)) {
            number = 0;
        }

        return number.toLocaleString("es-MX", {
            style: "currency",
            currency: "MXN"
        });

    }

    window.formatMoney = formatMoney;


    // ========================================================
    // START
    // ========================================================

    document.addEventListener("DOMContentLoaded", function () {

        setUpTheme();
        setUpConfirmations();
        setUpSingleSubmit();
        setUpMonthPicker();
        setUpDates();
        setUpInstallments();
        setUpMovementKind();

    });

})();
