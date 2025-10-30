from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
import math  # <-- Import math instead of numpy

_logger = logging.getLogger(__name__)


class NormalizationName(models.Model):
    _name = "normalization.name"
    _description = "Normalization of Ticket Data (Z-Score per Customer)"
    _rec_name = "customer_id"
    # [Ref: Proposal 2.5.1]
    _order = "norm_point desc" # Order by the normalized Z-score

    # ========= Basic info =========
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, index=True)
    customer_name = fields.Char(string='Customer', compute='_compute_customer_name', store=False)

    # ========= Original avg fields (from avg.ticket) =========
    # These fields store a snapshot of the data at the time of calculation
    # [cite_start][Ref: Proposal 2.5.1, Tabel L 2.1] [cite: 471-480, 1110-1114]
    ticket_count = fields.Float(string='Total Tickets', readonly=True)
    avg_priority = fields.Float(string='Average Priority', readonly=True)
    avg_complexity = fields.Float(string='Average Complexity', readonly=True)
    avg_response_time = fields.Float(string='Average Response (Seconds)', readonly=True)
    avg_resolution_time = fields.Float(string='Average Resolution (Seconds)', readonly=True)
    avg_rating = fields.Float(string='Average Rating (1-5)', readonly=True)
    avg_point = fields.Float(string='Average Point (min_point)', readonly=True)

    # ========= Normalized (Z-Score) =========
    # These are the output fields for the K-Means algorithm
    # [cite_start][Ref: Proposal 2.5.2, Tabel L 2.2] [cite: 482-488, 1116-1123]
    norm_ticket_count = fields.Float(string='Normalized Ticket Count', readonly=True)
    norm_priority = fields.Float(string='Normalized Priority', readonly=True)
    norm_complexity = fields.Float(string='Normalized Complexity', readonly=True)
    norm_response_time = fields.Float(string='Normalized Response', readonly=True)
    norm_resolution_time = fields.Float(string='Normalized Resolution', readonly=True)
    norm_rating = fields.Float(string='Normalized Rating', readonly=True)
    norm_point = fields.Float(string='Normalized Point', readonly=True)

    last_normalized = fields.Datetime(string='Last Normalized', readonly=True)

    # List of fields to process, matching the original fields
    FIELDS_TO_NORMALIZE = [
        'ticket_count', 'avg_priority', 'avg_complexity',
        'avg_response_time', 'avg_resolution_time', 'avg_rating', 'avg_point'
    ]
    
    # Map from original field name to its corresponding 'norm_' field name
    NORM_FIELD_MAP = {
        'ticket_count': 'norm_ticket_count',
        'avg_priority': 'norm_priority',
        'avg_complexity': 'norm_complexity',
        'avg_response_time': 'norm_response_time',
        'avg_resolution_time': 'norm_resolution_time',
        'avg_rating': 'norm_rating',
        'avg_point': 'norm_point',
    }

    # ========= Helpers =========
    @api.depends('customer_id')
    def _compute_customer_name(self):
        for rec in self:
            rec.customer_name = rec.customer_id.name if rec.customer_id else ''

    @api.model
    def _get_global_stats(self, avg_records):
        """
        Helper to calculate Mean (μ) and Standard Deviation (σ) for all fields
        without using numpy.
        [cite_start][Ref: Proposal 2.5.2] [cite: 483-487]
        """
        stats = {}
        n = len(avg_records)
        if n == 0:
            return None

        # Initialize sums
        sums = {field: 0 for field in self.FIELDS_TO_NORMALIZE}
        
        # 1. Calculate sums to find mean
        for rec in avg_records:
            for field in self.FIELDS_TO_NORMALIZE:
                sums[field] += getattr(rec, field, 0)
        
        # 2. Calculate means
        means = {field: sums[field] / n for field in self.FIELDS_TO_NORMALIZE}
        
        # 3. Calculate sum of squared differences (for std dev)
        sum_sq_diffs = {field: 0 for field in self.FIELDS_TO_NORMALIZE}
        for rec in avg_records:
            for field in self.FIELDS_TO_NORMALIZE:
                sum_sq_diffs[field] += (getattr(rec, field, 0) - means[field]) ** 2
        
        # 4. Calculate std dev
        for field in self.FIELDS_TO_NORMALIZE:
            variance = sum_sq_diffs[field] / n
            sigma = math.sqrt(variance)
            
            stats[field] = {
                'mean': means[field],
                'std_dev': sigma if sigma > 0 else 1.0  # Prevent division by zero
            }
            
        return stats

    # ========= Compute Normalization for All =========
    @api.model
    def recompute_all(self):
        """
        Recompute normalization for all customers using data from avg.ticket.
        This is fully automatic, just like avg.ticket.recompute_all().
        """
        _logger.info("Starting normalization recompute_all...")
        
        # 0. Refresh avg.ticket data first to ensure it's up-to-date
        _logger.info("Refreshing avg.ticket records first...")
        self.env['avg.ticket'].recompute_all()

        # 1. Get all average records
        AvgTicket = self.env['avg.ticket']
        avg_records = AvgTicket.search([])

        if not avg_records:
            _logger.warning("⚠️ No data found in avg.ticket for normalization. Aborting.")
            return False

        _logger.info(f"Found {len(avg_records)} records from avg.ticket to normalize.")

        # 2. Compute global statistics (μ and σ) using the helper
        global_stats = self._get_global_stats(avg_records)
        if not global_stats:
            _logger.error("Failed to compute global stats.")
            return False
            
        _logger.info("Global statistics computed (μ and σ).")

        # 3. Update or create normalization records
        created, updated = 0, 0
        all_customer_ids = []
        
        for avg_rec in avg_records:
            all_customer_ids.append(avg_rec.customer_id.id)
            
            vals = {
                'customer_id': avg_rec.customer_id.id,
                'last_normalized': fields.Datetime.now(),
            }
            
            # 4. Add original values and calculated Z-Scores
            for field in self.FIELDS_TO_NORMALIZE:
                # Add original value (e.g., 'avg_point': 10)
                original_value = getattr(avg_rec, field, 0)
                vals[field] = original_value
                
                # Calculate and add normalized value
                # z = (x - μ) / σ
                stats = global_stats[field]
                x = original_value
                mu = stats['mean']
                sigma = stats['std_dev']
                
                z_score = (x - mu) / sigma
                
                norm_field_name = self.NORM_FIELD_MAP[field]
                vals[norm_field_name] = z_score

            # 5. Find existing or create new
            norm_rec = self.search([('customer_id', '=', avg_rec.customer_id.id)], limit=1)
            if norm_rec:
                norm_rec.write(vals)
                updated += 1
            else:
                # Use context to bypass the create check
                self.with_context(from_ticket_auto=True).create(vals)
                created += 1

        # 6. Clean up old records (for customers who no longer have avg.ticket records)
        stale_recs = self.search([('customer_id', 'not in', all_customer_ids)])
        deleted = len(stale_recs)
        if stale_recs:
            stale_recs.unlink()
            _logger.info(f"Cleaned up {deleted} stale normalization records.")

        _logger.info(f"✅ Normalization finished — Created: {created}, Updated: {updated}, Deleted: {deleted}")
        return {'created': created, 'updated': updated, 'deleted': deleted}

    # ========= Manual refresh single =========
    def action_refresh(self):
        """
        Refresh one or more selected records.
        NOTE: This must re-calculate ALL normalization records.
        Why? Because refreshing one customer's average (x) changes the
        global mean (μ) and std dev (σ), which means every other
        customer's Z-Score (z) is also affected.
        """
        _logger.info(f"Manual refresh triggered for {len(self)} records. Running recompute_all...")
        # The logic is statistically correct: refreshing one 
        # requires refreshing all, so we just call the main function.
        self.recompute_all()
        _logger.info("Manual refresh complete.")
        return True

    @api.model
    def create(self, vals):
        """Prevent manual creation like avg.ticket."""
        # Check for 'from_ticket_auto' context set in recompute_all
        if self.env.context.get('params') and not self.env.context.get('from_ticket_auto'):
            raise UserError("Record Normalisasi tidak bisa dibuat manual. Sistem akan membuatnya otomatis.")
        return super(NormalizationName, self).create(vals)