# -*- coding: utf-8 -*-
# from odoo import http


# class Tickets(http.Controller):
#     @http.route('/tickets/tickets', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tickets/tickets/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('tickets.listing', {
#             'root': '/tickets/tickets',
#             'objects': http.request.env['tickets.tickets'].search([]),
#         })

#     @http.route('/tickets/tickets/objects/<model("tickets.tickets"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tickets.object', {
#             'object': obj
#         })
