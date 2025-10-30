# from odoo import _, api, fields, models
# from datetime import date, datetime
# from dateutil.relativedelta import relativedelta
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
# from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
# from odoo.exceptions import ValidationError

# class description(models.Model):
#     _name = 'description.name'
#     _description = 'New Description'

#     # name = fields.Char(string='problem', tracking=True,
#     #     store=True)
#     name = fields.Many2one(comodel_name='problem.name', string='Problems')
    
#     problem_description = fields.Char(string='Problem Description', tracking=True)
#     ticket_id = fields.Many2one(comodel_name='ticket.name', tracking=True,
#         store=True)
#     photo_prove = fields.Image('Photo Prove Attacthment', max_width=400, max_height=800, attachment=True, store=True, tracking=True)
    
#     def _post_chatter(self, msg):
#         if self.ticket_id:
#             self.ticket_id.message_post(
#                 body=msg,
#                 message_type='comment',
#                 subtype_xmlid='mail.mt_note'
#             )

#     @api.model
#     def create(self, vals):
#         rec = super().create(vals)
#         msg = (
#             f"➕ Problem Description ditambahkan:<br/>"
#             f"<b>Name:</b> {rec.name or '-'}<br/>"
#             f"<b>Description:</b> {rec.problem_description or '-'}<br/>"
#         )
#         rec._post_chatter(msg)
#         return rec

#     def write(self, vals):
#         messages = []
#         for rec in self:
#             msg_parts = []

#             if 'name' in vals and vals['name'] != rec.name:
#                 msg_parts.append(f"<b>Name:</b> '{rec.name}' → '{vals['name']}'")

#             if 'problem_description' in vals and vals['problem_description'] != rec.problem_description:
#                 msg_parts.append(
#                     f"<b>Description:</b> '{rec.problem_description}' → '{vals['problem_description']}'"
#                 )

#             if msg_parts:
#                 message = (
#                     f"✏️ Problem Description diperbarui:<br/>" +
#                     "<br/>".join(msg_parts)
#                 )
#                 messages.append((rec.ticket_id, message))

#         res = super().write(vals)

#         # Post lognote setelah write
#         for ticket, msg in messages:
#             if ticket:
#                 ticket.message_post(
#                     body=msg,
#                     message_type='comment',
#                     subtype_xmlid='mail.mt_note'
#                 )

#         return res

#     def unlink(self):
#         for rec in self:
#             rec._post_chatter(f"🗑️ Problem Description dihapus: <b>{rec.name}</b>")
            
#         return super().unlink()