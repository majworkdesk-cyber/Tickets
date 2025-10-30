from odoo import _, api, fields, models


class ModuleName(models.Model):
    _name = 'definition.name'
    _description = 'New Description'

    name = fields.Char(string='Problem Definition')
    remark = fields.Char(string='Remark')
    service_title = fields.Many2one(comodel_name='problem.name', string='Problem Service')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority')

    complexity = fields.Selection(
        string='Complexity',
        selection=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High')
        ],)
    

    
