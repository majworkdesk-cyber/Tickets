from odoo import _, api, fields, models


class ModuleName(models.Model):
    _name = 'about_program'
    _description = 'About Program'
    _rec_name = 'name'

    name = fields.Char(string='About Program', default="About Program", readonly=True,)
    creator_name = fields.Char(string="Creator Name", default="Michael Angelo", readonly=True)
    college_mentor = fields.Char(string="College Mentor", default="Dr. Bagus Mulyawan, S.Kom., M.M.", readonly=True)
    program_title = fields.Char(string="Program Title", default="Ticket Service", readonly=True)
    program_description = fields.Text(
        string="About Ticket Service Module",
        default=(
            "Modul Ticket Service merupakan sistem manajemen tiket berbasis Odoo 16 yang terintegrasi "
            "dengan analisis data menggunakan metode Intelligent K-Means dan EDA. "
            "Sistem ini tidak hanya mengelola tiket pelanggan secara otomatis, "
            "tetapi juga mampu melakukan analisis klaster pelanggan secara cerdas, "
            "menampilkan visualisasi interaktif, dan membantu pengambilan keputusan bisnis berbasis data."
        ),
        readonly=True
    )