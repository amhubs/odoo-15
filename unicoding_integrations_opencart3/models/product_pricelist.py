from odoo import api, fields, models

class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    opencartid = fields.Char('OpenCart ID')
