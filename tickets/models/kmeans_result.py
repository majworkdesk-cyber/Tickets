# tickets/models/kmeans_result.py
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class KmeansResult(models.Model):
    _name = 'kmeans.result' # Correct model name
    _description = 'K-Means Cluster Assignment Result'
    _rec_name = 'customer_id'
    _order = 'cluster_id, customer_id'

    # Link back to the K-Means run
    run_id = fields.Many2one(
        comodel_name='intelligent.kmeans', # Link back to the control model
        string='K-Means Run',
        ondelete='cascade',
        index=True,
        required=True
    )

    # Customer and assigned cluster
    customer_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True, index=True, required=True
    )
    cluster_id = fields.Integer(string='Cluster', readonly=True, index=True, required=True)

    normalization_id = fields.Many2one(
        'normalization.name', string='Normalization Record Ref',
        readonly=True, index=True, ondelete='set null' # Link ke record normalization.name
    )
    
    # Snapshot of Z-Score data used for clustering
    norm_ticket_count = fields.Float(string='Z-Count', readonly=True)
    norm_priority = fields.Float(string='Z-Priority', readonly=True)
    norm_complexity = fields.Float(string='Z-Complexity', readonly=True)
    norm_response_time = fields.Float(string='Z-Response', readonly=True)
    norm_resolution_time = fields.Float(string='Z-Resolution', readonly=True)
    norm_rating = fields.Float(string='Z-Rating', readonly=True)
    norm_point = fields.Float(string='Z-Point', readonly=True)

    @api.model
    def create(self, vals_list):
        # Prevent manual creation from UI
        context = self.env.context
        # Check context for both single create and batch create (list)
        if isinstance(vals_list, dict) and not context.get('from_kmeans_run'):
             _logger.warning("Manual creation attempt blocked for kmeans.result.")
             raise models.UserError("Cluster results cannot be created manually. Use the K-Means control panel.")
        if isinstance(vals_list, list) and not context.get('from_kmeans_run'):
             _logger.warning("Manual batch creation attempt blocked for kmeans.result.")
             raise models.UserError("Cluster results cannot be created manually in batch. Use the K-Means control panel.")
        return super(KmeansResult, self).create(vals_list)

    def write(self, vals):
         # Prevent editing after creation
         _logger.warning(f"Modification attempt blocked for kmeans.result {self.ids}.")
         raise models.UserError("Cluster results cannot be modified after creation.")

    # Unlink is allowed (e.g., when re-running clustering)
    def unlink(self):
        _logger.info(f"Deleting kmeans.result records: {self.ids}")
        return super(KmeansResult, self).unlink()