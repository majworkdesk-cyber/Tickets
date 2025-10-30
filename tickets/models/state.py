from odoo import _, api, fields, models

class TicketState(models.Model):
    _name = 'state.name'
    _description = 'Ticket State'

    name = fields.Char(string='State', required=True)
    won = fields.Char(string='Won')
    color = fields.Integer(string="Color Index")
    sequence = fields.Integer(string="Sequence")

    fold = fields.Boolean('Folded in Pipeline', help='This stage is folded in the kanban view when there are no records in that stage to display.')
    requirements = fields.Text('Requirements', help="Enter here the internal requirements for this stage (ex: Offer sent to customer). It will appear as a tooltip over the stage's name.")