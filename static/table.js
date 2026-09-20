// ============================================================
// CONTROL DE GASTOS
// Tables: search, filters and sorting by column
//
// How the HTML wires it up:
//
//   <div data-table-toolbar="expenses">
//       <input data-table-search>
//       <select data-table-filter="category">
//       <button data-table-clear>
//       <span data-table-count></span>
//   </div>
//
//   <table data-table="expenses">
//       <thead><tr><th data-sort="text">…</th></tr></thead>
//       <tbody>
//           <tr data-category="Salud" data-search="text to match">
//               <td data-value="1300">$1,300.00</td>
// ============================================================

(function () {

    "use strict";


    function normalize(text) {

        return (text || "")
            .toString()
            .toLowerCase()
            .normalize("NFD")
            .replace(/[̀-ͯ]/g, "");

    }


    function cellValue(row, index) {

        var cell = row.children[index];

        if (!cell) {
            return "";
        }

        return cell.dataset.value !== undefined
            ? cell.dataset.value
            : cell.textContent;

    }


    function setUpTable(table) {

        var name = table.dataset.table;

        var body = table.tBodies[0];

        if (!body) {
            return;
        }

        var toolbar = document.querySelector(
            '[data-table-toolbar="' + name + '"]'
        );

        var search = toolbar
            ? toolbar.querySelector("[data-table-search]")
            : null;

        var filters = toolbar
            ? Array.prototype.slice.call(
                toolbar.querySelectorAll("[data-table-filter]")
            )
            : [];

        var counter = toolbar
            ? toolbar.querySelector("[data-table-count]")
            : null;

        var clear = toolbar
            ? toolbar.querySelector("[data-table-clear]")
            : null;

        var emptyState = document.querySelector(
            '[data-table-empty="' + name + '"]'
        );

        // The searchable text is normalized once, up front.
        var rows = Array.prototype.slice.call(body.rows);

        rows.forEach(function (row) {
            row.dataset.searchNormalized = normalize(
                row.dataset.search || row.textContent
            );
        });


        // ----------------------------------------------------
        // FILTER
        // ----------------------------------------------------

        function applyFilters() {

            var text = normalize(search ? search.value : "");

            var visible = 0;

            rows.forEach(function (row) {

                var matches = true;

                if (text && row.dataset.searchNormalized.indexOf(text) === -1) {
                    matches = false;
                }

                if (matches) {

                    filters.some(function (filter) {

                        var field = filter.dataset.tableFilter;
                        var expected = filter.value;

                        if (expected && (row.dataset[field] || "") !== expected) {
                            matches = false;
                            return true;
                        }

                        return false;

                    });

                }

                row.hidden = !matches;

                if (matches) {
                    visible += 1;
                }

            });

            if (counter) {
                counter.textContent = (
                    visible === rows.length
                        ? rows.length + (rows.length === 1 ? " registro" : " registros")
                        : visible + " de " + rows.length
                );
            }

            if (emptyState) {
                emptyState.hidden = visible !== 0 || rows.length === 0;
            }

        }


        // ----------------------------------------------------
        // SORT
        // ----------------------------------------------------

        function sortBy(header) {

            var index = Array.prototype.indexOf.call(
                header.parentNode.children,
                header
            );

            var kind = header.dataset.sort;

            var descending = header.dataset.sortActive === "asc";

            table.querySelectorAll("th[data-sort]").forEach(function (th) {
                delete th.dataset.sortActive;
                th.setAttribute("aria-sort", "none");
            });

            header.dataset.sortActive = descending ? "desc" : "asc";

            header.setAttribute(
                "aria-sort",
                descending ? "descending" : "ascending"
            );

            var sorted = rows.slice().sort(function (a, b) {

                var left = cellValue(a, index);
                var right = cellValue(b, index);

                var result;

                if (kind === "number" || kind === "date") {

                    var leftNumber = kind === "number"
                        ? parseFloat(left)
                        : Date.parse(left);

                    var rightNumber = kind === "number"
                        ? parseFloat(right)
                        : Date.parse(right);

                    leftNumber = isNaN(leftNumber) ? -Infinity : leftNumber;
                    rightNumber = isNaN(rightNumber) ? -Infinity : rightNumber;

                    result = leftNumber - rightNumber;

                } else {

                    result = normalize(left).localeCompare(normalize(right));

                }

                return descending ? -result : result;

            });

            sorted.forEach(function (row) {
                body.appendChild(row);
            });

        }


        // ----------------------------------------------------
        // EVENTS
        // ----------------------------------------------------

        if (search) {
            search.addEventListener("input", applyFilters);
        }

        filters.forEach(function (filter) {
            filter.addEventListener("change", applyFilters);
        });

        if (clear) {

            clear.addEventListener("click", function () {

                if (search) {
                    search.value = "";
                }

                filters.forEach(function (filter) {
                    filter.value = "";
                });

                applyFilters();

            });

        }

        table.querySelectorAll("th[data-sort]").forEach(function (th) {

            th.classList.add("th-sortable");
            th.setAttribute("role", "button");
            th.setAttribute("tabindex", "0");
            th.setAttribute("aria-sort", "none");

            th.addEventListener("click", function () {
                sortBy(th);
            });

            th.addEventListener("keydown", function (event) {

                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    sortBy(th);
                }

            });

        });

        applyFilters();

    }


    document.addEventListener("DOMContentLoaded", function () {

        document.querySelectorAll("table[data-table]").forEach(setUpTable);

    });

})();
