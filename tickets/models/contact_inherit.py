from odoo import _, api, fields, models
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.exceptions import ValidationError


class PurchaseOrderInherit(models.Model):
    _inherit = 'res.partner'

    contact_role = fields.Selection(string='Role', selection=[('Admin', 'admin'), ('Sales', 'sales'), ('Technician', 'technician')])
    

    
