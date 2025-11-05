from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime

class Point(models.Model):
    _name = 'point.name'
    _description = 'Point'

    name = fields.Float(string='Points')
    # ticket_id = fields.Many2one(comodel_name='ticket.name', string='Ticket')
    product_point = fields.Many2one(comodel_name='problem.name', string='Produk')
    
    customer_id = fields.Many2one(comodel_name='res.partner', string='Customer', store=True)

    expired_date = fields.Datetime('Expired date')

    total_min_points = fields.Float(
        string="Total Used Tiket Poin",
        compute="_compute_total_min_points",
        store=True
    )

    @api.depends('customer_id','product_point')  # depend on customer
    def _compute_total_min_points(self):
        for record in self:
            if record.customer_id and record.product_point:
                # Ambil semua tiket milik customer ini
                tickets = self.env['point.transaction'].search([
                    ('customer_id', '=', record.customer_id.id),
                    ('problem_ticket', '=', record.product_point.id)
                ])
                # Akumulasi semua min_point
                total = sum(t.used_point for t in tickets)
                record.total_min_points = total
            else:
                record.total_min_points = 0

    # etest = fields.Char(string='etest')

    # @api.depends('ticket_id')
    # def _compute_customer_id(self):
    #     for rec in self:
    #         rec.customer_id = rec.ticket_id[0].customer_name_id if rec.ticket_id else False 
    
    # @api.constrains('name')
    # def _check_name(self):
    #     for record in self:
    #         if record.name and not record.name.isdigit():
    #             raise ValidationError("Isi Field Point dengan angka, tidak boleh ada huruf")
