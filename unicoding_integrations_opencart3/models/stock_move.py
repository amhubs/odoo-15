# -*- coding: utf-8 -*-


from odoo import SUPERUSER_ID, _, api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def write(self, vals):
        result = super().write(vals=vals)

        if 'state' in vals and vals['state'] == 'done':
            for move in self:
                if move.product_tmpl_id.unicoding_marketplace_id and move.product_tmpl_id.opencartid and move.product_tmpl_id.unicoding_marketplace_id.allow_update_price_oc and not self.env.context.get(
                        'no_send_status_update', False) and ( move.picking_type_id.code in ['incoming', 'outgoing', 'mrp_operation'] or move.scrapped):

                    total_available_quantity = 0
                    for sq in self.env['stock.quant'].search([('product_tmpl_id', '=', move.product_tmpl_id.id), ('quantity', '>', 0),('location_id.usage', '=', 'internal')]):
                        total_available_quantity += sq.quantity - sq.reserved_quantity


                    product_id = move.product_id
                    available_quantity = 0
                    for sq in self.env['stock.quant'].search(
                            [('product_id', '=', product_id.id), ('quantity', '>', 0),
                             ('location_id.usage', '=', 'internal')]):
                        available_quantity += sq.quantity - sq.reserved_quantity

                    self.env['unicoding.marketplace'].browse(
                        move.product_tmpl_id.unicoding_marketplace_id.id).opencart_update_product(
                        move.product_tmpl_id.opencartid,
                        {'quantity': total_available_quantity,
                         'options': ','.join(
                             product_id.product_template_attribute_value_ids.mapped('attribute_id.name')),
                         'values': ','.join(product_id.product_template_attribute_value_ids.mapped('name')),
                         'option_qty': available_quantity})
        return result

