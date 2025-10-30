/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, onWillStart, onMounted, useRef, useState } from "@odoo/owl"; 
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

// PENTING: Pindahkan konstanta warna ke luar kelas atau di dalam setup/class property 
// agar dapat diakses oleh semua metode, atau definisikan di global scope modul.
const CHART_COLORS = {
    "Problem Distribution (Ticket Count)": '#FF6384',
    "Problem Definition Distribution (Ticket Count)": '#FFCD56',
    "Sales Response Performance (Avg Hours)": '#4BC0C0',
    "Technician Resolution Performance (Avg Hours)": '#9966FF', 
    "Top Customers by Point Usage": '#000000',
};


class TicketDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.charts = {};
        
        // State untuk Filter Tanggal & Sorting Customer
        this.state = useState({
            startDate: '2020-01-01', 
            endDate: this.formatDate(new Date()),
            // State baru untuk sorting customer: 'desc' (default) atau 'asc'
            customerSort: 'desc', 
        });

        // Refs
        this.problemChartRef = useRef("problemChart");
        this.definitionChartRef = useRef("definitionChart");
        this.priorityChartRef = useRef("priorityChart");
        this.ratingChartRef = useRef("ratingChart");
        this.salesChartRef = useRef("salesChart");
        this.techChartRef = useRef("techChart");
        this.customerChartRef = useRef("customerChart");

        onWillStart(async () => {
            await loadJS("https://cdn.jsdelivr.net/npm/chart.js");
            await loadJS("https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels");

            if (window.Chart && window.ChartDataLabels) {
                Chart.register(window.ChartDataLabels);
            }
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    formatDate(date) {
        return new Date(date).toISOString().split('T')[0];
    }

    onDateChange(event) {
        this.state[event.target.name] = event.target.value;
        this.renderCharts(); 
    }
    
    // Handler baru untuk mengubah urutan sorting customer
    onCustomerSortChange(event) {
        this.state.customerSort = event.target.value;
        this.renderCharts(); 
    }

    openTicketListView({ name, domain }) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: 'ticket.name', 
            views: [
                [false, 'list'], 
                [false, 'form']  
            ],
            domain: domain,
            target: 'current',
        });
    }

    async renderCharts() {
        try {
            const baseDomain = [
                ['submitted_date', '>=', this.state.startDate + ' 00:00:00'],
                ['submitted_date', '<=', this.state.endDate + ' 23:59:59'],
            ];

            const tickets = await this.orm.searchRead("ticket.name", baseDomain, [
                "category", "definition", "priority", "customer_rating",
                "submitted_date", "progress_date", "finish_date", 
                "sales_person_id", "technician", "customer_name_id", "min_point"
            ]);

            // --- Data Processing ---
            const problemCounts = {};
            const definitionCounts = {};
            const priorityCounts = {};
            const ratingCounts = { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0 };
            const salesPerf = {};
            const techPerf = {};
            const customerPoints = {};
            
            tickets.forEach(t => {
                const cat = t.category ? t.category[1] : "Uncategorized";
                problemCounts[cat] = (problemCounts[cat] || 0) + 1;
                const def = t.definition ? t.definition[1] : "Undefined";
                definitionCounts[def] = (definitionCounts[def] || 0) + 1;
                const p = t.priority || "None";
                priorityCounts[p] = (priorityCounts[p] || 0) + 1;
                
                switch (t.customer_rating) {
                    case "worst": ratingCounts["1"]++; break;
                    case "bad": ratingCounts["2"]++; break;
                    case "medium": ratingCounts["3"]++; break;
                    case "good": ratingCounts["4"]++; break;
                    case "excellent": ratingCounts["5"]++; break;
                }

                if (t.submitted_date && t.progress_date && t.sales_person_id) {
                    const sales = t.sales_person_id[1];
                    const delta = (new Date(t.progress_date) - new Date(t.submitted_date)) / (1000 * 60 * 60);
                    if (!salesPerf[sales]) salesPerf[sales] = [];
                    salesPerf[sales].push(delta);
                }

                if (t.progress_date && t.finish_date && t.technician) {
                    const tech = t.technician[1];
                    const delta = (new Date(t.finish_date) - new Date(t.progress_date)) / (1000 * 60 * 60);
                    if (!techPerf[tech]) techPerf[tech] = [];
                    techPerf[tech].push(delta);
                }

                const cust = t.customer_name_id ? t.customer_name_id[1] : "Unknown";
                if (cust && t.min_point) {
                    customerPoints[cust] = (customerPoints[cust] || 0) + t.min_point;
                }
            });

            const salesAvg = {};
            Object.keys(salesPerf).forEach(s => {
                const vals = salesPerf[s];
                salesAvg[s] = vals.reduce((a, b) => a + b, 0) / vals.length;
            });

            const techAvg = {};
            Object.keys(techPerf).forEach(te => {
                const vals = techPerf[te];
                techAvg[te] = vals.reduce((a, b) => a + b, 0) / vals.length;
            });

            // --- Customer Points: Filter Top N berdasarkan Sort State ---
            const customerPointsEntries = Object.entries(customerPoints);
            const TOP_N = 20; 
            
            let filteredEntries;

            if (this.state.customerSort === 'asc') {
                // Ambil 20 terendah (Lowest) dari total data
                filteredEntries = customerPointsEntries
                    .sort((a, b) => a[1] - b[1]) // Sortir Lowest to Highest
                    .slice(0, TOP_N); // Ambil 20 teratas (yang merupakan 20 terendah)
                
            } else {
                // Ambil 20 tertinggi (Highest) dari total data (Default)
                filteredEntries = customerPointsEntries
                    .sort((a, b) => b[1] - a[1]) // Sortir Highest to Lowest
                    .slice(0, TOP_N); // Ambil 20 teratas (yang merupakan 20 tertinggi)
            }
            
            const topNCustomerPoints = Object.fromEntries(filteredEntries);


            // --- Render Charts ---
            this.renderBarChart(this.problemChartRef, "Problem Distribution (Ticket Count)", problemCounts, 'category', false);
            this.renderBarChart(this.definitionChartRef, "Problem Definition Distribution (Ticket Count)", definitionCounts, 'definition', false);
            this.renderPieChart(this.priorityChartRef, "Priority Distribution", priorityCounts, 'priority');
            this.renderDoughnutChart(this.ratingChartRef, "Customer Ratings", ratingCounts, 'customer_rating');
            this.renderBarChart(this.salesChartRef, "Sales Response Performance (Avg Hours)", salesAvg, 'sales_person_id', true);
            this.renderBarChart(this.techChartRef, "Technician Resolution Performance (Avg Hours)", techAvg, 'technician', true);
            // Panggil renderBarChart untuk customer dengan state sorting baru
            this.renderBarChart(this.customerChartRef, `Top ${TOP_N} Customers by Point Usage`, topNCustomerPoints, 'customer_name_id', false, this.state.customerSort);

        } catch (error) {
            console.error("❌ Error in renderCharts:", error);
        }
    }

    // --- Chart Methods (bar, pie, doughnut) ---
    // Tambahkan parameter sortOrder
    renderBarChart(ref, title, dataObj, fieldName, isAverage, sortOrder = 'desc') { 
        if (!ref || !ref.el) return;
        if (!dataObj || Object.keys(dataObj).length === 0) {
            if (this.charts[title]) { try { this.charts[title].destroy(); } catch(e) {} delete this.charts[title]; }
            return;
        }

        if (this.charts[title]) { try { this.charts[title].destroy(); } catch (e) {} delete this.charts[title]; }

        // 1. Logika sorting yang diperbarui
        let sortedEntries;
        if (sortOrder === 'asc') {
            sortedEntries = Object.entries(dataObj).sort((a, b) => a[1] - b[1]); // Lowest to Highest
        } else {
            sortedEntries = Object.entries(dataObj).sort((a, b) => b[1] - a[1]); // Highest to Lowest (Default)
        }
        
        // 2. Deklarasi sortedLabels dan sortedValues (Penting: harus sebelum digunakan!)
        const sortedLabels = sortedEntries.map(e => String(e[0]));
        const sortedValues = sortedEntries.map(e => Number(e[1]));
        
        // 3. Ambil warna berdasarkan judul
        const barColor = CHART_COLORS[title] || '#36A2EB'; // Default ke Biru jika tidak ditemukan

        const baseDomain = [
            ['submitted_date', '>=', this.state.startDate + ' 00:00:00'],
            ['submitted_date', '<=', this.state.endDate + ' 23:59:59'],
        ];

        const yLabel = isAverage ? 'Average Time (Hours)' : (title.toLowerCase().includes('point') ? 'Total Points' : 'Ticket Count');
        const total = isAverage ? null : sortedValues.reduce((a, b) => a + b, 0);

        const datalabelsConfig = {
            formatter: (value) => {
                if (!value && value !== 0) return '';
                if (isAverage) return value.toFixed(2);
                if (!total) return String(value);
                const percentage = ((value / total) * 100).toFixed(1) + "%";
                return `${Math.round(value)} (${percentage})`;
            },
            color: '#333',
            anchor: 'end',
            align: 'top',
            offset: 4,
            font: { weight: 'bold', size: 10 }
        };

        this.charts[title] = new Chart(ref.el, {
            type: "bar",
            data: {
                labels: sortedLabels,
                datasets: [{
                    label: yLabel,
                    data: sortedValues,
                    // Gunakan barColor yang sudah ditentukan
                    backgroundColor: sortedLabels.map(() => barColor), 
                    barPercentage: 0.6,
                    categoryPercentage: 0.8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (event, elements) => {
                    if (!elements || !elements.length) return;
                    const idx = elements[0].index;
                    const label = sortedLabels[idx];
                    const clickDomain = isNaN(label) ? [[fieldName, 'ilike', label]] : [[fieldName, '=', label]];
                    this.openTicketListView({
                        name: `${title}: ${label}`,
                        domain: baseDomain.concat(clickDomain),
                    });
                },
                plugins: {
                    title: { display: true, text: title },
                    datalabels: datalabelsConfig
                },
                scales: {
                    x: { ticks: { autoSkip: false, maxRotation: 40, minRotation: 30, font: { size: 10 } } },
                    y: { beginAtZero: true, title: { display: true, text: yLabel } }
                }
            }
        });
    }

    // ... (renderPieChart dan renderDoughnutChart tetap sama)
    renderPieChart(ref, title, dataObj, fieldName) {
        if (!ref.el || Object.keys(dataObj).length === 0) return;
        if (this.charts[title]) this.charts[title].destroy();

        const baseDomain = [
            ['submitted_date', '>=', this.state.startDate + ' 00:00:00'],
            ['submitted_date', '<=', this.state.endDate + ' 23:59:59'],
        ];

        const priorityColors = { 'low': '#4CAF50', 'medium': '#FFC107', 'high': '#F44336', 'None': '#9E9E9E' };
        const backgroundColors = Object.keys(dataObj).map(label => priorityColors[label] || '#CCCCCC');
        const total = Object.values(dataObj).reduce((a, b) => a + b, 0);

        this.charts[title] = new Chart(ref.el, {
            type: "pie",
            data: {
                labels: Object.keys(dataObj),
                datasets: [{ data: Object.values(dataObj), backgroundColor: backgroundColors }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (event, elements) => {
                    if (!elements.length) return;
                    const index = elements[0].index;
                    const label = Object.keys(dataObj)[index]; 
                    const clickDomain = [[fieldName, '=', label]];
                    this.openTicketListView({ name: `${title}: ${label}`, domain: baseDomain.concat(clickDomain) });
                },
                plugins: {
                    title: { display: true, text: title },
                    datalabels: { 
                        formatter: (value) => { const percentage = ((value / total) * 100).toFixed(1) + "%"; if (value===0) return ''; return `${Math.round(value)} (${percentage})`; },
                        color: '#fff', textShadowBlur: 4, textShadowColor: 'rgba(0,0,0,0.5)', font: { weight:'bold', size:10 }
                    }
                }
            }
        });
    }

    renderDoughnutChart(ref, title, dataObj, fieldName) {
        if (!ref.el || Object.keys(dataObj).length === 0) return;
        if (this.charts[title]) this.charts[title].destroy();

        const baseDomain = [
            ['submitted_date', '>=', this.state.startDate + ' 00:00:00'],
            ['submitted_date', '<=', this.state.endDate + ' 23:59:59'],
        ];

        const displayLabels = ["⭐ 1","⭐ 2","⭐ 3","⭐ 4","⭐ 5"];
        const datasetData = [dataObj["1"],dataObj["2"],dataObj["3"],dataObj["4"],dataObj["5"]];
        const total = datasetData.reduce((a,b)=>a+b,0);

        this.charts[title] = new Chart(ref.el,{
            type:"doughnut",
            data:{labels: displayLabels, datasets:[{data: datasetData, backgroundColor:["#FF6384","#FF9F40","#FFCD56","#4BC0C0","#36A2EB"]}]},
            options:{
                responsive:true,
                maintainAspectRatio:false,
                plugins:{
                    title:{display:true,text:title},
                    datalabels:{formatter:(value)=>{if(!total||value===0)return'';const percent=((value/total)*100).toFixed(1);return`${Math.round(value)} (${percent}%)`;}, color:'#fff', font:{weight:'bold',size:10}},
                    legend:{position:'top'}
                },
                onClick:(event,elements)=>{if(!elements.length)return;const idx=elements[0].index;const ratingMap=["worst","bad","medium","good","excellent"];const ratingValue=ratingMap[idx];const clickDomain=[[fieldName,'=',ratingValue]];this.openTicketListView({name:`${title}: ${ratingValue.toUpperCase()}`,domain:baseDomain.concat(clickDomain)});}
            }
        });
    }
}

// --- XML Template ---
TicketDashboard.template = xml`
<div class="o_ticket_dashboard" style="padding:20px; height:100vh; overflow-y:auto; background:#f8f9fa;">
    <h2 style="color:#875A7B; margin-bottom:20px; text-align:center;">📊 Ticket Dashboard</h2>

    <div style="display:flex; justify-content:center; align-items:center; margin-bottom:30px; gap:15px; background:white; padding:15px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <label for="startDate" style="font-weight:bold; color:#555;">Mulai Tanggal:</label>
        <input type="date" id="startDate" name="startDate" t-att-value="state.startDate" t-on-change="onDateChange" style="padding:8px; border:1px solid #ced4da; border-radius:4px;"/>
        <label for="endDate" style="font-weight:bold; color:#555;">Sampai Tanggal:</label>
        <input type="date" id="endDate" name="endDate" t-att-value="state.endDate" t-on-change="onDateChange" style="padding:8px; border:1px solid #ced4da; border-radius:4px;"/>
    </div>
    
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap:20px; max-width:2000px; margin:0 auto;">
        
        <div style="background:white; border-radius:8px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1); height:400px; grid-column: span 4; cursor:pointer;">
             <div style="display:flex; justify-content:flex-end; margin-bottom:10px;">
                <label for="customerSort" style="margin-right:10px; font-weight:bold; color:#555;">Urutkan:</label>
                <select id="customerSort" name="customerSort" t-att-value="state.customerSort" t-on-change="onCustomerSortChange" style="padding:5px; border:1px solid #ced4da; border-radius:4px;">
                    <option value="desc">Highest to Lowest</option>
                    <option value="asc">Lowest to Highest</option>
                </select>
            </div>
            <canvas t-ref="customerChart" style="width:100%; height:90%;"></canvas>
        </div>

        <div style="background:white; border-radius:8px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1); height:350px; grid-column: span 2; cursor:pointer;">
            <canvas t-ref="salesChart" style="width:100%; height:100%;"></canvas>
        </div>
        
        <div style="background:white; border-radius:8px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1); height:350px; grid-column: span 2; cursor:pointer;">
            <canvas t-ref="techChart" style="width:100%; height:100%;"></canvas>
        </div>

        <div style="grid-column: span 4; display: flex; gap: 20px; margin-bottom: 5px;">
            
            <div style="flex: 1 1 0; background:white; border-radius:8px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1); height:350px; cursor:pointer;">
                <canvas t-ref="problemChart" style="width:100%; height:100%;"></canvas>
            </div>
            
            <div style="flex: 1 1 0; background:white; border-radius:8px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1); height:350px; cursor:pointer;">
                <canvas t-ref="priorityChart" style="width:100%; height:100%;"></canvas>
            </div>
            
            <div style="flex: 1 1 0; background:white; border-radius:8px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1); height:350px; cursor:pointer;">
                <canvas t-ref="ratingChart" style="width:100%; height:100%;"></canvas>
            </div>
        </div>
        <div style="background:white; border-radius:8px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1); height:500px; grid-column: span 4; cursor:pointer;">
            <canvas t-ref="definitionChart" style="width:100%; height:100%;"></canvas>
        </div>
        
    </div>
</div>
`;

registry.category("actions").add("tickets.ticket_dashboard_action", TicketDashboard);