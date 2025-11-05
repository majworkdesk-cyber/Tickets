from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime
import math


class Ticketing(models.Model):
    _name = 'ticket.name'
    _description = 'Ticketing Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='No Ticket', readonly=True)

    # problem_description_ids = fields.One2many(
    #     comodel_name='description.name',
    #     inverse_name='ticket_id',
    #     string='Problem Description',
    #     tracking=True,
    # )

    sales_person_id = fields.Many2one(
        'res.users',
        string='Sales Person',
        compute='_compute_sales_person_id',
        store=True,
        readonly=True,
    )
    technician = fields.Many2one(
        'res.partner',
        string='Technician',
        store=True,
    )
    customer_name_id = fields.Many2one(
    'res.partner', 
    string="Customer", 
    default=lambda self: self.env.user.partner_id,)
    customer_name = fields.Char(string="Client", compute='_compute_customer_name_id')
    tech_note = fields.Char(string='Technician Note')
    submitted_date = fields.Datetime(string='Submit Date', default=fields.Datetime.now )
    progress_date = fields.Datetime(string='On Progress Date')
    response_time_days = fields.Integer(string="Response Time (Days)", compute="_compute_response_time", store=True)
    response_time_hours = fields.Float(string="Response Time (Hours)", compute="_compute_response_time_hour", store=True)
    response_time_minutes = fields.Float(string="Response Time (Minutes)", compute="_compute_response_time_minute", store=True)
    finish_date = fields.Datetime(string='Finished Date')
    work_day = fields.Integer(string='Work Days', compute="_compute_work_days", store=True)
    
    manual_min_point = fields.Float(string='Manual Point Override', )
    min_point = fields.Float(string='Ticket Usage', compute='_compute_min_point', inverse='_inverse_min_point', store=True,)

    points_id = fields.Many2one(
        'point.name',
        string='Ticket Available',
        compute='_compute_points_id',
        store=True,
    )

    category = fields.Many2one(
    'problem.name',
    string='Kategori',
    store=True,
    # required=True
    )

    expired_ticket = fields.Datetime(
    string='Expired Ticket',
    compute='_compute_expired_ticket',
    store=True,
    )

    @api.depends('customer_name_id', 'category')
    def _compute_expired_ticket(self):
        for rec in self:
            # Tanggal hangus tiket ini = tanggal hangus dari record poin
            # yang sudah ditemukan oleh _compute_points_id
            rec.expired_ticket = rec.points_id.expired_date or False

    @api.depends('customer_name_id', 'category')
    def _compute_points_id(self):
        for rec in self:
            rec.points_id = False  # Set default
            
            if not rec.customer_name_id or not rec.category:
                continue

            # Domain untuk mencari poin yang valid:
            # 1. Cocokkan customer dan kategori
            # 2. Poinnya masih ada (name > 0)
            # 3. Belum hangus (expired_date = False ATAU expired_date > sekarang)
            domain = [
                ('customer_id', '=', rec.customer_name_id.id),
                ('product_point', '=', rec.category.id),
                ('name', '>', 0),
                '|',
                    ('expired_date', '=', False),
                    ('expired_date', '>', fields.Datetime.now())
            ]

            # Cari record poin yang akan hangus PALING DEKAT
            # 'order='expired_date asc'' artinya:
            # - Urutkan berdasarkan expired_date (asc = dari yang tercepat hangus)
            # - Tanggal NULL (yang tidak punya expired date) otomatis ditaruh di akhir
            point = self.env['point.name'].search(
                domain,
                order='expired_date asc', # <-- INI PERBAIKANNYA
                limit=1
            )
            
            rec.points_id = point

    @api.onchange('category', 'customer_name_id')
    def _onchange_validate_point_available(self):
        for rec in self:
            if rec.customer_name_id and rec.category:
                point = self.env['point.name'].search([
                    ('customer_id', '=', rec.customer_name_id.id),
                    ('product_point', '=', rec.category.id)
                ], limit=1)
                if not point:
                    return {
                        'warning': {
                            'title': "No Points Found",
                            'message': "Customer doesn't have point balance for the selected category."
                        }
                    }

    point_value = fields.Float(string='Ticket Available', compute="_compute_values")
    
    @api.depends('points_id')
    def _compute_values(self):
        for record in self:
            record.point_value = record.points_id.name
    
    states = fields.Many2one(
        'state.name',
        string='Status',
        tracking=True,
        store=True,
        compute='_compute_states',
        group_expand='_read_group_stage_ids',
        ondelete='restrict',
        readonly=False,
    )

    color = fields.Integer(string="Color Index")

    # states_readonly = fields.Boolean(
    #     string="Is State Readonly",
    #     compute="_compute_states_readonly"
    # )

    customer_rating = fields.Selection(string='Customer Rating', selection=[
        ('no', 'No'),
        ('worst', 'Worst'), 
        ('bad', 'Bad'), 
        ('medium', 'Medium'), 
        ('good', 'Good'), 
        ('excellent', 'Excellent')])
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority',)

    complexity = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Complexity', default='none')

    @api.onchange('definition')
    def _onchange_definition(self):
        if self.definition:
            self.priority = self.definition.priority
            self.complexity = self.definition.complexity
        else:
            self.complexity = 'none'
    # total_point_used = fields.Integer(
    #         string="Total Poin Terpakai",
    #         compute="_compute_total_point_used",
    #         store=True
    #     )

    # @api.depends('customer_name_id')
    # def _compute_total_point_used(self):
    #     for record in self:
    #         if record.customer_name_id:
    #             tickets = self.env['ticket.name'].search([
    #                 ('customer_name_id', '=', record.customer_name_id.id)
    #             ])
    #             record.total_point_used = sum(t.min_point or 0 for t in tickets)
    #         else:
    #             record.total_point_used = 0

    @api.depends('customer_name_id', 'customer_name_id.user_id')
    def _compute_sales_person_id(self):
        for record in self:
            record.sales_person_id = record.customer_name_id.user_id or False

    # respond times
    @api.depends('submitted_date', 'progress_date')
    def _compute_response_time(self):
        for record in self:
            if record.submitted_date and record.progress_date:
                delta = record.progress_date - record.submitted_date
                record.response_time_days = delta.days
            else:
                record.response_time_days = 0

    @api.depends('submitted_date', 'progress_date')
    def _compute_response_time_hour(self):
        for record in self:
            if record.submitted_date and record.progress_date:
                delta = record.progress_date - record.submitted_date
                record.response_time_hours = delta.total_seconds() / 3600
            else:
                record.response_time_hours = 0

    @api.depends('submitted_date', 'progress_date')
    def _compute_response_time_minute(self):
        for record in self:
            if record.submitted_date and record.progress_date:
                delta = record.progress_date - record.submitted_date
                record.response_time_minutes = delta.total_seconds() / 60
            else:
                record.response_time_minutes = 0

    @api.depends('progress_date', 'finish_date')
    def _compute_work_days(self):
        for record in self:
            if record.progress_date and record.finish_date:
                delta = record.finish_date - record.progress_date
                record.work_day = delta.days
            else:
                record.work_day = 0
            
    # nama customer auto
    @api.depends('customer_name_id')
    def _compute_customer_name_id(self):
        if self.customer_name_id:
            self.customer_name = self.customer_name_id.name
        else:
            self.customer_name = False

    # @api.depends('states', 'points_id.name')
    # def _compute_states_readonly(self):
    #     for rec in self:
    #         user = self.env.user
    #         rec.states_readonly = user.has_group('tickets.group_customer_only')

    @api.depends('states')
    def _compute_states(self):
        for rec in self:
            if not rec.states:
                rec.states = self.env['state.name'].search([('fold', '=', False)], limit=1).id

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.search([], order=order)

    calculate_bool = fields.Boolean(string='true/false')
    

    # State Calculate Actions
    def action_calculate_cost(self):
        for rec in self:
            
            rec.calculate_bool = True

            if not rec.points_id:
                raise ValidationError("Customer tidak memiliki poin yang terdaftar.")

            if rec.min_point <= 0:
                raise ValidationError("Point cost tidak boleh negatif.")

            if rec.points_id.name < rec.min_point:
                raise ValidationError("Poin customer tidak cukup.")

            # Kurangi poin
            rec.points_id.name -= rec.min_point

            # Catat transaksi
            self.env['point.transaction'].create({
                'point_id': rec.points_id.id,
                'ticket_id': rec.id,
                'customer_id': rec.customer_name_id.id,
                'used_point': rec.min_point,
                'problem_ticket': rec.category.id,
                'date': fields.Datetime.now(),
            })

            # Recompute total used_point dari semua transaksi customer & produk ini
            rec.points_id._compute_total_min_points()

            rec.message_post(
                body=f"Poin sebanyak {rec.min_point} telah dikurangi.",
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
    
    # track state default (misal: 'Submit')
    def default_get(self, fields):
        defaults = super().default_get(fields)
        is_customer = self.env.user.has_group('tickets.group_customer_only')
        if is_customer:
            new_state = self.env['state.name'].search([('name', '=', 'Submit')], limit=1)
            if new_state:
                defaults['states'] = new_state.id
        return defaults
    
    @api.constrains('states')
    def _check_states_by_customer(self):
        for rec in self:
            if self.env.user.has_group('tickets.group_customer_only'):
                if rec.states and rec.states.name not in ['Submit']:
                    raise ValidationError("Customer tidak diizinkan mengubah status tiket.")

    @api.constrains('submitted_date', 'expired_ticket')
    def _check_ticket_expiry(self):
        for rec in self:
            if rec.submitted_date and rec.expired_ticket:
                if rec.submitted_date > rec.expired_ticket:
                    raise ValidationError("Ticket Available anda telah kadaluarsa.")

    # @api.constrains('category', 'name')
    # def _categ_empty(self):
    #     for rec in self:
    #         if not rec.category:
    #             raise ValidationError("Field Category Kosong")


    # point 0 constraint            
    @api.constrains('points_id', 'category', 'min_point')
    def _point_validation(self):
        for record in self:
            if record.points_id and record.points_id.name <= 0:
                raise ValidationError("Ticket Available anda bernilai 0 tidak dapat membuat tiket.")

    @api.onchange('points_id', 'category')
    def _onchange_point_validation(self):
        for rec in self:
            if rec.points_id and rec.points_id.name <= 0:
                return {
                    'warning': {
                        'title': "Poin Tidak Cukup",
                        'message': "Poin customer bernilai 0. Tidak bisa membuat tiket."
                }
            }

    @api.model
    def create(self, vals):
        if not vals.get('customer_name_id') and user.has_group('tickets.group_customer_only'):
            vals['customer_name_id'] = user.partner_id.id

        user = self.env.user
        customer_id = vals.get('customer_name_id')
        category_id = vals.get('category')
        definition_id= vals.get('definition')
        min_point = vals.get('min_point', 0)

        # if customer_id:
        #     # Cek apakah customer sudah punya tiket dengan status id 1 (Submit) atau 2 (Progress)
        #     existing_tickets = self.search([
        #         ('customer_name_id', '=', customer_id),
        #         ('states', 'in', [1, 2])
        #     ])
        #     if existing_tickets:
        #         raise ValidationError(
        #             _("Anda masih memiliki tiket yang belum selesai")
        #         )
            
        if self.submitted_date and self.expired_ticket:
            if self.submitted_date > self.expired_ticket:
                raise ValidationError("Ticket Available anda telah kadaluarsa.")

        # Validasi: Customer harus dipilih
        if not customer_id:
            raise ValidationError("Customer field is Empty, please fill the field first.")

        # Validasi: Kategori harus diisi
        if not category_id:
            raise ValidationError("Field Category is Empty, please fill the field first.")

        if not definition_id :
            raise ValidationError("Field Problem Definition is Empty, please fill the field first.")

        # Cari point.name berdasarkan customer + category (product_point)
        point_obj = self.env['point.name'].search([
            ('customer_id', '=', customer_id),
            ('product_point', '=', category_id)
        ], limit=1)

        # Kalau tidak ditemukan, GAGAL buat tiket (dilarang create baru di sini)
        if not point_obj:
            raise ValidationError("Customer belum memiliki alokasi tiket poin untuk kategori ini.")

        if point_obj.name <= 0.00:
            raise ValidationError(
                _("Poin customer untuk kategori ini adalah %(balance)s. Tidak dapat membuat tiket baru.", 
                  balance=point_obj.name)
            )

        # Set ke field points_id
        vals['points_id'] = point_obj.id

        # Buat nomor tiket jika masih default
        # if vals.get('name', 'Submit') == 'Submit':
        #     vals['name'] = self.env['ir.sequence'].next_by_code('ticket.name') or '/'

        # Buat tiket
        record = super().create(vals)

        if record.point_value == 0.00:
            raise ValidationError("Customer Have No Ticket Available Please Contact Sales To Confirm Ticket")

        # Buat nomor tiket baru setelah semua validasi lulus
        # if record.name in (False, 'Submit', '/'):
        #     record.name = self.env['ir.sequence'].next_by_code('ticket.name') or '/'

        # Validasi: point cost tidak boleh negatif
        if record.min_point < 0:
            raise ValidationError("Point cost tidak boleh bernilai negatif.")

        # Validasi: apakah cukup poin
        if record.points_id.name < record.min_point:
            raise ValidationError("Poin customer tidak cukup untuk membuat tiket ini.")

        # Kurangi poin customer
        record.points_id.name -= record.min_point

        # Catat transaksi pemotongan poin
        # self.env['point.transaction'].create({
        #     'point_id': record.points_id.id,
        #     'ticket_id': record.id,
        #     'customer_id': record.customer_name_id.id,
        #     'used_point': record.min_point,
        #     'problem_ticket': record.category.id,
        #     'date': fields.Datetime.now(),
        # })

        # Chatter
        # record.message_post(
        #     body="Tiket berhasil dibuat dan poin dikurangi sebanyak %s." % record.min_point,
        #     message_type='comment',
        #     subtype_xmlid='mail.mt_note'
        # )
        
        # Update atau buat avg.ticket otomatis
        record._update_avg_ticket_auto()

        return record


    # api one change
    @api.depends("min_point")
    def onchange_states(self):
        print("Customer tidak boleh membuat tiket langsung dalam status lain selain status 'Submit'.")
        submit_state = self.env['state.name'].search([('name', '=', '1')], limit=1)
        admin = self.env.user.has_group('tickets.group_admin')

        if admin and self.states.id == submit_state.id:
            self.states = False
            print("Customer tidak boleh membuat tiket langsung dalam status lain selain status 'Submit'.")
    
    # === Constraints ===

    @api.constrains('customer_name_id')
    def _check_required_fields(self):
        for rec in self:
            if not rec.customer_name_id:
                raise ValidationError("Field Customer Name tidak boleh kosong.")
    
    # @api.onchange('states')
    # def onchange_states(self):
    #         for record in self:
    #             if record.states.id == 2:
    #                 print("record berhasil")
    
    # kanban states
    @api.onchange('states')
    def onchange_statess(self):
        # print("record berhasil di submit********************************************************************************************************************************************************8")
        # print(self.states.name)
        for record in self:
            if record.states.id == 2:
                print(self.states.name)

    def state_submit(self):
        # for ticket in self:
            self.states = 1  # Atur state (misalnya 'Submitted') 
            print("record berhasil di submit********************************************************************************************************************************************************8")
            # Ambil template email berdasarkan ID eksternal
            # template = self.env.ref('tickets.email_template_ticket_update', raise_if_not_found=False)
            
            # # Kirim email jika templatenya ditemukan
            # if template:
            #     template.send_mail(ticket.name, force_send=True)

    def state_progress(self):
        self.states = 2
        self.progress_date = fields.Datetime.now(self)
        print(self.points_id)
        for record in self:
            if record.point_value < 1:
                raise ValidationError("Ticket Available anda bernilai 0 tidak dapat membuat tiket.")

    def state_finish(self):
        self.states = 3
        self.finish_date = fields.Datetime.now(self)

    def state_cancel(self):
        self.states = 4
    
    # problem_id = fields.Many2one(comodel_name='problem.name', string='Problems')

    definition = fields.Many2one(comodel_name='definition.name', string='Problem Definition', domain="[('service_title', '=', category)]")
    remark_name = fields.Char(string='Remarks', related="definition.remark",
    store=True)
    
    @api.onchange('definition')
    def _onchange_definition_remark(self):
        if self.definition:
            self.remark_name = self.definition.remark
        else:
            self.remark_name = 'None'

    problem_description = fields.Char(string='Problem Description')
    # ticket_id = fields.Many2one(comodel_name='ticket.name', tracking=True,
    #     store=True)
    photo_prove = fields.Image('Photo Prove Attacthment', max_width=400, max_height=800, attachment=True, store=True, tracking=True)
    
    # def _post_chatter(self, msg):
        
    #     self.message_post(
    #         body=msg,
    #         message_type='comment',
    #         subtype_xmlid='mail.mt_note'
    #     )

    # def create(self, vals):
    #     rec = super().create(vals)
    #     if vals.get('problem_id') or vals.get('problem_description'):
    #         msg = (
    #             f"➕ Problem Description ditambahkan:<br/>"
    #             f"<b>Name:</b> {rec.problem_id or '-'}<br/>"
    #             f"<b>Description:</b> {rec.problem_description or '-'}<br/>"
    #         )
    #     rec._post_chatter(msg)
    #     return rec

    # def unlink(self):
    #     for rec in self:
    #         rec._post_chatter(f"🗑️ Problem Description dihapus: <b>{rec.problem_id}</b>")
            
    #     return super().unlink()\
    
    def write(self, vals):
        # --- Persiapan (dari write #1 dan #2) ---
        new_state = None
        if 'states' in vals and vals['states']:
            new_state = self.env['state.name'].browse(vals['states'])
        
        is_customer_group = self.env.user.has_group('tickets.group_customer_only')
        
        messages = [] # Untuk chatter

        # --- Validasi & Persiapan Chatter (Harus sebelum super().write) ---
        for record in self:
            
            # --- Logika Keamanan (dari write #1) ---
            # Jika user termasuk group customer dan ingin ubah state apa pun → tolak
            if is_customer_group and 'states' in vals:
                raise ValidationError("Customer tidak diperbolehkan mengubah status tiket.")

            # --- LOGIKA BARU: Tidak bisa kembali ke Submit ---
            # Cek jika *siapapun* mencoba memindahkan ke 'Submit'
            if is_customer_group:
                # Dan mereka mencoba memindahkan ke 'Submit'
                if new_state and new_state.name == 'Submit':
                    # Dan state lamanya adalah salah satu dari ini
                    if record.states.name in ['Progress', 'Finish', 'Cancel']:
                        raise ValidationError(
                            _("Tiket yang sudah di-Proses, Selesai, atau Batal tidak bisa dikembalikan ke Submit.")
                        )

            # --- Logika Chatter (dari write #2) ---
            msg_parts = []

            # Logika 'problem_id' (Anda comment di kode Anda, jadi saya comment juga)
            # if 'problem_id' in vals and vals['problem_id'] != record.problem_id:
            #     a = self.env['problem.name'].search([
            #         ('id', '=', vals['problem_id'])]).name
            #     msg_parts.append(f"<b>Name:</b> '{record.problem_id.name}' → '{a}'")

            if 'problem_description' in vals and vals['problem_description'] != record.problem_description:
                msg_parts.append(
                    f"<b>Description:</b> '{record.problem_description}' → '{vals['problem_description']}'"
                )

            if msg_parts:
                message = (
                    f"✏️ Problem Description diperbarui:<br/> ✏️" +
                    "<br/>".join(msg_parts)
                )
                # Menyimpan record-nya, bukan cuma nama, agar bisa post chatter
                messages.append((record, message)) 

        # --- Panggil super().write() HANYA SATU KALI ---
        res = super().write(vals)

        # --- Logika Setelah Simpan (dari write #2 dan #3) ---

        # Logika dari write #3 (Avg Ticket)
        # 'self' di sini adalah semua record, jadi panggil _update_avg_ticket_auto()
        if res:
            self._update_avg_ticket_auto()

        # Logika dari write #2 (Posting Chatter)
        if messages:
            for rec, message in messages: # Loop dari messages yang sudah disiapkan
                rec.message_post(
                    body=message,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )

        return res

    def _update_avg_ticket_auto(self):
        """Auto update or create avg.ticket record when ticket changes"""
        for rec in self:
            customer = rec.customer_name_id
            if not customer:
                continue

            avg_model = self.env['avg.ticket']
            avg_rec = avg_model.search([('customer_id', '=', customer.id)], limit=1)

            # Hitung ulang data customer tersebut
            vals = avg_model.compute_avg_for_customer(customer.id)
            vals.update({
                'customer_id': customer.id,
                'last_computed': fields.Datetime.now(),
            })

            if avg_rec:
                avg_rec.write(vals)
            else:
                # context tambahan agar create() di avg.ticket tidak diblok oleh UserError
                avg_model.with_context(from_ticket_auto=True).create(vals)

    @api.depends('complexity', 'progress_date', 'finish_date', 'manual_min_point')
    def _compute_min_point(self):
        for rec in self:
            # Check for a manual override first
            if rec.manual_min_point:
                rec.min_point = rec.manual_min_point
                continue
            
            # Original computation logic if no manual override
            rec.min_point = 0.0
            if not rec.complexity or not rec.progress_date:
                continue

            complexity_map = {'none':0.0, 'low':1.0, 'medium':1.5, 'high':2.0}
            complexity_value = complexity_map.get(rec.complexity, 0.0)

            if rec.finish_date:
                delta_hours = (rec.finish_date - rec.progress_date).total_seconds() / 3600.0
            else:
                delta_hours = (fields.Datetime.now() - rec.progress_date).total_seconds() / 3600.0

            duration_points = math.ceil(delta_hours / 24.0)

            rec.min_point = complexity_value + duration_points


    def _inverse_min_point(self):
        for rec in self:
            # The value the user typed in 'min_point' is now written to 'manual_min_point'
            rec.manual_min_point = rec.min_point
