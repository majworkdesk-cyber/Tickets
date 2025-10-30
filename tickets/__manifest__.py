# -*- coding: utf-8 -*-
{
    'name': "tickets",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'mail'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/ticket.xml',
        'views/state.xml',
        'views/states.xml',
        'views/point.xml',
        'views/point_transaction.xml',
        'views/ticket_sequence.xml',
        'views/contact_inherit.xml',
        'views/ticket_email_temp.xml',
        'views/problem_view.xml',
        'security/view_users.xml', 
        'views/problem_def.xml',
        'views/ticket_dashboard_views.xml',
        'views/avg_ticket.xml',
        'views/eda_std.xml',
        'views/eda_correlation.xml',
        'views/correlation_menu.xml',
        'views/intelligent_kmeans.xml',
        'views/normalization.xml',
        'views/kmeans_result.xml',
        'views/kmeans_menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    
    # # qweb templates khusus untuk assets JS
    # 'qweb': [
    #     'static/src/xml/ticket_dashboard_template.xml',
    # ],
    
    'assets': {
        'web.assets_backend': [
            'tickets/static/src/js/ticket_dashboard.js',
            'tickets/static/src/js/correlation_dashboard.js',
            'tickets/static/src/js/kmeans_scatter_plot.js',
            'tickets/static/lib/chartjs/chart.umd.js',
            'tickets/static/lib/datalabels/chartjs-plugin-datalabels.min.js',
            'tickets/static/lib/chartjsmatrix/chartjs-chart-matrix.min.js',
        ],
    },
}
