# tickets/models/intelligent_kmeans.py
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
import base64
import io

_logger = logging.getLogger(__name__)

# --- Try importing required libraries ---
try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score, davies_bouldin_score
    import numpy as np
    SKLEARN_INSTALLED = True
except ImportError:
    _logger.warning("⚠️ K-Means: scikit-learn (sklearn) or numpy not installed.")
    SKLEARN_INSTALLED = False
try:
    # Keep Matplotlib ONLY for the Elbow chart
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_INSTALLED = True
except ImportError:
    _logger.warning("⚠️ K-Means: matplotlib not installed (Elbow chart unavailable).")
    MATPLOTLIB_INSTALLED = False

# --- Constants ---
FEATURE_SELECTION = [
    ('norm_ticket_count', 'Z-Count'),
    ('norm_priority', 'Z-Priority'),
    ('norm_complexity', 'Z-Complexity'),
    ('norm_response_time', 'Z-Response'),
    ('norm_resolution_time', 'Z-Resolution'),
    ('norm_rating', 'Z-Rating'),
    ('norm_point', 'Z-Point'),
]
FEATURE_DICT = dict(FEATURE_SELECTION) # Used for Centroid Table labels

class IntelligentKmeans(models.Model):
    _name = 'intelligent.kmeans'
    _description = 'Intelligent K-Means Control Panel'
    _rec_name = 'run_date'

    run_date = fields.Datetime(string='Run Date', default=fields.Datetime.now, readonly=True)

    # --- Step 1 Fields (Find Optimal K) ---
    k_min = fields.Integer(string='Min k', default=2, required=True)
    k_max = fields.Integer(string='Max k (inclusive)', default=10, required=True)
    wcss_results = fields.Html(string='WCSS Results (Elbow)', readonly=True)
    silhouette_results = fields.Html(string='Silhouette Results', readonly=True)
    wcss_data = fields.Text(string='WCSS Data (Raw)', readonly=True)
    silhouette_data = fields.Text(string='Silhouette Data (Raw)', readonly=True)
    elbow_chart = fields.Binary(string="Elbow Method Chart", readonly=True) # Keep Elbow chart

    # --- Step 2 Fields (Final Clustering) ---
    chosen_k = fields.Integer(string='Chosen k', default=3, required=True, help="Select the best 'k'.")
    final_centroids = fields.Html(string='Final Centroids (Z-Scores)', readonly=True)
    final_silhouette = fields.Float(string='Final Silhouette Score', readonly=True)
    final_dbi = fields.Float(string='Final Davies-Bouldin Index', readonly=True)

    # --- REMOVED Scatter Plot Feature Selection Fields from this model ---
    # scatter_x_feature = fields.Selection(...) # REMOVED
    # scatter_y_feature = fields.Selection(...) # REMOVED

    # --- Link to Results ---
    result_count = fields.Integer(compute='_compute_result_count', string="Assigned Clusters")
    result_ids = fields.One2many('kmeans.result', 'run_id', string='Cluster Results')

    def _compute_result_count(self):
        for run in self: run.result_count = len(run.result_ids)

    # --- Library Checks ---
    def _check_sklearn(self):
        if not SKLEARN_INSTALLED:
            raise UserError("Library 'scikit-learn' or 'numpy' not found. Install: 'pip install scikit-learn numpy'")

    def _check_matplotlib(self):
        # Only needed for Elbow chart
        if not MATPLOTLIB_INSTALLED:
             _logger.warning("matplotlib not found. Elbow chart cannot be generated.")

    # --- Data Retrieval ---
    def _get_normalized_data(self):
        """Fetches Z-Score data + record map. Returns X (numpy array), record_map, feature_names (list)."""
        norm_records = self.env['normalization.name'].search([], order='id') # Add consistent order
        if not norm_records: raise UserError("No data found in 'normalization.name'. Run its 'Recompute All' first.")
        data_matrix = []
        record_map = []
        # Use FEATURE_SELECTION keys for consistent order
        feature_names = [f[0] for f in FEATURE_SELECTION]
        feature_indices = {name: i for i, name in enumerate(feature_names)}
        for rec in norm_records:
            row_data = [0.0] * len(feature_names)
            for fname in feature_names:
                row_data[feature_indices[fname]] = getattr(rec, fname, 0.0)
            data_matrix.append(row_data)
            record_map.append(rec) # Keep track of the original normalization record
        X = np.array(data_matrix)
        return X, record_map, feature_names

    # --- Button Actions ---
    def action_find_optimal_k(self):
        """Runs K-Means multiple times and generates Elbow plot."""
        self._check_sklearn()
        X, record_map, feature_names = self._get_normalized_data()
        if len(X) < self.k_max:
             raise UserError(f"Not enough data ({len(X)} records) to test up to k={self.k_max}.")
        wcss = []
        silhouette_scores = []
        k_range = list(range(self.k_min, self.k_max + 1))
        _logger.info(f"K-Means: Finding optimal k from {self.k_min} to {self.k_max}...")
        for k in k_range:
            kmeans = KMeans(n_clusters=k, init="k-means++", random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            wcss.append(kmeans.inertia_)
            if k > 1: silhouette_scores.append(silhouette_score(X, labels))
            else: silhouette_scores.append(0)
        _logger.info("Optimal k calculation finished.")
        wcss_html = "<ul>" + "".join([f"<li><b>k={k}:</b> {w:.4f}</li>" for k, w in zip(k_range, wcss)]) + "</ul>"
        sil_html = "<ul>" + "".join([f"<li><b>k={k}:</b> {s:.4f}</li>" for k, s in zip(k_range, silhouette_scores)]) + "</ul>"
        chart_base64 = self._generate_elbow_chart(k_range, wcss)
        self.write({
            'wcss_results': wcss_html,
            'silhouette_results': sil_html,
            'wcss_data': str(wcss),
            'silhouette_data': str(silhouette_scores),
            'elbow_chart': chart_base64 if chart_base64 else False,
            'run_date': fields.Datetime.now(),
        })
        return True

    def _generate_elbow_chart(self, k_range, wcss_list):
        """Creates Elbow Method plot using matplotlib."""
        self._check_matplotlib()
        if not MATPLOTLIB_INSTALLED: return False
        _logger.info("Generating Elbow Method chart...")
        try:
            plt.figure(figsize=(8, 5))
            plt.plot(k_range, wcss_list, marker="o", linestyle='-')
            plt.xlabel("Number of Clusters (k)")
            plt.ylabel("WCSS")
            plt.title("Elbow Method for Optimal k")
            plt.xticks(k_range)
            plt.grid(True, linestyle='--', alpha=0.6)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            plt.close()
            image_base64 = base64.b64encode(buf.getvalue())
            buf.close()
            return image_base64
        except Exception as e:
            _logger.error(f"Error generating elbow chart: {e}")
            return False

    def action_run_final_clustering(self):
        """Runs K-Means, evaluates, stores results in kmeans.result."""
        self._check_sklearn()
        if self.chosen_k <= 1: raise UserError("'Chosen k' must be greater than 1.")
        _logger.info(f"K-Means: Running final clustering with k={self.chosen_k}...")
        X, norm_records, feature_names = self._get_normalized_data()
        if len(X) < self.chosen_k: raise UserError(f"Not enough data ({len(X)}) for {self.chosen_k} clusters.")
        # Run K-Means
        kmeans = KMeans(n_clusters=self.chosen_k, init="k-means++", random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        centroids = kmeans.cluster_centers_
        # Store results in kmeans.result
        _logger.info("Deleting previous cluster results for this run...")
        self.result_ids.unlink()
        _logger.info(f"Creating {len(labels)} new cluster result records...")
        ResultModel = self.env['kmeans.result']
        vals_list = []
        for i, norm_rec in enumerate(norm_records):
             vals_list.append({
                 'run_id': self.id,
                 'customer_id': norm_rec.customer_id.id,
                 'cluster_id': int(labels[i]) + 1,
                 'norm_ticket_count': norm_rec.norm_ticket_count,
                 'norm_priority': norm_rec.norm_priority,
                 'norm_complexity': norm_rec.norm_complexity,
                 'norm_response_time': norm_rec.norm_response_time,
                 'norm_resolution_time': norm_rec.norm_resolution_time,
                 'norm_rating': norm_rec.norm_rating,
                 'norm_point': norm_rec.norm_point,
             })
        ResultModel.with_context(from_kmeans_run=True).create(vals_list)
        # Evaluate final clusters
        final_sil = silhouette_score(X, labels)
        final_dbi = davies_bouldin_score(X, labels)
        _logger.info(f"Final Evaluation: Silhouette={final_sil:.4f}, DBI={final_dbi:.4f}")
        # Format centroids
        html_table = "<table class='table table-sm table-bordered'><thead><tr><th>Cluster</th>"
        html_table += "".join([f"<th>{FEATURE_DICT.get(fn, fn)}</th>" for fn in feature_names]) + "</tr></thead><tbody>" # Use FEATURE_DICT for labels
        for i, center in enumerate(centroids):
            html_table += f"<tr><td><b>Cluster {i+1}</b></td>" + "".join([f"<td>{val:.4f}</td>" for val in center]) + "</tr>"
        html_table += "</tbody></table>"
        # Save evaluation results
        self.write({
            'final_centroids': html_table,
            'final_silhouette': final_sil,
            'final_dbi': final_dbi,
            'run_date': fields.Datetime.now(),
        })
        self.invalidate_recordset(['result_count'], self.ids) # Update smart button count
        return True

    def action_view_results(self):
        """Action for the smart button to show related cluster result list."""
        self.ensure_one()
        return {
            'name': 'Cluster Results',
            'type': 'ir.actions.act_window',
            'res_model': 'kmeans.result',
            'view_mode': 'tree,form',
            'domain': [('run_id', '=', self.id)],
            'context': {'search_default_group_by_cluster': 1}
        }

    # --- Action to launch the Scatter Plot Client Action ---
    def action_view_scatter_plot(self):
        self.ensure_one()
        if not self.result_ids:
            raise UserError("Please run 'Step 2: Run Final Clustering' first to generate results.")
        # Pass only the run ID and k - features are selected in JS now
        context = {
            'active_id': self.id,
            'active_model': self._name,
            'kmeans_run_id': self.id, # Pass the run ID
            'chosen_k': self.chosen_k,
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'kmeans_scatter_plot_action', # Tag for our JS component
            'name': f'Scatter Plot - Run {self.run_date.strftime("%Y-%m-%d %H:%M") if self.run_date else self.id}',
            'target': 'main', # Open in main content area
            'context': context,
        }