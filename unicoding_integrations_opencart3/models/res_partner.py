from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    opencartid = fields.Char('OpenCart ID')
