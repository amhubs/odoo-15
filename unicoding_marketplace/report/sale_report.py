# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    unicoding_marketplace_id = fields.Many2one('unicoding.marketplace', 'Unicoding marketplace ID', readonly=True)


    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['unicoding_marketplace_id'] = ", s.unicoding_marketplace_id as unicoding_marketplace_id"
        groupby += ', s.unicoding_marketplace_id'
        return super()._query(with_clause=with_clause, fields=fields, groupby=groupby, from_clause=from_clause)


