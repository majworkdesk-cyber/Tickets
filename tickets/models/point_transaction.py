from odoo import _, api, fields, models

class PointTransaction(models.Model):
    _name = 'point.transaction'
    _description = 'Point Usage History'

    ticket_id = fields.Many2one('ticket.name', string='Related Ticket', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    point_id = fields.Many2one('point.name', string='Customer Points')
    used_point = fields.Integer(string='Used Points', required=True)
    problem_ticket = fields.Many2one('problem.name', string='Problems', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)