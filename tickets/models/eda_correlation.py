# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import numpy as np
import pandas as pd
from datetime import datetime # No need for timedelta here

# Make sure pandas is installed in your Odoo environment:
# pip install pandas

class EDACorrelation(models.Model):
    _name = 'eda.correlation'
    _description = 'Correlation Matrix Between Average Ticket Variables'
    _order = 'calculation_date desc'
    _rec_name = 'calculation_date'

    calculation_date = fields.Datetime(string='Calculation Date', default=fields.Datetime.now, readonly=True)

    # === Define all 21 correlation fields ===
    corr_ticket_priority = fields.Float('Corr(Ticket Count vs Avg Priority)', digits=(6, 3))
    corr_ticket_complexity = fields.Float('Corr(Ticket Count vs Avg Complexity)', digits=(6, 3))
    corr_ticket_response = fields.Float('Corr(Ticket Count vs Avg Response Time)', digits=(6, 3))
    corr_ticket_resolution = fields.Float('Corr(Ticket Count vs Avg Resolution Time)', digits=(6, 3))
    corr_ticket_point = fields.Float('Corr(Ticket Count vs Avg Point)', digits=(6, 3))
    corr_ticket_rating = fields.Float('Corr(Ticket Count vs Avg Rating)', digits=(6, 3))

    corr_priority_complexity = fields.Float('Corr(Avg Priority vs Avg Complexity)', digits=(6, 3))
    corr_priority_response = fields.Float('Corr(Avg Priority vs Avg Response Time)', digits=(6, 3))
    corr_priority_resolution = fields.Float('Corr(Avg Priority vs Avg Resolution Time)', digits=(6, 3))
    corr_priority_point = fields.Float('Corr(Avg Priority vs Avg Point)', digits=(6, 3))
    corr_priority_rating = fields.Float('Corr(Avg Priority vs Avg Rating)', digits=(6, 3))

    corr_complexity_response = fields.Float('Corr(Avg Complexity vs Avg Response Time)', digits=(6, 3))
    corr_complexity_resolution = fields.Float('Corr(Avg Complexity vs Avg Resolution Time)', digits=(6, 3))
    corr_complexity_point = fields.Float('Corr(Avg Complexity vs Avg Point)', digits=(6, 3))
    corr_complexity_rating = fields.Float('Corr(Avg Complexity vs Avg Rating)', digits=(6, 3))

    corr_response_resolution = fields.Float('Corr(Avg Response Time vs Avg Resolution Time)', digits=(6, 3))
    corr_response_point = fields.Float('Corr(Avg Response Time vs Avg Point)', digits=(6, 3))
    corr_response_rating = fields.Float('Corr(Avg Response Time vs Avg Rating)', digits=(6, 3))

    corr_resolution_point = fields.Float('Corr(Avg Resolution Time vs Avg Point)', digits=(6, 3))
    corr_resolution_rating = fields.Float('Corr(Avg Resolution Time vs Avg Rating)', digits=(6, 3))

    corr_point_rating = fields.Float('Corr(Avg Point vs Avg Rating)', digits=(6, 3))

    # === [PRIVATE METHOD] Logic for Calculating the Matrix ===
    def _calculate_matrix(self):
        """Calculates the Pearson correlation matrix and returns a dictionary of results."""
        AvgTicket = self.env['avg.ticket']
        # Fetch necessary average data per customer
        avg_data = AvgTicket.search_read([], fields=[
            'ticket_count', 'avg_priority', 'avg_complexity',
            'avg_response_time', 'avg_resolution_time',
            'avg_point', 'avg_rating'
        ])

        if not avg_data:
            return False # Return False if no average data exists

        # Convert to Pandas DataFrame
        df = pd.DataFrame([{
            'ticket_count': rec['ticket_count'],
            'avg_priority': rec['avg_priority'],
            'avg_complexity': rec['avg_complexity'],
            'avg_response_time': rec['avg_response_time'],
            'avg_resolution_time': rec['avg_resolution_time'],
            'avg_point': rec['avg_point'],
            'avg_rating': rec['avg_rating'],
        } for rec in avg_data])

        if df.empty:
            return False # Return False if DataFrame is empty

        df = df.fillna(0) # Replace potential NaN values with 0
        corr_matrix = df.corr(method='pearson') # Calculate Pearson correlation

        # Helper function to safely get correlation values
        def safe_corr(a, b):
            try:
                val = corr_matrix.loc[a, b]
                # Ensure the value is a standard float, handle NaN
                return float(val) if pd.notna(val) else 0.0
            except KeyError:
                return 0.0
            except Exception:
                return 0.0

        # Map correlation results to model fields
        return {
            'corr_ticket_priority': safe_corr('ticket_count', 'avg_priority'),
            'corr_ticket_complexity': safe_corr('ticket_count', 'avg_complexity'),
            'corr_ticket_response': safe_corr('ticket_count', 'avg_response_time'),
            'corr_ticket_resolution': safe_corr('ticket_count', 'avg_resolution_time'),
            'corr_ticket_point': safe_corr('ticket_count', 'avg_point'),
            'corr_ticket_rating': safe_corr('ticket_count', 'avg_rating'),

            'corr_priority_complexity': safe_corr('avg_priority', 'avg_complexity'),
            'corr_priority_response': safe_corr('avg_priority', 'avg_response_time'),
            'corr_priority_resolution': safe_corr('avg_priority', 'avg_resolution_time'),
            'corr_priority_point': safe_corr('avg_priority', 'avg_point'),
            'corr_priority_rating': safe_corr('avg_priority', 'avg_rating'),

            'corr_complexity_response': safe_corr('avg_complexity', 'avg_response_time'),
            'corr_complexity_resolution': safe_corr('avg_complexity', 'avg_resolution_time'),
            'corr_complexity_point': safe_corr('avg_complexity', 'avg_point'),
            'corr_complexity_rating': safe_corr('avg_complexity', 'avg_rating'),

            'corr_response_resolution': safe_corr('avg_response_time', 'avg_resolution_time'),
            'corr_response_point': safe_corr('avg_response_time', 'avg_point'),
            'corr_response_rating': safe_corr('avg_response_time', 'avg_rating'),

            'corr_resolution_point': safe_corr('avg_resolution_time', 'avg_point'),
            'corr_resolution_rating': safe_corr('avg_resolution_time', 'avg_rating'),

            'corr_point_rating': safe_corr('avg_point', 'avg_rating'),
            'calculation_date': fields.Datetime.now(), # Record calculation time
        }

    # === [PUBLIC METHOD 1] Triggered by Odoo Action (SINGLETON WRITE) ===
    def compute_and_save_correlation(self, records=None): # Add records=None to handle potential extra arg
        """
        Calculate correlation matrix. Update the existing record (overwrite)
        or create a new one if none exists (Singleton Pattern).
        """
        vals = self._calculate_matrix()

        if not vals:
            raise ValidationError("No data found in 'avg.ticket' or data is empty. Cannot compute correlation.")

        # --- Singleton Update/Create Logic ---
        # Find the oldest existing record
        record = self.search([], limit=1, order='id asc')

        if record:
            # Update the existing record
            record.write(vals)
            # Clean up potential duplicate records (pass context)
            self.search([('id', '!=', record.id)]).with_context(skip_unlink_validation=True).unlink()
        else:
            # Create a new record if none exists
            record = self.create(vals)

        # Return success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Correlation matrix calculated and saved successfully (ID: %s).' % record.id,
                'sticky': False,
            }
        }

    # === [PUBLIC METHOD 2] Called by JavaScript/OWL ===
    @api.model
    def get_latest_correlation_data(self):
        """Fetches the latest correlation data for the OWL dashboard."""
        corr_record = self.search([], order='calculation_date desc', limit=1)

        if not corr_record:
            return {} # Return empty dict if no record found

        # Read all float fields (correlation values)
        fields_to_read = [name for name, field in self._fields.items() if field.type == 'float']
        data = corr_record.read(fields=fields_to_read)[0] # Read the first record
        data.pop('id', None) # Remove the internal ID

        return data

    # === Prevent Manual Deletion ===
    def unlink(self):
        """Override unlink to prevent manual deletion but allow internal cleanup."""
        # Allow deletion if the special context key is passed
        if self.env.context.get('skip_unlink_validation'):
            # Use proper super() call for inheritance
            return super(EDACorrelation, self).unlink()
        # Raise error for manual deletion attempts
        raise ValidationError("Correlation result records cannot be deleted manually!")