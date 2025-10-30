from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

class AvgTicket(models.Model):
    _name = 'avg.ticket'
    _description = 'Average Ticket Summary per Customer'
    _rec_name = 'customer_id'
    _order = 'avg_point desc'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True, index=True)
    customer_name = fields.Char(string='Customer', compute='_compute_customer_name', store=False)
    ticket_count = fields.Integer(string='Total Tickets', readonly=True)
    avg_priority = fields.Float(string='Average Priority', readonly=True)
    avg_complexity = fields.Float(string='Average Complexity', readonly=True)
    avg_response_time = fields.Float(string='Average Response (Seconds)', readonly=True)
    avg_resolution_time = fields.Float(string='Average Resolution (Seconds)', readonly=True)
    avg_point = fields.Float(string='Average Point (min_point)', readonly=True)
    avg_rating = fields.Float(string='Average Rating (1-5)', readonly=True)
    last_computed = fields.Datetime(string='Last Computed', readonly=True)

    PRIORITY_MAP = {'low': 1, 'medium': 2, 'high': 3}
    COMPLEXITY_MAP = {'none': 0, 'low': 1, 'medium': 1.5, 'high': 2}
    RATING_MAP = {'no': 0, 'worst': 1, 'bad': 2, 'medium': 3, 'good': 4, 'excellent': 5}

    # === Hitung rata-rata untuk 1 customer ===
    def compute_avg_for_customer(self, customer_id):
        Ticket = self.env['ticket.name']
        tickets = Ticket.search([('customer_name_id', '=', customer_id)])
        if not tickets:
            return {
                'ticket_count': 0,
                'avg_priority': 0,
                'avg_complexity': 0,
                'avg_response_time': 0,
                'avg_resolution_time': 0,
                'avg_point': 0,
                'avg_rating': 0,
            }

        count = len(tickets)
        total_priority = total_complexity = total_response = total_resolution = total_point = total_rating = 0
        valid_response = valid_resolution = valid_point = valid_rating = 0

        for t in tickets:
            total_priority += self.PRIORITY_MAP.get(t.priority, 0)
            total_complexity += self.COMPLEXITY_MAP.get(t.complexity, 0)

            if t.submitted_date and t.progress_date:
                delta = t.progress_date - t.submitted_date
                total_response += delta.total_seconds()
                valid_response += 1

            if t.progress_date and t.finish_date:
                delta = t.finish_date - t.progress_date
                total_resolution += delta.total_seconds()
                valid_resolution += 1

            if t.min_point:
                total_point += t.min_point
                valid_point += 1

            if t.customer_rating:
                total_rating += self.RATING_MAP.get(t.customer_rating, 0)
                valid_rating += 1

        return {
            'ticket_count': count,
            'avg_priority': total_priority / count if count else 0,
            'avg_complexity': total_complexity / count if count else 0,
            'avg_response_time': total_response / valid_response if valid_response else 0,
            'avg_resolution_time': total_resolution / valid_resolution if valid_resolution else 0,
            'avg_point': total_point / valid_point if valid_point else 0,
            'avg_rating': total_rating / valid_rating if valid_rating else 0,
        }

    @api.depends('customer_id')
    def _compute_customer_name(self):
        for rec in self:
            rec.customer_name = rec.customer_id.name if rec.customer_id else ''

    # === Recompute semua customer (data lama / mass update) ===
    @api.model
    def recompute_all(self):
        Ticket = self.env['ticket.name']
        all_customers = Ticket.search([]).mapped('customer_name_id')
        created, updated = 0, 0

        for customer in all_customers:
            vals = self.compute_avg_for_customer(customer.id)
            vals.update({'customer_id': customer.id, 'last_computed': fields.Datetime.now()})
            avg_rec = self.search([('customer_id', '=', customer.id)], limit=1)

            if avg_rec:
                avg_rec.write(vals)
                updated += 1
            else:
                self.create(vals)
                created += 1

        return {'created': created, 'updated': updated}

    # === Manual refresh dari form (opsional) ===
    def action_refresh(self):
        for rec in self:
            vals = self.compute_avg_for_customer(rec.customer_id.id)
            vals.update({'last_computed': fields.Datetime.now()})
            rec.write(vals)
        return True
    
    @api.model
    def create(self, vals):
        """
        - Cegah create manual dari UI.
        - Tapi biarkan create dari kode atau recompute_all() tetap bisa.
        """

        # ✅ hanya blokir jika benar-benar dari UI (context Odoo form view)
        if self.env.context.get('params') and not self.env.context.get('from_ticket_auto'):
            raise UserError("Record Average Ticket tidak bisa dibuat manual. Sistem akan membuatnya otomatis.")

        # Buat record baru
        record = super(AvgTicket, self).create(vals)

        # Auto isi nilai avg biar tidak kosong
        if record.customer_id:
            vals = record.compute_avg_for_customer(record.customer_id.id)
            vals.update({'last_computed': fields.Datetime.now()})
            record.write(vals)

        return record