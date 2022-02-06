# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
import json



class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def marketplace_update_product(self, quantity):
        if self.product_tmpl_id.unicoding_marketplace_id and self.product_tmpl_id.opencartid and self.product_tmpl_id.unicoding_marketplace_id.allow_update_price_oc and not self.env.context.get(
                'no_send_status_update', False):
            total_available_quantity = quantity
            product_id = self.product_id
            available_quantity = 0
            for sq in self.env['stock.quant'].search(
                    [('product_id', '=', product_id.id), ('quantity', '>', 0),
                     ('location_id.usage', '=', 'internal')]):
                available_quantity += sq.quantity - sq.reserved_quantity

            self.env['unicoding.marketplace'].browse(
                self.product_tmpl_id.unicoding_marketplace_id.id).opencart_update_product(
                self.product_tmpl_id.opencartid,
                {'quantity': total_available_quantity,
                 'options': ','.join(
                     product_id.product_template_attribute_value_ids.mapped('attribute_id.name')),
                 'values': ','.join(product_id.product_template_attribute_value_ids.mapped('name')),
                 'option_qty': available_quantity})

    def write(self, vals):
        result = super(StockQuant, self).write(vals)

        if 'inventory_quantity' in vals.keys():
            self.marketplace_update_product(self.product_tmpl_id.qty_available)
        if 'reserved_quantity' in vals.keys():
            self.marketplace_update_product(self.product_tmpl_id.qty_available - vals['reserved_quantity'])

        return result

    # @api.model
    # def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
    #                                in_date=None):
    #     result = super()._update_available_quantity(product_id=product_id, location_id=location_id, quantity=quantity,
    #                                        lot_id=lot_id, package_id=package_id, owner_id=owner_id, in_date=in_date)
    #     if location_id.usage in ('customer', 'production'):
    #         print("%s %s " % (product_id.name, location_id.name))
    #         print("_update_available_quantity %s" % quantity)
    #         self.marketplace_update_product(self.product_tmpl_id.qty_available)
    #     elif location_id.usage in ('supplier'):
    #         print("%s %s " % (product_id.name, location_id.name))
    #         print("_update_available_quantity2 %s" % quantity)
    #         self.marketplace_update_product(self.product_tmpl_id.qty_available)
    #
    #     return result