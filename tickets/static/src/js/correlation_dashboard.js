/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, onMounted, onWillStart, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

class CorrelationHeatmap extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: true, correlationData: {} });
        this.heatmapRef = useRef("heatmap");
        this.charts = {}; // To store chart instances

        onWillStart(async () => {
            // Load Chart.js + Plugins from CDN
            try {
                await loadJS("https://cdn.jsdelivr.net/npm/chart.js");
                await loadJS("https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels");
                await loadJS("https://cdn.jsdelivr.net/npm/chartjs-chart-matrix/dist/chartjs-chart-matrix.min.js");

                // Register datalabels plugin if it's loaded and not already registered
                if (window.Chart && window.ChartDataLabels && !Chart.registry.plugins.get("datalabels")) {
                    Chart.register(window.ChartDataLabels);
                }
            } catch (e) {
                console.error("Failed to load Chart.js libraries from CDN:", e);
                this.state.error = "Failed to load charting libraries. Please check internet connection.";
            }

            // Fetch correlation data only if libraries loaded
            if (!this.state.error) {
                try {
                    const rawCorrData = await this.orm.call("eda.correlation", "get_latest_correlation_data", [], {});
                    if (rawCorrData && Object.keys(rawCorrData).length) {
                        this.state.correlationData = rawCorrData;
                    } else {
                        console.warn("No correlation data returned from server.");
                    }
                } catch (error) {
                    console.error("Error fetching correlation data:", error);
                    this.state.error = "Failed to fetch correlation data from server.";
                }
            }
            
            this.state.loading = false; // Mark loading as complete
        });

        onMounted(() => {
            // Render heatmap after component is mounted
            // Use setTimeout to ensure canvas is ready
            setTimeout(() => {
                if (!this.state.loading && !this.state.error && Object.keys(this.state.correlationData).length) {
                    this.renderHeatmap();
                }
            }, 100); // 100ms delay
        });
    }

    /**
     * Renders the Chart.js heatmap (matrix chart)
     */
    renderHeatmap() {
        const rawCorrData = this.state.correlationData;
        if (!rawCorrData || !Object.keys(rawCorrData).length || !this.heatmapRef?.el) {
            console.warn("renderHeatmap skipped: No data or canvas element not found.");
            return;
        }
        if (typeof Chart === 'undefined' || typeof ChartDataLabels === 'undefined') {
            console.error("renderHeatmap skipped: Chart.js or Datalabels plugin not loaded.");
            return;
        }

        const ref = this.heatmapRef;
        const title = "Matriks Korelasi EDA (Pearson)";
        
        // Destroy existing chart if it exists
        if (this.charts[title]) {
            try { this.charts[title].destroy(); } catch (e) {
                console.error("Error destroying previous chart:", e);
            }
            delete this.charts[title];
        }

        // --- Data Preparation ---
        const labels = ["Ticket Count", "Priority", "Complexity", "Response", "Resolution", "Rating", "Point"];
        const simple = ['ticket', 'priority', 'complexity', 'response', 'resolution', 'rating', 'point'];
        const flatData = [];

        // Loop to create flat data structure {x, y, v}
        for (let i = 0; i < simple.length; i++) {
            for (let j = 0; j < simple.length; j++) {
                let val = 1.0;
                if (i !== j) {
                    // Check for both key directions (e.g., corr_a_b or corr_b_a)
                    const direct = `corr_${simple[i]}_${simple[j]}`;
                    const reverse = `corr_${simple[j]}_${simple[i]}`;
                    val = rawCorrData[direct] ?? rawCorrData[reverse] ?? 0.0;
                }
                flatData.push({ x: labels[j], y: labels[i], v: Number(val) });
            }
        }

        // --- Color Helper Function ---
        const getHeatmapColor = (v) => {
            const val = Math.max(-1, Math.min(1, Number(v) || 0));
            if (val === 0) return "rgb(255,255,255)"; // White for 0
            if (val > 0) { // Positive: Shades of Green/Blue (Cool)
                const g = Math.round(255 - (255 - 153) * val);
                const r = Math.round(255 - (255 - 0) * val);
                const b = Math.round(255 - (255 - 102) * val);
                return `rgb(${r},${g},${b})`;
            } else { // Negative: Shades of Red (Hot)
                const t = Math.abs(val);
                const r = Math.round(255 - (255 - 244) * t);
                const g = Math.round(255 - (255 - 67) * t);
                const b = Math.round(255 - (255 - 54) * t);
                return `rgb(${r},${g},${b})`;
            }
        };

        // --- Draw Chart ---
        setTimeout(() => {
            try {
                this.charts[title] = new Chart(ref.el.getContext("2d"), {
                    type: "matrix", // Requires chartjs-chart-matrix.min.js
                    plugins: [ChartDataLabels], // Requires chartjs-plugin-datalabels
                    data: {
                        datasets: [{
                            label: "Correlation Matrix",
                            data: flatData,
                            backgroundColor: ctx => getHeatmapColor(ctx.raw?.v ?? 0), // Safety check ctx.raw.v
                            borderColor: "rgba(0,0,0,0.15)",
                            borderWidth: 1,
                            width: ({chart}) => (chart.chartArea?.width / labels.length) - 2,
                            height: ({chart}) => (chart.chartArea?.height / labels.length) - 2,
                            
                            // ===================================
                            // PERBAIKAN FINAL DI SINI
                            // ===================================
                            datalabels: {
                                color: (ctx) => {
                                    // Akses 'v' dengan aman dari 'ctx.raw'
                                    const val = ctx.raw ? ctx.raw.v : 0;
                                    return Math.abs(val) > 0.45 ? "#fff" : "#000";
                                },
                                formatter: (value, ctx) => {
                                    // 'value' tidak bisa diandalkan, gunakan 'ctx.raw.v' dengan aman
                                    if (ctx.raw && typeof ctx.raw.v === 'number') {
                                        return ctx.raw.v.toFixed(3);
                                    }
                                    return ''; // Kembalikan string kosong jika data tidak valid
                                },
                                font: { weight: "bold", size: 9 }
                            }
                            // ===================================

                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        parsing: { xAxisKey: "x", yAxisKey: "y", valueAxisKey: "v" }, // Map keys
                        scales: {
                            x: {
                                type: "category",
                                labels: labels,
                                position: "top",
                                offset: true,
                                grid: { display: false },
                                ticks: { font: { size: 11 }, color: "#444" }
                            },
                            y: {
                                type: "category",
                                labels: labels,
                                reverse: false, // Keep y-axis top-to-bottom
                                offset: true,
                                grid: { display: false },
                                ticks: { font: { size: 11 }, color: "#444" }
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    title: (items) => `${items[0].raw.y} vs ${items[0].raw.x}`,
                                    label: (item) => `r = ${item.raw.v.toFixed(3)}`
                                },
                                backgroundColor: "rgba(0,0,0,0.8)",
                                titleFont: { weight: 'bold', size: 13 },
                                bodyFont: { size: 12 },
                                displayColors: false,
                                padding: 8
                            },
                            title: { display: true, text: title, font: { size: 14, weight: "bold" } },
                            datalabels: { display: true } // Ensure plugin is enabled
                        }
                    }
                });
            } catch (err) {
                console.error("Error rendering correlation heatmap:", err);
                this.state.error = "Error rendering chart. See console for details.";
            }
        }, 200); // Delay for canvas readiness
    }

    /**
     * Getter for building correlation table data for the template
     */
    get correlationTableData() {
        const raw = this.state.correlationData;
        if (!raw || !Object.keys(raw).length) return [];
        
        const labels = ["Ticket Count", "Priority", "Complexity", "Response", "Resolution", "Rating", "Point"];
        const simple = ['ticket', 'priority', 'complexity', 'response', 'resolution', 'rating', 'point'];

        return simple.map((y, i) => ({
            label: labels[i],
            values: simple.map((x, j) => {
                if (i === j) return 1.0;
                const key = `corr_${y}_${x}`;
                const rev = `corr_${x}_${y}`;
                return raw[key] ?? raw[rev] ?? 0.0;
            })
        }));
    }
}

/**
 * Embedded XML Template
 */
CorrelationHeatmap.template = xml/* xml */`
<div class="o_correlation_dashboard" style="padding:20px; background:#f8f9fa; height:100vh; overflow-y:auto;">
    <h2 style="text-align:center; color:#875A7B;">📈 Analisis Korelasi Matriks (Heatmap)</h2>

    <div t-if="state.loading" style="text-align:center; padding:40px;">
        <i class="fa fa-spinner fa-spin fa-2x"/> Loading data...
    </div>

    <div t-if="state.error &amp;&amp; !state.loading" class="alert alert-danger" style="padding:20px;">
        <strong>Error:</strong> <t t-esc="state.error"/>
    </div>

    <div t-elif="!state.correlationData || !Object.keys(state.correlationData).length &amp;&amp; !state.loading" class="alert alert-warning" style="padding:20px;">
        Tidak ada data korelasi yang ditemukan. Jalankan perhitungan terlebih dahulu.
    </div>

    <div t-else="">
        <div style="margin-top:20px; background:white; padding:15px; border-radius:8px; box-shadow:0 2px 6px rgba(0,0,0,0.1);">
            <canvas t-ref="heatmap" style="width:100%; height:600px;"></canvas>
        </div>

        <div t-if="correlationTableData.length" style="margin-top:40px;">
            <h4 style="text-align:center; color:#444;">📋 Tabel Nilai Korelasi (Pearson r)</h4>
            <div style="overflow-x:auto;">
                <table class="table table-bordered table-striped" style="font-size:13px; text-align:center; min-width: 600px; background: white;">
                    <thead style="background:#875A7B; color:white;">
                        <tr>
                            <th style="min-width: 100px;">Variable</th>
                            <t t-foreach="correlationTableData" t-as="col" t-key="col.label">
                                <th style="min-width: 90px;"><t t-esc="col.label"/></th>
                            </t>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-foreach="correlationTableData" t-as="row" t-key="row.label">
                            <tr>
                                <td style="font-weight:bold; background-color: #f8f9fa;"><t t-esc="row.label"/></td>
                                <t t-foreach="row.values" t-as="val" t-key="val_index">
                                    <td><t t-esc="val.toFixed(3)"/></td>
                                </t>
                            </tr>
                        </t>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
`;

// Register the component as a client action
registry.category("actions").add("tickets.correlation_heatmap_action", CorrelationHeatmap);