# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    unicoding_marketplace_id = fields.Many2one('unicoding.marketplace', 'Unicoding marketplace ID', readonly=True)

    unicoding_opencart_status_id = fields.Many2one(
        string='Opencart Order Status',
        comodel_name='unicoding.opencart.status',
        readonly=True
    )





    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['unicoding_opencart_status_id'] = ", s.unicoding_opencart_status_id as unicoding_opencart_status_id"
        groupby += ', s.unicoding_opencart_status_id'


        return super()._query(with_clause=with_clause, fields=fields, groupby=groupby, from_clause=from_clause)


