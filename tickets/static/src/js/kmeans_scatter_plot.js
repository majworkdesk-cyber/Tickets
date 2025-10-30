/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState, xml } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

// Feature list mirroring the Python definition
const FEATURE_SELECTION = [
    { id: 'norm_ticket_count', label: 'Z-Count' },
    { id: 'norm_priority', label: 'Z-Priority' },
    { id: 'norm_complexity', label: 'Z-Complexity' },
    { id: 'norm_response_time', label: 'Z-Response' },
    { id: 'norm_resolution_time', label: 'Z-Resolution' },
    { id: 'norm_rating', label: 'Z-Rating' },
    { id: 'norm_point', label: 'Z-Point' },
];
// Dictionary for easy label lookup
const FEATURE_DICT = Object.fromEntries(FEATURE_SELECTION.map(f => [f.id, f.label]));

// Owl Component for the Scatter Plot Client Action
export class KmeansScatterDashboard extends Component {
    setup() {
        console.log("KmeansScatterDashboard Props:", this.props); // Log props on setup
        console.log("Action Context received:", this.props.action?.context);

        this.orm = useService("orm");
        this.actionService = useService("action");
        this.chartRef = useRef("scatterChartCanvas");
        this.chartInstance = null;
        this.state = useState({
            loading: true,
            error: null,
            allResults: [], // Holds raw data fetched from kmeans.result
            plotData: null, // Holds data formatted for the *current* chart based on selection
            runInfo: { // Information passed from the triggering action's context
                runId: this.props.action?.context?.kmeans_run_id, // Get the ID of the K-Means run
                k: this.props.action?.context?.chosen_k, // Get the number of clusters used
                runName: this.props.action?.name, // Get the name of the action (e.g., "Scatter Plot - Run ...")
            },
            features: FEATURE_SELECTION, // Make features available to the template for dropdowns
            selectedXFeature: 'norm_point', // Default feature for the X-axis
            selectedYFeature: 'norm_rating', // Default feature for the Y-axis
        });

        console.log("Initial State set:", JSON.stringify(this.state.runInfo));
        // Early check for missing Run ID
        if (!this.state.runInfo.runId) {
             console.error(">>> KmeansScatterDashboard: runId IS MISSING FROM CONTEXT! Cannot load data. <<<", this.props.action?.context);
             this.state.error = "Missing K-Means Run ID. Cannot load data. Go back and ensure the run is saved.";
             this.state.loading = false; // Stop loading process
        }

        onWillStart(async () => {
            // Only proceed if runId was found in setup
            if (!this.state.error) {
                // Load Chart.js library asynchronously
                if (typeof Chart === 'undefined') {
                    try {
                        // Use Odoo's standard path if available, fallback to CDN if needed
                        await loadJS('/web/static/lib/Chart/Chart.js');
                    } catch (e) {
                        try { // Fallback CDN
                            console.warn("Could not load Chart.js locally, trying CDN...");
                            await loadJS('https://cdn.jsdelivr.net/npm/chart.js');
                        } catch (cdnError) {
                             this.state.error = "Failed to load Chart.js library.";
                             console.error(this.state.error, e, cdnError);
                        }
                    }
                }
                // Load cluster result data only if Chart.js loaded and still no error
                if (!this.state.error) {
                    await this.loadResultData();
                }
            }
            this.state.loading = false; // Mark loading as complete
        });

        onMounted(() => {
            // Wait a brief moment for the DOM to be fully stable after loading/rendering
            setTimeout(() => {
                if (!this.state.loading && !this.state.error && this.state.allResults.length > 0) {
                    console.log("onMounted: DOM should be ready, attempting initial renderChart().");
                    this.updatePlotData();
                    this.renderChart();
                } else {
                    console.log("onMounted: Skipping initial renderChart() due to loading/error/no data.");
                }
            }, 100); // 100ms delay
        });


        onWillUnmount(() => {
            // Clean up the chart instance when the component is destroyed
            this.destroyChart();
        });
    }

    /**
     * Loads ALL cluster results for the current K-Means run, including the record ID itself.
     */
    async loadResultData() {
        if (!this.state.runInfo.runId) {
             if (!this.state.error) { this.state.error = "Missing K-Means Run ID."; }
             console.error(this.state.error);
             return;
        }
        // Fetch 'id' along with other necessary fields
        const fieldsToFetch = ['id', 'cluster_id', 'customer_id'].concat(this.state.features.map(f => f.id));
        try {
            console.log(`Fetching kmeans.result for run_id: ${this.state.runInfo.runId} with fields:`, fieldsToFetch);
            const results = await this.orm.searchRead(
                'kmeans.result',
                [['run_id', '=', this.state.runInfo.runId]],
                fieldsToFetch,
                { order: 'id' } // Order by ID for consistency
            );
            console.log(`Fetched ${results.length} results. Example:`, results[0]);
            if (!results || results.length === 0) {
                this.state.error = `No cluster results found for K-Means Run ID ${this.state.runInfo.runId}. Run 'Step 2' first.`;
                return;
            }
            this.state.allResults = results;
             if (results.length > 0 && results[0].id === undefined) {
                 console.error(">>> id field was NOT fetched! <<<");
                 this.state.error = "Failed to fetch result record ID.";
             }
        } catch (e) {
            this.state.error = `Failed to load cluster results: ${e.message || e}`;
            console.error(this.state.error, e);
        }
    }

    /**
     * Prepares plotData including {x, y, cluster_id, resultId}.
     */
    updatePlotData() {
        if (!this.state.allResults.length) { this.state.plotData = null; return; }
        const xKey = this.state.selectedXFeature;
        const yKey = this.state.selectedYFeature;
        this.state.plotData = {
            points: this.state.allResults.map(r => ({
                x: r[xKey],
                y: r[yKey],
                cluster_id: r.cluster_id,
                resultId: r.id, // Store the ID of the kmeans.result record itself
                // Store Customer Name for tooltip
                customerName: r.customer_id ? r.customer_id[1] : 'Unknown Customer'
            })),
            xLabel: FEATURE_DICT[xKey] || xKey,
            yLabel: FEATURE_DICT[yKey] || yKey,
            clusterNames: [...new Set(this.state.allResults.map(r => r.cluster_id))].sort((a, b) => a - b).map(id => `Cluster ${id}`)
        };
        console.log("Plot data updated. Example point:", this.state.plotData.points[0]);
    }

    /**
     * Prepares Chart.js datasets. Point data includes resultId and customerName.
     */
     prepareChartJsData(plotData) {
        if (!plotData || !plotData.points || !plotData.clusterNames) return null;
        const datasets = [];
        const colors = ['rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)', 'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)', 'rgba(199, 199, 199, 0.7)', 'rgba(83, 102, 255, 0.7)', 'rgba(40, 167, 69, 0.7)', 'rgba(214, 51, 132, 0.7)'];
        plotData.clusterNames.forEach((name, index) => {
            const clusterId = parseInt(name.split(' ')[1]);
            // Keep the full point object {x, y, cluster_id, resultId, customerName}
            const pointsInCluster = plotData.points.filter(p => p.cluster_id === clusterId);
            if (pointsInCluster.length > 0) {
                datasets.push({
                    label: name,
                    data: pointsInCluster, // Pass the full point objects
                    backgroundColor: colors[index % colors.length],
                    pointRadius: 4, pointHoverRadius: 6,
                });
            }
        });
        return { datasets };
    }

    /**
     * Renders the Chart.js scatter plot, disabling datalabels.
     */
    renderChart() {
         if (!this.chartRef.el) {
            console.error("renderChart: Canvas element (this.chartRef.el) not found!");
            return;
         }
        if (typeof Chart === 'undefined' || !this.state.plotData) {
             console.warn("Chart rendering skipped. Pre-conditions not met.");
             this.destroyChart();
             const ctx = this.chartRef.el?.getContext('2d');
             if(ctx){ // Clear canvas message
                ctx.clearRect(0, 0, this.chartRef.el.width, this.chartRef.el.height);
                ctx.font = "14px sans-serif"; ctx.textAlign = 'center'; ctx.fillStyle = '#888';
                ctx.fillText('Select features or check data availability.', this.chartRef.el.width / 2, 40);
             }
            return;
        }
        this.destroyChart();
        const chartJsData = this.prepareChartJsData(this.state.plotData);
        if (!chartJsData) { this.state.error = "Failed to prepare data structure for Chart.js."; return; }

        const ctx = this.chartRef.el.getContext('2d');
        try {
            console.log("Rendering Chart.js scatter plot...");
            this.chartInstance = new Chart(ctx, {
                type: 'scatter', data: chartJsData,
                options: {
                    responsive: true, maintainAspectRatio: false,
                    onClick: (event, elements) => {
                        // --- Keep onClick handler targeting kmeans.result list view ---
                        if (elements.length > 0) {
                            const firstElement = elements[0];
                            const datasetIndex = firstElement.datasetIndex;
                            const index = firstElement.index;
                            const dataPoint = chartJsData?.datasets?.[datasetIndex]?.data?.[index];
                            if (dataPoint && dataPoint.hasOwnProperty('cluster_id') && typeof dataPoint.cluster_id === 'number' && dataPoint.cluster_id > 0) {
                                const clickedClusterId = dataPoint.cluster_id;
                                console.log(`[onClick] Clicked Cluster ID: ${clickedClusterId}. Opening list view...`);
                                const actionConfig = {
                                    type: 'ir.actions.act_window',
                                    res_model: 'kmeans.result',
                                    name: `Cluster ${clickedClusterId} Results (Run ${this.state.runInfo.runId})`,
                                    view_mode: 'list,form', views: [[false, 'list'], [false, 'form']],
                                    target: 'current',
                                    domain: [['run_id', '=', this.state.runInfo.runId], ['cluster_id', '=', clickedClusterId]],
                                };
                                this.actionService.doAction(actionConfig).catch(e => {
                                     console.error("[onClick] Error during doAction for list view:", e);
                                     this.state.error = `Could not open results for Cluster ${clickedClusterId}: ${e.message || e}`;
                                });
                            } else { console.warn("[onClick] Clicked element missing 'cluster_id'. Data point:", dataPoint); }
                        } else { console.log("[onClick] No chart element detected."); }
                    },
                    plugins: {
                        title: { display: true, text: `Scatter Plot: ${this.state.plotData.yLabel} vs ${this.state.plotData.xLabel}`, font: { size: 16 } },
                        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 12 } } },
                        tooltip: {
                            enabled: true, backgroundColor: 'rgba(0, 0, 0, 0.8)', titleFont: { weight: 'bold' }, bodyFont: { size: 11 }, padding: 8,
                            callbacks: {
                                label: (context) => {
                                    const dataPoint = context.dataset.data[context.dataIndex];
                                    const clusterLabel = context.dataset.label || '';
                                    const customerName = dataPoint?.customerName || 'Customer';
                                    const xVal = context.parsed.x?.toFixed(3);
                                    const yVal = context.parsed.y?.toFixed(3);
                                    return [`${clusterLabel}: ${customerName}`, `(${this.state.plotData.xLabel}: ${xVal}, ${this.state.plotData.yLabel}: ${yVal})`];
                                }
                            }
                        },
                        // --- Explicitly Disable Datalabels ---
                        datalabels: {
                            display: false
                        }
                    },
                    scales: {
                        x: { title: { display: true, text: this.state.plotData.xLabel, font: { weight: 'bold' } }, grid: { color: 'rgba(0, 0, 0, 0.05)' } },
                        y: { beginAtZero: false, title: { display: true, text: this.state.plotData.yLabel, font: { weight: 'bold' } }, grid: { color: 'rgba(0, 0, 0, 0.05)' } }
                    },
                    animation: { duration: 400 }
                }
            });
        } catch(e) { this.state.error = `Chart.js rendering error: ${e.message || e}`; console.error(e); }
    }

    /**
     * Safely destroys the Chart.js instance.
     */
    destroyChart() {
        if (this.chartInstance) {
            this.chartInstance.destroy();
            this.chartInstance = null;
        }
    }

    // --- Event Handlers for Select Dropdowns ---
    onChangeX(ev) {
        this.state.selectedXFeature = ev.target.value;
        this.updatePlotData(); // Re-prepare data based on the new selection
        this.renderChart();    // Re-render the chart with the updated data/axes
    }
    onChangeY(ev) {
        this.state.selectedYFeature = ev.target.value;
        this.updatePlotData(); // Re-prepare data
        this.renderChart();    // Re-render chart
    }

    // --- Navigation ---
    goBack() {
         if (this.state.runInfo.runId) {
             // Use Odoo's action service to navigate back to the specific record
             this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'intelligent.kmeans',
                res_id: this.state.runInfo.runId,
                views: [[false, 'form']], // Specify to open in form view
                target: 'main', // Open in the main content area, replacing the current view
             });
         } else {
             // Fallback if runId is somehow missing
             window.history.back();
         }
    }
} // End of KmeansScatterDashboard Class

// --- Template ---
KmeansScatterDashboard.template = xml/* xml */`
    <div class="o_kmeans_scatter_dashboard container-fluid p-3 bg-light vh-100 d-flex flex-column">
        <div class="d-flex justify-content-between align-items-center mb-3 p-2 border-bottom bg-white rounded shadow-sm flex-shrink-0">
            <div>
                 <button class="btn btn-secondary btn-sm me-2" title="Back to K-Means Run" t-on-click="goBack">
                    <i class="fa fa-arrow-left me-1" role="img" aria-label="Back"/> Back
                 </button>
                 <h2 class="h5 d-inline-block mb-0 align-middle">K-Means Scatter Plot</h2>
                 <span t-if="state.runInfo.runName" class="ms-2 text-muted small fst-italic"><t t-esc="state.runInfo.runName"/></span>
            </div>
            <div class="d-flex align-items-center" t-if="!state.loading and !state.error and state.allResults.length > 0">
                 <label for="scatterXSelect" class="col-form-label col-form-label-sm fw-bold me-1 ms-3">X-Axis:</label>
                 <select id="scatterXSelect" class="form-select form-select-sm me-3 shadow-sm" style="width: 150px;" aria-label="Select X-axis feature" t-on-change="onChangeX">
                    <t t-foreach="state.features" t-as="feature" t-key="feature.id">
                        <option t-att-value="feature.id" t-att-selected="feature.id === state.selectedXFeature">
                            <t t-esc="feature.label"/>
                        </option>
                    </t>
                 </select>
                 <label for="scatterYSelect" class="col-form-label col-form-label-sm fw-bold me-1">Y-Axis:</label>
                 <select id="scatterYSelect" class="form-select form-select-sm shadow-sm" style="width: 150px;" aria-label="Select Y-axis feature" t-on-change="onChangeY">
                    <t t-foreach="state.features" t-as="feature" t-key="feature.id">
                        <option t-att-value="feature.id" t-att-selected="feature.id === state.selectedYFeature">
                             <t t-esc="feature.label"/>
                        </option>
                    </t>
                 </select>
            </div>
        </div>
        <div class="flex-grow-1 d-flex flex-column">
            <div t-if="state.loading" class="flex-grow-1 d-flex justify-content-center align-items-center text-muted">
                <i class="fa fa-spinner fa-spin fa-2x me-2" role="status" aria-label="Loading"/>Loading Plot Data...
            </div>
            <div t-if="state.error &amp;&amp; !state.loading" class="alert alert-danger mx-3 flex-grow-0" role="alert">
                 <i class="fa fa-exclamation-triangle me-2" role="img" aria-label="Error"/>Error: <t t-esc="state.error"/>
            </div>
            <div t-if="!state.loading and !state.error and state.allResults.length > 0" class="bg-white border rounded p-3 shadow-sm mx-3 mb-3" style="min-height: 400px;">
                 <div class="w-90 h-90" style="position: relative; min-height: 600px;">
                    <canvas t-ref="scatterChartCanvas" class="w-90 h-90" aria-label="Scatter Plot Canvas"></canvas>
                </div>
            </div>
             <div t-if="!state.loading and !state.error and !state.allResults.length === 0" class="flex-grow-1 d-flex justify-content-center align-items-center text-muted">
                No cluster results were found for this run. Please run Step 2 first on the K-Means Run screen.
            </div>
             <div style="height: 20px;"></div> </div>
    </div>
`;

// Register the component as a client action
registry.category("actions").add("kmeans_scatter_plot_action", KmeansScatterDashboard);