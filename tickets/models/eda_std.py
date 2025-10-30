from odoo import models, fields, api
import statistics
from datetime import datetime
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class EDATicketSTDStats(models.Model):
    _name = 'eda.std'
    _description = 'Global Standard Deviation Results (EDA History)'
    _order = 'calculation_date desc'
    _rec_name = 'calculation_date'

    # === FIELDS ===
    calculation_date = fields.Datetime(
        string='Calculation Date',
        readonly=True,
        default=fields.Datetime.now,
    )
    std_priority_score = fields.Float('STD Priority Score (1–3)', readonly=True)
    std_response_time = fields.Float('STD Response Time (Hours)', readonly=True)
    std_resolution_time = fields.Float('STD Resolution Time (Hours)', readonly=True)
    std_min_point = fields.Float('STD Ticket Point Usage', readonly=True)
    std_complexity_score = fields.Float('STD Complexity Score (0–2)', readonly=True)
    std_rating_score = fields.Float('STD Rating Score (1–5)', readonly=True)

    # === MAPPING CONSTANTS ===
    COMPLEXITY_MAP = {'low': 1.0, 'medium': 1.5, 'high': 2.0, 'none': 0.0} # Tambahkan 'none' jika ada
    PRIORITY_MAP = {'low': 1.0, 'medium': 2.0, 'high': 3.0}
    RATING_MAP = {'worst': 1, 'bad': 2, 'medium': 3, 'good': 4, 'excellent': 5, 'no': 0} # Tambahkan 'no' jika ada

    @api.model
    def create_default_if_empty(self):
        """Ensure at least one record exists (auto heal if deleted)."""
        if not self.search([], limit=1):
            _logger.info("No eda.std record found, creating default one.")
            self.create({
                'calculation_date': fields.Datetime.now(),
                'std_priority_score' : 0.0,
                'std_response_time': 0.0,
                'std_resolution_time': 0.0,
                'std_min_point': 0.0,
                'std_complexity_score': 0.0,
                'std_rating_score': 0.0,
            })

    # === UTILITIES ===
    @api.model
    def _safe_pstdev(self, data):
        """Hitung STD populasi dengan aman (return 0 kalau data < 2)."""
        # Pastikan semua data adalah float
        cleaned_data = [float(d) for d in data if d is not None]
        if len(cleaned_data) < 2:
            return 0.0
        try:
            return statistics.pstdev(cleaned_data)
        except statistics.StatisticsError:
            return 0.0

    @api.model
    def _gather_ticket_values(self):
        """Ambil data mentah dari model ticket.name untuk dihitung STD-nya."""
        Ticket = self.env['ticket.name']
        
        # Ambil semua tiket (sesuai logika asli Anda)
        tickets = Ticket.search([])
        _logger.info(f"Gathering data from {len(tickets)} tickets for STD calculation.")

        response_times = []
        resolution_times = []
        min_points = []
        complexity_scores = []
        priority_scores = []
        ratings = []

        for t in tickets:
            # ==========================================================
            # PERBAIKAN: Hapus 'if t.field:' agar nilai 0.0 ikut terhitung.
            # Gunakan 't.field or 0.0' untuk menangani nilai None/False.
            # ==========================================================

            # Response Time (dari field compute store=True Anda)
            response_times.append(float(t.response_time_hours or 0.0))

            # Resolution Time (hanya jika tiket sudah selesai)
            if t.progress_date and t.finish_date:
                delta = t.finish_date - t.progress_date
                resolution_times.append(delta.total_seconds() / 3600.0)

            # Ticket Usage Point
            min_points.append(float(t.min_point or 0.0))
            
            # ==========================================================
            # Akhir Perbaikan
            # ==========================================================

            # Complexity (konversi)
            if t.complexity in self.COMPLEXITY_MAP:
                complexity_scores.append(self.COMPLEXITY_MAP[t.complexity])

            # Priority (konversi)
            if t.priority in self.PRIORITY_MAP:
                priority_scores.append(self.PRIORITY_MAP[t.priority])

            # Rating (konversi)
            if t.customer_rating in self.RATING_MAP:
                ratings.append(self.RATING_MAP[t.customer_rating])

        _logger.info(f"Data points collected: Response={len(response_times)}, Resolution={len(resolution_times)}, Points={len(min_points)}")

        return {
            'tickets': tickets,
            'response_times': response_times,
            'resolution_times': resolution_times,
            'min_points': min_points,
            'complexity_scores': complexity_scores,
            'priority_scores': priority_scores,
            'ratings': ratings,
        }

    # === MAIN ACTION ===
    def action_recalculate_std(self):
        """Hitung STD baru dan buat record history baru."""
        _logger.info("Action 'action_recalculate_std' triggered.")
        data = self._gather_ticket_values()

        if not data['tickets']:
            raise ValidationError("Tidak dapat menghitung STD: Tidak ada data tiket ditemukan di sistem.")

        std_values = {
            'std_priority_score': self._safe_pstdev(data['priority_scores']),
            'std_response_time': self._safe_pstdev(data['response_times']),
            'std_resolution_time': self._safe_pstdev(data['resolution_times']),
            'std_min_point': self._safe_pstdev(data['min_points']),
            'std_complexity_score': self._safe_pstdev(data['complexity_scores']),
            'std_rating_score': self._safe_pstdev(data['ratings']),
            'calculation_date': fields.Datetime.now(),
        }
        
        _logger.info(f"New STD values calculated: {std_values}")

        # Membuat record baru untuk history
        record = self.create(std_values)
        self.env.cr.commit() # Commit agar data langsung tersimpan
        _logger.info(f"New eda.std record created with ID: {record.id}")

        # Mengembalikan action untuk membuka record baru yang baru saja dibuat
        return {
            'type': 'ir.actions.act_window',
            'name': 'STD Calculation Result',
            'res_model': 'eda.std',
            'view_mode': 'form',
            'res_id': record.id,
            'target': 'current',
        }