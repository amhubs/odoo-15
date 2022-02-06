from odoo import _, api, fields, models
import requests
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)
import base64
URLOPEN_TIMEOUT = 10
#import werkzeug
import html
import threading

class UnicodingMarketplace(models.Model):
    _inherit = 'unicoding.marketplace'
    _access_token = fields.Char(string="access_token")

    opencart_webhookurl = fields.Char(string="Webhook URL", compute='_compute_opencart_webhookurl', store=False)
    api_username = fields.Char(string="API Name")
    api_key = fields.Text(string="API Key")

    def _compute_opencart_webhookurl(self):
        for opencart_id in self:
            opencart_id.opencart_webhookurl = "%s/unicoding-marketplace/opencart/%d" % (self.env['ir.config_parameter'].sudo().get_param('web.base.url'), opencart_id.id)

    def opencart_notification(self, message):
        channel = self.env['mail.channel'].browse(
            self.env.ref('unicoding_integrations_opencart3.unicoding_marketplace_opencart_channel').id)

        channel.message_post(attachment_ids=[], body=message, content_subtype='html',
                             message_type='comment', partner_ids=[],
                             channel_ids=[channel.id],
                             email_from=self.env.user.partner_id.email, author_id=self.env.ref(
                'unicoding_integrations_opencart3.unicoding_marketplace_user_opencart_partner').id)



    def opencart_get_token(self):
        for opencart_id in self:
            result = opencart_id.opencart_request("%s/index.php?route=api/login&api_token=" % (opencart_id.url),{'username': opencart_id.api_username, 'key': opencart_id.api_key}, method='post')
            if result:
                opencart_id._access_token = result["api_token"] if "api_token" in result.keys() else result["token"]
                opencart_id._token_datetime = datetime.now()
                return result
            else:
                return {}
    
    def opencart_sync_products(self, products=[]):
        for opencart_id in self:
            if len(products):
                result = opencart_id.opencart_request("%s/index.php?route=api/integrations/syncproducts" % (opencart_id.url), {'api_token': opencart_id._access_token, 'token': opencart_id._access_token, 'products': products})
                if result:
                    return result
            else:
                return {}


    def opencart_get_orders(self):
        for opencart_id in self:
            result = opencart_id.opencart_request("%s/index.php?route=api/integrations/orders" % (opencart_id.url),
                                              {'api_token': opencart_id._access_token, 'token': opencart_id._access_token, 'date': self.last_item_date.strftime("%Y-%m-%d"), 'limit': opencart_id.page_orders_num})
            if result:
                return result['orders']
            else:
                return {}


    def opencart_get_products(self):
        for opencart_id in self:
            result = opencart_id.opencart_request("%s/index.php?route=api/integrations/products" % (opencart_id.url), {'api_token': opencart_id._access_token, 'token': opencart_id._access_token, 'page': opencart_id.pages, 'limit': opencart_id.page_products_num})
            if result:
                return result['products']
            else:
                return {}

    def opencart_get_categories(self, opencart_category_id = 0):
        for opencart_id in self:
            result = opencart_id.opencart_request("%s/index.php?route=api/integrations/categories" % (opencart_id.url),
                                              {'api_token': opencart_id._access_token, 'token': opencart_id._access_token, 'category_id': opencart_category_id})
            if result:
                return result['categories']
            else:
                return {}

    def opencart_update_order(self, opencartid, data):
        for opencart_id in self:
            url = "%s/index.php?route=api/integrations/update_order" % (opencart_id.url)
            opencart_id.opencart_get_token()

            params = {
                'api_token': opencart_id._access_token,
                'token': opencart_id._access_token,
                'order_id': opencartid
            }

            params = dict(params, **data)

            threaded_calculation = threading.Thread(target=self.opencart_update, args=(url, params))


            threaded_calculation.start()

    def opencart_update_product(self, opencartid, data):
        for opencart_id in self:
            if not opencart_id.allow_update_price_oc:
                return False
            url = "%s/index.php?route=api/integrations/update_product" % (opencart_id.url)
            opencart_id.opencart_get_token()

            params = {
                'api_token': opencart_id._access_token,
                'token': opencart_id._access_token,
                'product_id': opencartid
            }

            

            params = dict(params, **data)
            threaded_calculation = threading.Thread(target=self.opencart_update, args=(url, params))
            threaded_calculation.start()

    def opencart_update(self, url, params):
        """
        :param url:
        :param opencartid:
        :param params: {'price': 123, 'quantitiy': 12}
        :return:
        """
        with api.Environment.manage():
            try:
                new_cr = self.pool.cursor()
                self = self.with_env(self.env(cr=new_cr))
                for opencart_id in self:

                    result = opencart_id.opencart_request(url, params)
                    if result:
                        opencart_id.message_post(body=_(str(result["success"])), subject=_('Update Opencart'))
                        return result['success']
            except Exception as e:
                _logger.debug(e)
            finally:
                new_cr.close()
            return {}

    def opencart_request(self, url, params={}, method="get"):
        for opencart_id in self:
            headers = {"content-type": "application/x-www-form-urlencoded"}
            try:
                #_logger.info(params)
                #print(params)
                #print(headers)
                if method == "post":
                    response = requests.post(url, data=params, headers=headers)
                else:
                    response = requests.get(url, params=params, headers=headers)
                _logger.info(response.text)
                result = response.json()
                
                
                if result and "error" not in result.keys():
                    return result
                else:
                    opencart_id.message_post(body=_('Failed <%s> %s.' ) % (url, result), subject=_('Issue with Connection'))
            except Exception as e:
                opencart_id.message_post(body=_('Failed <%s> %s ' % (url, str(e))), subject=_('Issue with connection'))
            return False

    def _get_customergroups(self):
        for opencart_id in self:
            result = opencart_id.opencart_request("%s/index.php?route=api/integrations/customergroups" % (opencart_id.url), {'api_token': opencart_id._access_token,'token': opencart_id._access_token})
            if result:
                return result['customergroups']
            else:
                return {}

    def add_coupon(self, name):
        for opencart_id in self:
            ProductTemplate = self.env['product.template'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            coupon_id = ProductTemplate.search([('name', '=', name)], limit=1)

            if not coupon_id:
                coupon_id = ProductTemplate.create({
                    'name': name,
                    'type': 'service',
                    'categ_id': opencart_id.service_categ_id.id,
                    "invoice_policy": "order",
                    'company_id': opencart_id.company_id.id,
                    # 'attribute_line_ids': attribute_line_ids
                })

            return coupon_id.product_variant_id
    def action_sync_odoo_products(self):
        
        super().action_sync_odoo_products()
        

        for opencart_id in self:
            if opencart_id.type != "opencart":
                return False

            ProductTemplate = self.env['product.template'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductProduct = self.env['product.product'].with_context(allowed_company_ids=[opencart_id.company_id.id])

          
            
            
            opencart_id.opencart_get_token()
            
            product_tmpl_ids = ProductTemplate.search([('opencartid', '=', None), ('unicoding_marketplace_id', '=', opencart_id.id)])
            
            try:
                _logger.info(product_tmpl_ids.ids)
                result = opencart_id.opencart_sync_products(product_tmpl_ids.ids)
                _logger.info(result)
                if result:
                    opencart_id.message_post(body=_('Sync products state %s' % (str(result['state'])) ), subject=_('OpenCart sync product status'))
            except Exception:
                pass


            


    def action_sync_products(self):
        super().action_sync_products()
        
        for opencart_id in self:
            if opencart_id.type != "opencart":
                return False

            
            ProductTemplate = self.env['product.template'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductProduct = self.env['product.product'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductAttribute = self.env['product.attribute'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductAttributeValue = self.env['product.attribute.value'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductTemplateAttributeValue = self.env['product.template.attribute.value'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductTemplateAttributeLine = self.env['product.template.attribute.line'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductCategory = self.env['product.category'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductPricelist = self.env['product.pricelist'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductPricelistItem = self.env['product.pricelist.item'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            Partner = self.env['res.partner'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            AccountTax = self.env['account.tax'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ResCountryGroup = self.env['res.country.group'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            StockQuant = self.env['stock.quant'].sudo().with_context(allowed_company_ids=[opencart_id.company_id.id])

            


            opencart_id.opencart_get_token()

            currency_id = opencart_id.currency_id

            customergroups = opencart_id._get_customergroups()

            for object in customergroups:

                res_country_group_id = ResCountryGroup.search([('opencartid', '=', object['customer_group_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)])
                if not res_country_group_id:
                    res_country_group_id = ResCountryGroup.create({
                        'name': object['name'],
                        'opencartid': object['customer_group_id'],
                        'unicoding_marketplace_id': opencart_id.id,
                    })







            products = opencart_id.opencart_get_products()
            

            added_amount = 0
            updated_amount = 0

            for pkey, product in products.items() if isinstance(products, dict) else {}:
                good_is_exists = False
                manufacturer_id = Partner.search(
                    [('opencartid', '=', product['manufacturer']), ('is_company', '=', True), ('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)

                if not manufacturer_id and product['manufacturer']:
                    manufacturer_id = Partner.create({
                        'name': product['manufacturer'],
                        "company_type": 'company',
                        "is_company": True,
                        "opencartid": product['manufacturer'],
                        'unicoding_marketplace_id': opencart_id.id,
                        'property_purchase_currency_id': currency_id.id,
                        'company_id': opencart_id.company_id.id,
                    })

                product_tmpl_id = False
                if product['ean']:
                    product_tmpl_id = ProductTemplate.search(
                        [('barcode', '=', product['ean'])])

                if not product_tmpl_id:
                    product_tmpl_id = ProductTemplate.search(
                        [('opencartid', '=', product['product_id']),
                         ('unicoding_marketplace_id.id', '=', opencart_id.id)]
                    )

                if not product_tmpl_id:

                    product_tmpl_id = ProductTemplate.create({
                        'name': html.unescape(product['name']),
                        'opencartid': product['product_id'],
                        'unicoding_marketplace_id': opencart_id.id,

                        'type': 'product',
                        # 'categ_id': category_id.id,
                        'barcode': product['ean'],
                        'seller_ids':[(0, False, {'name': manufacturer_id.id, 'delay': 1, 'min_qty': 1, 'price': 0,
                                                   'currency_id': currency_id.id})] if manufacturer_id else [],
                        'description': html.unescape(product['description']),
                        # 'attribute_line_ids': attribute_line_ids
                        'opencart_url': "%s/index.php?route=product/product&product_id=%s" % (opencart_id.url, product['product_id']),
                        'default_code': product['model'],
                        "invoice_policy": "order",
                        'company_id': opencart_id.company_id.id,
                    })

                    added_amount += 1
                else:
                    good_is_exists = True

                    product_tmpl_id.write({
                        'name': html.unescape(product['name']),
                        #'barcode': product['ean'],
                        'description': html.unescape(product['description']),
                    })

                    updated_amount +=1

                if product['image'] and opencart_id.sync_product_images:
                    # print("%s/%s" % (opencart_id.url, product['image']))
                    try:
                        image = base64.b64encode(
                            requests.get("%s/image/%s" % (opencart_id.url, product['image'])).content)
                        product_tmpl_id.image_1920 = image
                    except Exception:
                        pass



                category_id = ProductCategory.search([('opencartid', '=', product['category_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)])
                #if not category_id:
                #    category_id = ProductCategory.search([('name', '=', product['category'])], limit=1)
                if not category_id and product['category']:
                    category_id = ProductCategory.create({
                        'name': product['category'],
                        'parent_id': self.env.ref('product.product_category_1').id,
                        'property_cost_method': 'average',
                        'property_valuation': 'real_time',
                        'opencartid': product['category_id'],
                        'unicoding_marketplace_id': opencart_id.id,
                    })

                product_tmpl_id.categ_id = category_id.id

                attribute_ids = []
                value_ids = []
                product_and_qty = {}


                for option in product['options']:

                    attribute_id = ProductAttribute.search([('name', '=', option['name'])])
                    if not attribute_id:
                        attribute_id = ProductAttribute.create({
                            'name': option['name']
                        })

                    for option_value in option['product_option_value']:
                        value_id = ProductAttributeValue.search(
                            [('attribute_id', '=', attribute_id.id), ('name', '=', option_value['name'])], limit=1)
                        if not value_id:
                            value_id = ProductAttributeValue.create(
                                {'name': option_value['name'], 'attribute_id': attribute_id.id})

                        ptal_id = ProductTemplateAttributeLine.search([('product_tmpl_id', '=', product_tmpl_id.id), ('attribute_id', '=', attribute_id.id)], limit=1)
                        if not ptal_id:
                            ptal_id = ProductTemplateAttributeLine.create({
                                'product_tmpl_id': product_tmpl_id.id,
                                'attribute_id': attribute_id.id,
                                'value_ids': [(6, 0, [value_id.id])]
                            })
                        else:
                            ptal_id.write({'value_ids': [(4, value_id.id)]})

                        ptav_id = ProductTemplateAttributeValue.search([('product_tmpl_id', '=', product_tmpl_id.id), ('attribute_id', '=', attribute_id.id), ('product_attribute_value_id', '=', value_id.id)])
                        product_id_ = ProductProduct.search([('product_tmpl_id', '=', product_tmpl_id.id), ('product_template_attribute_value_ids', 'in', ptav_id.ids)], limit=1)
                        if 'quantity' in option_value.keys() and option_value['quantity']:
                            product_and_qty[product_id_.id] = option_value['quantity']

                        value_ids.append(value_id.id)



                    attribute_ids.append(attribute_id.id)



                product_tmpl_id.write({
                        'list_price': product['price'],
                        'default_code': product['model'],
                        'currency_id': currency_id.id
                })

                #combination = ProductTemplateAttributeValue.search( [('attribute_id', 'in', attribute_ids), ('product_tmpl_id', '=',  product_tmpl_id.id), ('product_attribute_value_id', 'in', value_ids)])

                #product_ids = ProductProduct.search([('product_tmpl_id', '=', product_tmpl_id.id), ('product_template_attribute_value_ids', 'in', combination.ids)])

                product_ids = product_tmpl_id.product_variant_ids
                
                #print(product_and_qty)
                for product_id in product_ids:

                    product_id.write({
                        'list_price': product['price'],
                        'currency_id': currency_id.id
                    })



                    for object in product['discounts'] + product['specials']:

                        #res_country_group_id = ResCountryGroup.search([('opencartid', '=', object['customer_group_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)])

                        #
                        # productpricelist_id = ProductPricelist.search([('currency_id', '=', currency_id.id), ('country_group_ids', '=', res_country_group_id.id)])
                        # if not productpricelist_id:
                        #     productpricelist_id = ProductPricelist.create({
                        #         'name': '%s %s (%s)' % (opencart_id.name, res_country_group_id.name, currency_id.name),
                        #         'currency_id': currency_id.id,
                        #         'country_group_ids': [res_country_group_id.id]
                        #     })



                        if object['date_start'] and object['date_start'][:10] == "0000-00-00":
                            object['date_start'] = False
                        if object['date_end'] and object['date_end'][:10] == "0000-00-00":
                            object['date_end'] = False

                        if 'quantity' not in object.keys() or not object['quantity']:
                            object['quantity'] = 0


                        product_pricelist_item_id = ProductPricelistItem.search([('product_tmpl_id', '=',  product_tmpl_id.id),
                                                                       ('date_start', '=',  object['date_start']),
                                                                       ('date_end', '=',  object['date_end']),
                                                                        ('min_quantity', '=',  object['quantity']),
                                                                       ('fixed_price', '=',  object['price']),
                                                                       ('pricelist_id', '=',  opencart_id.pricelist_id.id),
                                                                        ('currency_id', '=', currency_id.id)

                                                                       ])

                        if not product_pricelist_item_id:
                            if not opencart_id.pricelist_id.company_id:
                                opencart_id.pricelist_id.company_id = opencart_id.company_id.id
                            
                            ProductPricelistItem.create(
                                {
                                    'name': product_id.name,
                                    'date_start': object['date_start'],
                                    'date_end': object['date_end'],
                                    'applied_on': '1_product',
                                    'product_tmpl_id': product_tmpl_id.id,
                                    #'product_id': product_id.id,
                                    'fixed_price': object['price'],
                                    'min_quantity': object['quantity'],
                                    'pricelist_id': opencart_id.pricelist_id.id,
                                    'currency_id': currency_id.id
                                    #'sequence': object['priority'],
                                }
                            )
                          



                    #update stock

                    if not good_is_exists:
                        stockquant_id = StockQuant.search([('product_id', '=', product_id.id), ('location_id', '=', opencart_id.location_dest_id.id)])
                        if not stockquant_id and product['quantity']:
                            qty = product['quantity']
                            #print( product_id.product_template_attribute_value_ids.id )
                            if product_id.id in product_and_qty.keys() and product_and_qty[product_id.id]:
                                qty = product_and_qty[product_id.id]
                         
                            StockQuant.with_context(no_send_status_update=True).create({
                                    'product_id': product_id.id,
                                    'location_id': opencart_id.location_dest_id.id,
                                    'quantity': float(qty),
                                    'company_id': opencart_id.company_id.id,
                            })
                    # elif product['quantity']:
                    #     if stockquant_id.available_quantity > float(product['quantity']):
                    #         stockquant_id.write({
                    #             #'quantity': stockquant_id.inventory_quantity + float(product['quantity'])
                    #             'quantity': float(product['quantity'])
                    #         })

            opencart_id.message_post(body=_('PRODUCTS Added: %s, Updated %s Page %s' % (str(added_amount), str(updated_amount), str(opencart_id.pages)) ), subject=_('OpenCart sync status'))
            if not len(products):
                opencart_id.pages = 1
            else:
                opencart_id.pages += 1

    def action_sync_categories(self):
        super().action_sync_categories()

        for opencart_id in self:
            if opencart_id.type != "opencart":
                return False

            opencart_id.opencart_sync_categories()

    def opencart_sync_categories(self, opencart_category_id = 0):
        for opencart_id in self:
            ProductCategory = self.env['product.category'].with_context(allowed_company_ids=[opencart_id.company_id.id])



            opencart_id.opencart_get_token()


            objects = opencart_id.opencart_get_categories(opencart_category_id)
            cats_name = []

            for object in objects:

                category_id = ProductCategory.search(
                    [('opencartid', '=', object['category_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)

                if opencart_category_id:
                    parent_id = ProductCategory.search(
                        [('opencartid', '=', opencart_category_id), ('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)
                else:
                    parent_id = self.env.ref('product.product_category_1')


                if not category_id:

                    category_id = ProductCategory.create({
                        'name': object['name'],
                        'parent_id': parent_id.id,
                        'property_cost_method': 'average',
                        'property_valuation': 'real_time',
                        'opencartid': object['category_id'],
                        'unicoding_marketplace_id': opencart_id.id
                    })
                    cats_name.append(category_id.name)


                opencart_id.opencart_sync_categories(object['category_id'])
            if cats_name:
                opencart_id.message_post(body=_('Added categories "%s"' % (str(cats_name))), subject=_('OpenCart sync status'))
            if not opencart_category_id:
                opencart_id.message_post(body=_('Finished Added categories'), subject=_('OpenCart sync status'))

    def action_sync_check(self):
        for opencart_id in self:
             if opencart_id.opencart_get_token():
                 opencart_id.message_post(
                    body=_(
                        '<div class="text-success">Sussecss getting token %s datetime %s</div>'
                    ) % (opencart_id._access_token, str(opencart_id._token_datetime)),
                    subject=_(
                        '<div class="text-danger">Issue with Online OpenCart</div>'
                    ),
                )


    def opencart_get_orderstatus(self):
        for opencart_id in self:
            params = {
                'api_token': opencart_id._access_token,
                'token': opencart_id._access_token
            }

            headers = {"content-type": "application/x-www-form-urlencoded"}
            try:
                response = requests.get("%s/index.php?route=api/integrations/orderstatus" % (opencart_id.url),
                                        params=params, headers=headers)

                # if response.ok:
                # response = werkzeug.utils.unescape(response.content.decode())
                result = response.json()
                if "error" not in result.keys():
                    return result['items']
                else:
                    opencart_id.message_post(
                        body=_(
                            'Failed to get orderstaus with error %s. See server logs for  more details.'
                        ) % str(result["error"]),
                        subject=_(
                            'Issue with Connection'
                        ),
                    )
            except Exception as e:
                opencart_id.message_post(body=_('Failed to get orderstatus %s' % str(e)),
                                         subject=_('Issue with connection'))

        return []
    def action_getorderstatus(self):
        for opencart_id in self:
            opencart_id.opencart_get_token()
            statues = opencart_id.opencart_get_orderstatus()
            UnicodingOpencartStatus = self.env['unicoding.opencart.status']
            for object in statues:
                status_id = UnicodingOpencartStatus.search(
                    [('opencartid', '=', object['order_status_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)],
                    limit=1)


                # if not status_id:
                #     s = {'AWAITING_PROCESSING': 'Pending',
                #     'PAID': 'Paid',
                #     'SHIPPED': 'Shipped',
                #     'CANCELLED': 'Cancelled',
                #     'DELIVERED': 'Delivered',
                #     'RETURNED': 'Returned',
                #     'REFUNDED': 'Refunded',
                #     'COMPLETE': 'Ready for pickup'}
                #
                #     for s_key, s_value in s.items():
                #         if s_value.upper().find("")
                if not status_id:
                    status_id = UnicodingOpencartStatus.create(
                        {
                            'name': object['name'],
                            "opencartid": object['order_status_id'],
                            "unicoding_marketplace_id": opencart_id.id
                        }
                    )
            opencart_id.message_post(body=_('Added statuses: %s' % str(len(statues))), subject=_('OpenCart sync status'))



    def action_getorders(self):
        super().action_getorders()

        for opencart_id in self:
            if opencart_id.type != "opencart":
                return False
            #opencart_id = self.get_integration_details()
            #print('-------------------------------------------------------')



            Partner = self.env['res.partner'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            SaleOrder = self.env['sale.order'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            SaleOrderLine = self.env['sale.order.line'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            СrmLead = self.env['crm.lead'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ResCountryState = self.env['res.country.state'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ResCountry = self.env['res.country'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ResCurrency = self.env['res.currency'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            CrmTeam = self.env['crm.team'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductTemplate = self.env['product.template'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductProduct = self.env['product.product'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductAttribute = self.env['product.attribute'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductAttributeValue = self.env['product.attribute.value'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductTemplateAttributeValue = self.env['product.template.attribute.value'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductTemplateAttributeLine = self.env['product.template.attribute.line'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductCategory = self.env['product.category'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductPricelist = self.env['product.pricelist'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            ProductPricelistItem = self.env['product.pricelist.item'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            AccountTax = self.env['account.tax'].with_context(allowed_company_ids=[opencart_id.company_id.id])
            UnicodingOpencartStatus = self.env['unicoding.opencart.status'].with_context(allowed_company_ids=[opencart_id.company_id.id])




            # check for order status assign
            status_none = UnicodingOpencartStatus.search([('status', '=', False), ('unicoding_marketplace_id.id', '=', opencart_id.id)])
            status_check = UnicodingOpencartStatus.search([('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)
            if not status_check:
                opencart_id.message_post(body=_('First import order statuses'), subject=_('OpenCart sync status'))
                return False
            if status_none:
                opencart_id.message_post(body=_('All order statuses must be assigned'), subject=_('OpenCart sync status'))
                return False
            #check parameters
            opencart_id.opencart_get_token()

            currency_id = opencart_id.currency_id
            orders = opencart_id.opencart_get_orders()

            #return True
            orders_amount = 0
            for key, order in orders.items() if orders else []:
                #try:


                #print(order)
                saleorder_id = SaleOrder.search(
                    [('opencartid', '=', order['order_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)



                if saleorder_id:
                    continue

                orders_amount += 1

                opencart_id.last_item_date = order['date_added']


                # create partner if not exists

                if order["customer_id"]:
                    partner_id = Partner.search(
                        [('opencartid', '=', order['customer_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)
                else:
                    if not partner_id and order['telephone']:
                        partner_id = Partner.search(
                            [('mobile', '=', order['telephone']), ('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)
                    if not partner_id and order['firstname'] != 'Заказ' and (order['firstname'] or order['lastname']):
                        partner_id = Partner.search([('name', 'ilike', order['firstname'] + ' ' + order['lastname']),
                                                     ('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)

                # create partner

                partner_country_id = ResCountry.search([('code', '=', order['shipping_iso_code_2'])])

                if not partner_id:
                    partner_id = Partner.create({
                        'name': order['firstname'] + ' ' + order['lastname'],
                        "company_type": 'person',
                        "opencartid": order['customer_id'] if order['customer_id'] else '',
                        'unicoding_marketplace_id': opencart_id.id,
                        "mobile": order['telephone'],
                        "email": order['email'],
                        'create_date': order['date_added'],
                        'child_ids': [[0, False, {
                            'type': 'delivery',
                            'name': order['shipping_firstname'] + ' ' + order['shipping_lastname'],
                            'street': order['shipping_address_1'],
                            'street2': order['shipping_address_2'],
                            'city': order['shipping_city'],
                            'state_id': ResCountryState.search([('code', '=', order['shipping_zone_code']),
                                                                ('country_id', '=', partner_country_id.id)]).id,
                            'zip': order['shipping_postcode'],
                            'country_id': partner_country_id.id,
                            "email": order['email'],
                            "mobile": order['telephone'],
                            'create_date': order['date_added'],
                        }]]
                    })

                from_currency_id = ResCurrency.with_context(active_test=False).search([('name', '=', order['currency_code'])])
                if not from_currency_id.active:
                    from_currency_id.active = True



                #products add

                productpricelist_id = ProductPricelist.search(
                    [('name', '=', from_currency_id.name), ('currency_id', '=', from_currency_id.id)], limit=1)
                if not productpricelist_id:
                    productpricelist_id = ProductPricelist.create({
                        'name': from_currency_id.name,
                        'currency_id': from_currency_id.id,
                        'company_id': opencart_id.company_id.id,
                    })

                if not saleorder_id:
                    status_id = UnicodingOpencartStatus.search([("opencartid", "=", order['order_status_id'])], limit=1)
                    saleorder_id = SaleOrder.create({
                        'partner_id': partner_id.id,
                        'date_order': order['date_added'],
                        "opencartid": order['order_id'],
                        "unicoding_marketplace_id": opencart_id.id,
                        'team_id': CrmTeam.search([('name', '=', order['payment_country'])]).id,
                        'pricelist_id': productpricelist_id.id,
                        'create_date': order['date_added'],
                        'user_id': self.env.ref('unicoding_integrations_opencart3.unicoding_marketplace_user_opencart_user').id,
                        'unicoding_opencart_status_id': status_id.id if status_id else None,
                        'company_id': opencart_id.company_id.id,
                    })

                    opencart_id.opencart_notification(
                        _("Excellent! New order just created Opencart ID <b>%s</b>, Order name <b>%s</b>, Total <b>%s</b><b>%s</b>") % (
                        order['order_id'], saleorder_id.name, order['total'], opencart_id.currency_id.symbol))

                subtotal = 0
                tax_ids = []
                tax_ids_coupons = []

                for pkey, product in order['products'].items() if 'products' in order.keys() and isinstance(order['products'], dict) else {}:

                    manufacturer_id = Partner.search(
                        [('opencartid', '=', product['manufacturer']), ('is_company', '=', True)], limit=1)

                    if not manufacturer_id and product['manufacturer']:
                        manufacturer_id = Partner.create({
                            'name': product['manufacturer'],
                            "company_type": 'company',
                            "is_company": True,
                            "opencartid": product['manufacturer'],
                            'property_purchase_currency_id': from_currency_id.id,
                            'company_id': opencart_id.company_id.id,
                        })

                    product_tmpl_id = False
                    if product['ean']:
                        product_tmpl_id = ProductTemplate.search(
                            [('barcode', '=', product['ean'])])

                    if not product_tmpl_id:
                        product_tmpl_id = ProductTemplate.search(
                            [('opencartid', '=', product['product_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)]
                        )



                    if not product_tmpl_id:
                        product_tmpl_id = ProductTemplate.create({
                            'name': html.unescape(product['name']),
                            'default_code': product['model'],
                            'opencartid': product['product_id'],
                            'unicoding_marketplace_id': opencart_id.id,
                            'type': 'product',
                            # 'categ_id': category_id.id,
                            'seller_ids':[(0, False, {'name': manufacturer_id.id, 'delay': 1, 'min_qty': 1, 'price': 0,
                                                       'currency_id': from_currency_id.id})] if manufacturer_id else [],
                            # 'attribute_line_ids': attribute_line_ids
                            'barcode': product['ean'],
                            'description': html.unescape(product['description']),
                            # 'attribute_line_ids': attribute_line_ids
                            'opencart_url': "%s/index.php?route=product/product&product_id=%s" % (opencart_id.url, product['product_id']),
                            "invoice_policy": "order",
                            'company_id': opencart_id.company_id.id,
                            'currency_id': from_currency_id.id

                        })
                    if product['image'] and opencart_id.sync_product_images:
                        try:
                            image = base64.b64encode(requests.get("%s/image/%s" % (opencart_id.url, product['image'])).content)
                            product_tmpl_id.image_1920 = image
                        except Exception:
                            pass





                    category_id = ProductCategory.search([('opencartid', '=', product['category_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)])
                    #
                    # if not category_id:
                    #     continue

                    #if not category_id:
                    #    category_id = ProductCategory.search([('name', '=', product['category'])])
                    if not category_id and product['category']:
                        category_id = ProductCategory.create({
                            'name': product['category'],
                            'parent_id': self.env.ref('product.product_category_1').id,
                            'property_cost_method': 'average',
                            'property_valuation': 'real_time',
                            'opencartid': product['category_id'],
                            'unicoding_marketplace_id': opencart_id.id,
                        })


                        product_tmpl_id.categ_id = category_id.id

                    attribute_ids = []
                    value_ids = []

                    # choice next product
                    #if not product['options']:
                    #    continue


                    for option in product['options']:

                        attribute_id = ProductAttribute.search([('name', '=', option['name'])])
                        if not attribute_id:
                            attribute_id = ProductAttribute.create({
                                'name': option['name']
                            })

                        value_id = ProductAttributeValue.search(
                            [('attribute_id', '=', attribute_id.id), ('name', '=', option['value'])], limit=1)
                        if not value_id:
                            value_id = ProductAttributeValue.create(
                                {'name': option['value'], 'attribute_id': attribute_id.id})

                        ptal_id = ProductTemplateAttributeLine.search([('product_tmpl_id', '=', product_tmpl_id.id), ('attribute_id', '=', attribute_id.id)], limit=1)
                        if not ptal_id:
                            ptal_id = ProductTemplateAttributeLine.create({
                                'product_tmpl_id': product_tmpl_id.id,
                                'attribute_id': attribute_id.id,
                                'value_ids': [(6, 0, [value_id.id])]
                            })
                        else:
                            ptal_id.write({'value_ids': [(4, value_id.id)]})




                        value_ids.append(value_id.id)
                        attribute_ids.append(attribute_id.id)


                    # combination = ProductTemplateAttributeValue.search( [('attribute_id', 'in', attribute_ids), ('product_tmpl_id', '=',  product_tmpl_id.id), ('product_attribute_value_id', 'in', value_ids)], limit=1)
                    #
                    # #product_id = product_tmpl_id._get_variant_for_combination(combination)
                    # product_id = ProductProduct.search([('product_tmpl_id', '=', product_tmpl_id.id), ('product_template_attribute_value_ids', '=', [combination.id])],
                    #                                             limit=1)
                    product_id = product_tmpl_id.product_variant_id
                    if not product_id:
                        product_id = ProductProduct.search([('product_tmpl_id', '=', product_tmpl_id.id)], limit=1)

                    product_id.write({
                        "invoice_policy": "order",
                        'currency_id': from_currency_id.id
                    })

                    tax_ids = []
                    if "rates" in product.keys():
                        for prate, rate in product["rates"].items() if product["rates"] else []:

                            tax_name = rate['name']
                            tax_id = AccountTax.search(
                                [('name', '=', tax_name), ("price_include", '=', True if order['config_tax']=='1' else False)])
                            if not tax_id and tax_name:
                                tax_id = AccountTax.create({
                                    'name': tax_name,
                                    'amount': rate['rate'],
                                    'price_include': True if order['config_tax']=='1' else False,
                                    'amount_type': "fixed" if rate['type'] == "F" else "percent",
                                    'active': True,
                                    'company_id': opencart_id.company_id.id,
                                })

                            tax_ids.append(tax_id.id)


                    #product_id.write({'default_code': product['model']})


                    if product['price']:
                        price_unit = from_currency_id._convert(float(product['price']) * float(order['currency_value']),
                                                           from_currency_id, self.env.company, order['date_added'])
                    else:
                        price_unit = 0

                    if product_id:
                        SaleOrderLine.create({
                            'order_id': saleorder_id.id,
                            'name': product_id.name,
                            'product_id': product_id.id,
                            'product_uom': product_id.uom_id.id,
                            'product_uom_qty': product['quantity'],
                            'price_unit': price_unit,
                            'tax_id':  [(6, 0, tax_ids)],
                        })



                    subtotal += float(product['total'])

                    ProductPricelistItem.create(
                        {'name': product_tmpl_id.name, 'date_start': order['date_added'], 'applied_on': '1_product',
                         'product_tmpl_id': product_tmpl_id.id, 'fixed_price': price_unit,
                         'product_id': product_id.id,
                         'currency_id': from_currency_id.id,
                         'pricelist_id': productpricelist_id.id})


                if "totals" in order:
                    for total in order["totals"]:

                        tax_ids_coupons = []
                        total_tax_ids = []
                        if "rates" in total.keys():
                            for prate, rate in total["rates"].items() if total["rates"] else []:
                                tax_name = rate['name']
                                tax_id = AccountTax.search(
                                    [('name', '=', tax_name),
                                     ("price_include", '=', True if order['config_tax'] == '1' else False)])
                                if not tax_id and tax_name:
                                    tax_id = AccountTax.create({
                                        'name': tax_name,
                                        'amount': rate['rate'],
                                        'price_include': True if order['config_tax'] == '1' else False,
                                        'amount_type': "fixed" if rate['type'] == "F" else "percent",
                                        'active': True,
                                        'company_id': opencart_id.company_id.id,
                                    })

                                total_tax_ids.append(tax_id.id)
                                if rate['type'] == "P":
                                    tax_ids_coupons.append(tax_id.id)

                        if total['code'] == 'coupon':
                            coupon_id = opencart_id.add_coupon(total['title'])
                            SaleOrderLine.create({
                                'order_id': saleorder_id.id,
                                'name': coupon_id.name,
                                'product_id': coupon_id.id,
                                'product_uom': coupon_id.uom_id.id,
                                'product_uom_qty': 1,
                                'price_unit': total['value'],
                                'tax_id': [(6, 0, tax_ids_coupons)],
                            })

                        if total['code'] == 'voucher':
                            coupon_id = opencart_id.add_coupon(total['title'])
                            SaleOrderLine.create({
                                'order_id': saleorder_id.id,
                                'name': coupon_id.name,
                                'product_id': coupon_id.id,
                                'product_uom': coupon_id.uom_id.id,
                                'product_uom_qty': 1,
                                'price_unit': total['value'],
                                'tax_id': [],
                            })

                        if total['code'] == 'shipping':
                            #print(total)
                            delivery_carrier_id = self.env['delivery.carrier'].search(
                                [('name', '=', total['title']), ('delivery_type', '=', 'fixed')])

                            if not delivery_carrier_id:
                                delivery_template_id = ProductTemplate.create({
                                    'name': total['title'],
                                    'type': 'service',
                                    'categ_id': opencart_id.delivery_categ_id.id,
                                    'taxes_id': [(6, 0, total_tax_ids)],
                                    "invoice_policy": "order"
                                    # 'attribute_line_ids': attribute_line_ids
                                })
                                delivery_product_id = ProductProduct.search([('product_tmpl_id', '=', delivery_template_id.id)], limit=1)

                                #delivery_template_id._create_variant_ids()
                                delivery_carrier_id = self.env['delivery.carrier'].create({
                                    'name': total['title'],
                                    'delivery_type': 'fixed',
                                    'product_id': delivery_product_id.id,
                                })

                            # if found carreir
                            if delivery_carrier_id:
                                #print(delivery_carrier_id)
                                delivery_carrier_id.product_id.write({
                                    'taxes_id': [(6, 0, total_tax_ids)]
                                })

                                saleorder_id.set_delivery_line(delivery_carrier_id, from_currency_id._convert(
                                    (float(total['value'])) * float(order['currency_value']), from_currency_id,
                                    self.env.company, order['date_added']))
                                saleorder_id.write({
                                    'recompute_delivery_price': False,
                                    'delivery_message': total['title'],
                                })

                        if total['code'] not in ['shipping', 'voucher', 'coupon', 'sub_total', 'total', 'tax']:

                            another_template_id = ProductTemplate.search([('name', '=', total['title'])], limit=1)
                            if not another_template_id:
                                another_template_id = ProductTemplate.create({
                                    'name': total['title'],
                                    'type': 'service',
                                    'categ_id': opencart_id.delivery_categ_id.id,
                                    'taxes_id': [(6, 0, total_tax_ids)],
                                    "invoice_policy": "order"
                                    # 'attribute_line_ids': attribute_line_ids
                                })

                            another_product_id = ProductProduct.search([('product_tmpl_id', '=', another_template_id.id)], limit=1)

                            SaleOrderLine.create({
                                'order_id': saleorder_id.id,
                                'name': another_product_id.name,
                                'product_id': another_product_id.id,
                                'product_uom': another_product_id.uom_id.id,
                                'product_uom_qty': 1,
                                'price_unit': total['value'],
                                'taxes_id': [(6, 0, total_tax_ids)],
                            })




                # CRM add

                lead_id = СrmLead.search(
                    [('opencartid', '=', order['order_id']), ('unicoding_marketplace_id.id', '=', opencart_id.id)], limit=1)

                if not lead_id:
                    lead_id = СrmLead.create({
                        'name': _('Order') + ' ' + order['order_id'],
                        'expected_revenue': from_currency_id._convert(float(order['total']) * float(order['currency_value']),
                                                                     currency_id, self.env.company, order['date_added']),
                        'email_from': order['email'],
                        'phone': order['telephone'],
                        'partner_id': partner_id.id,
                        'team_id': CrmTeam.search([('name', '=', order['payment_country'])]).id,
                        'description': order['comment'],
                        "opencartid": order['order_id'],
                        "unicoding_marketplace_id": opencart_id.id,
                        'order_ids': [(4, saleorder_id.id)],
                        'create_date': order['date_added'],
                        'user_id': self.env.ref('unicoding_integrations_opencart3.unicoding_marketplace_user_opencart_user').id,
                    })

                    saleorder_id.write({
                        'opportunity_id': lead_id.id,
                        'team_id': opencart_id.team_id.id,
                    })

                    if status_id.status in ["COMPLETE"]:
                        lead_id.with_context(no_send_status_update=True).action_set_won()

                #### confirm sale
                if status_id.status in ['PAID', 'REFUNDED', 'PARTIALLY_REFUNDED', 'SHIPPED', 'DELIVERED', 'COMPLETE', 'PROCESSING']:
                    saleorder_id.with_context(no_send_status_update=True).action_confirm()
                    if status_id.status in ['PAID', 'DELIVERED', 'COMPLETE']:
                        for invoice in saleorder_id.invoice_ids:
                            invoice.with_context(no_send_status_update=True).make_payment()
                if status_id.status in ['CANCELLED']:
                    saleorder_id.with_context(no_send_status_update=True).action_cancel()
                #except Exception as e:
                #    opencart_id.message_post(body=_('Failed to add order %s' % str(e)), subject=_('Opencart order import failed'))

            opencart_id.message_post(body=_('Added orders: %s' % str(orders_amount)), subject=_('OpenCart sync status'))

