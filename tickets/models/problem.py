from odoo import _, api, fields, models


class ModuleName(models.Model):
    _name = 'problem.name'
    _description = 'New Description'

    name = fields.Char(string='Problem')
    problem_def = fields.Many2one(comodel_name='definition.name', string='Problem Definition')
    
    problem = fields.Many2one(comodel_name='', string='')
    
    
    
