// ============================================================
// CONTROL DE GASTOS
// Dashboard charts (Chart.js)
//
// The data comes from Python inside:
//   <script type="application/json" id="chart-data">
// ============================================================

(function () {

    "use strict";

    var dataElement = document.getElementById("chart-data");

    if (!dataElement) {
        return;
    }

    // When Chart.js did not load (no internet, for example) say so
    // instead of leaving empty boxes behind.
    if (typeof Chart === "undefined") {

        document.querySelectorAll(".chart-box").forEach(function (box) {
            box.innerHTML =
                '<p class="chart-error">' +
                "No se pudo cargar Chart.js. Revisa tu conexión a internet." +
                "</p>";
        });

        return;
    }

    var data = JSON.parse(dataElement.textContent);

    var moneyFormat = new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: "MXN"
    });

    var PALETTE = [
        "#2563eb", "#16a34a", "#d97706", "#dc2626",
        "#7c3aed", "#0891b2", "#db2777", "#65a30d",
        "#ea580c", "#475569", "#0d9488", "#a16207"
    ];

    var charts = [];


    // ========================================================
    // COLORS (read from the CSS so dark mode is respected)
    // ========================================================

    function cssVariable(name) {
        return getComputedStyle(document.documentElement)
            .getPropertyValue(name)
            .trim();
    }

    function applyBaseStyle() {

        Chart.defaults.color = cssVariable("--text-secondary");
        Chart.defaults.borderColor = cssVariable("--border");
        Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;

    }

    function axisFormat(value) {
        return "$" + Number(value).toLocaleString("es-MX");
    }


    // ========================================================
    // SPENDING BY CATEGORY (doughnut)
    // ========================================================

    function createCategoriesChart() {

        var canvas = document.getElementById("categoriesChart");

        if (!canvas || data.categories.length === 0) {
            return;
        }

        var total = data.categories.reduce(function (sum, item) {
            return sum + item.amount;
        }, 0);

        return new Chart(canvas, {

            type: "doughnut",

            data: {
                labels: data.categories.map(function (item) {
                    return item.category;
                }),
                datasets: [{
                    data: data.categories.map(function (item) {
                        return item.amount;
                    }),
                    backgroundColor: data.categories.map(function (_, index) {
                        return PALETTE[index % PALETTE.length];
                    }),
                    borderColor: cssVariable("--surface"),
                    borderWidth: 2
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "58%",

                plugins: {
                    legend: {
                        position: window.innerWidth < 600 ? "bottom" : "right"
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {

                                var percent = total > 0
                                    ? (context.parsed / total * 100).toFixed(1)
                                    : "0.0";

                                return " " + context.label + ": " +
                                    moneyFormat.format(context.parsed) +
                                    " (" + percent + "%)";
                            }
                        }
                    }
                }
            }

        });

    }


    // ========================================================
    // INCOME VS. EXPENSES (bars)
    // ========================================================

    function createIncomeExpensesChart() {

        var canvas = document.getElementById("incomeExpensesChart");

        if (!canvas) {
            return;
        }

        return new Chart(canvas, {

            type: "bar",

            data: {
                labels: ["Ingresos", "Gastos"],
                datasets: [{
                    data: [
                        data.income_vs_expenses.income,
                        data.income_vs_expenses.expenses
                    ],
                    backgroundColor: [
                        cssVariable("--success"),
                        cssVariable("--danger")
                    ],
                    borderRadius: 6,
                    maxBarThickness: 90
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return " " + moneyFormat.format(context.parsed.y);
                            }
                        }
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: axisFormat }
                    }
                }
            }

        });

    }


    // ========================================================
    // MONTHLY TREND (lines)
    // ========================================================

    function createTrendChart() {

        var canvas = document.getElementById("trendChart");

        if (!canvas || data.trend.length === 0) {
            return;
        }

        function series(label, field, color, dashed) {
            return {
                label: label,
                data: data.trend.map(function (item) {
                    return item[field];
                }),
                borderColor: color,
                backgroundColor: color,
                borderDash: dashed ? [6, 4] : [],
                tension: 0.3,
                fill: false,
                pointRadius: 3,
                pointHoverRadius: 5
            };
        }

        return new Chart(canvas, {

            type: "line",

            data: {
                // "Enero" -> "Ene"
                labels: data.trend.map(function (item) {
                    return item.month.slice(0, 3);
                }),
                datasets: [
                    series("Ingresos", "income", cssVariable("--success"), false),
                    series("Gastos", "expenses", cssVariable("--danger"), false),
                    series("Disponible", "available", cssVariable("--primary"), true)
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    intersect: false,
                    mode: "index"
                },

                plugins: {
                    legend: { position: "top" },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return " " + context.dataset.label + ": " +
                                    moneyFormat.format(context.parsed.y);
                            }
                        }
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: axisFormat }
                    }
                }
            }

        });

    }


    // ========================================================
    // BUILD / REBUILD
    // ========================================================

    function buildCharts() {

        charts.forEach(function (chart) {
            chart.destroy();
        });

        charts = [];

        applyBaseStyle();

        [
            createCategoriesChart(),
            createIncomeExpensesChart(),
            createTrendChart()
        ].forEach(function (chart) {
            if (chart) {
                charts.push(chart);
            }
        });

    }

    buildCharts();

    // Switching between light and dark mode redraws them with the
    // colors of the new theme.
    document.addEventListener("themechange", buildCharts);

})();
