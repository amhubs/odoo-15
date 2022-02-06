

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class UnicodingOpencartStatus(models.Model):
    _name = 'unicoding.opencart.status'
    _description = 'Opencart statuses'

    opencartid = fields.Char('OpenCart ID')
    unicoding_marketplace_id = fields.Many2one(
        string='Unicoding marketplace ID',
        comodel_name='unicoding.marketplace',
        ondelete='restrict',
        copy=False,
    )

    name = fields.Char(
        string='Name',
        store=True,
        readonly=False,
        translate = True,
    )


    status = fields.Selection([
        ('AWAITING_PROCESSING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('PAID', 'Paid'),
        ('SHIPPED', 'Shipped'),
        ('CANCELLED', 'Cancelled'),
        ('DELIVERED', 'Delivered'),
        ('RETURNED', 'Returned'),
        ('REFUNDED', 'Refunded'),
        ('COMPLETE', 'Complete'),
    ], string='Statuses', index=True)


