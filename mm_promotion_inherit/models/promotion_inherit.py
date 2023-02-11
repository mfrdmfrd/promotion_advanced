# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import ast
from odoo.tools.misc import formatLang
from odoo.tools.safe_eval import safe_eval


class CouponProgramInherit(models.Model):
    _inherit = 'coupon.program'
    _description = "Coupon Reward"

    # reward_type = fields.Selection(selection_add=[('category', 'Free Item From Category')])

    # reward_type = fields.Selection([
    #     ('discount', 'Discount'),
    #     ('product', 'Free Product'),
    #     ('category', 'Free Item From Category'),
    #     ], string='Reward Type', default='discount',
    #     help="Discount - Reward will be provided as discount.\n" +
    #     "Free Product - Free product will be provide as reward \n" +
    #     "Free Shipping - Free shipping will be provided as reward (Need delivery module)")
    rule_maximum_amount = fields.Monetary(string='Purchase Maximum Of', default=0)

    category_id = fields.Many2one('pos.category', 'Product Category')
    category_qty = fields.Integer(string="Min Quantity", default=0, help="Minimum Category quantity")
    max_category_qty = fields.Integer(string="Max Quantity", default=0, help="Maximum Category quantity")

    category_id2 = fields.Many2one('pos.category', 'Product Category')
    category_qty2 = fields.Integer(string="Quantity", default=0, help="Minimum Category quantity")
    max_category_qty2 = fields.Integer(string="Max Quantity", default=0, help="Maximum Category quantity")

    category_id3 = fields.Many2one('pos.category', 'Product Category')
    category_qty3 = fields.Integer(string="Quantity", default=0, help="Minimum Category quantity")
    max_category_qty3 = fields.Integer(string="Max Quantity", default=0, help="Maximum Category quantity")

    product_categ_id = fields.Many2one('pos.category', 'Product Category')
    product_category_id = fields.Many2one('product.product', string="Free Product", help="Reward Product")
    category_quantity = fields.Integer(string="Quantity", default=1, help="Category quantity")
    promotion_type = fields.Selection([
        ('by_domain', 'By Domain'),
        ('by_category', 'By Category'),
    ], string='Reward Type', default='by_domain',)

    discount_apply_on = fields.Selection([
        ('on_order', 'On Order'),
        ('on_order_line', 'On Order as Discount'),
        ('cheapest_product', 'On Cheapest Product'),
        ('specific_products', 'On Specific Products')], default="on_order",
        help="On Order - Discount on whole order\n" +
             "Cheapest product - Discount on cheapest product of the order\n" +
             "Specific products - Discount on selected specific products")

    discount_on = fields.Selection([
        ('discount_1', 'Discount #1'),
        ('discount_2', 'Discount #2'),
        ('discount_3', 'Discount #3'),
    ], string='Discount On', default='discount_1')

    line_applicability = fields.Selection([
        ('on_all', 'On all products'),
        ('on_filter', 'On filtered products')], string="Line Applicability", default='on_all')

    @api.onchange('product_categ_id')
    def domain_product_categ_id(self):
        return {'domain': {'product_category_id': [('pos_categ_id', '=', self.product_categ_id.id)]}}

class CouponRewardInherit(models.Model):
    _inherit = 'coupon.reward'
    _description = "Coupon Reward"

    reward_type = fields.Selection(selection_add=[('category', 'Free Item From Category')])
    # reward_type = fields.Selection(selection_add=[('discount2', 'Discount 2')])

    def name_get(self):
        result = []
        reward_names = super(CouponRewardInherit, self).name_get()
        free_from_category_reward_ids = self.filtered(lambda reward: reward.reward_type == 'category').ids
        # self.product_categ_id.name

        for res in reward_names:
            result.append(
                (res[0], res[0] in free_from_category_reward_ids and _("Free Product from Category") or res[1]))
        return result


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    promotion_wizard = fields.Boolean(string="Promotion", default=False)

    def clear_discounts(self):
        for record in self:
            for line in record.order_line:
                line.write({
                    'discount': 0,
                    'discount2': 0,
                    'discount3': 0,
                })

    def action_confirm(self):
        # res = super(SaleOrderInherit, self).action_confirm()
        for record in self:
            if not record.promotion_wizard:
                record.ensure_one()
                order = record
                programs = order._get_applicable_no_code_promo_program()
                programs = programs._keep_only_most_interesting_auto_applied_global_discount_program()
                if programs:
                    program_str = ''
                    for program in programs:
                        program_str += program.name + '\n'
                    success_form = record.env.ref('mm_promotion_inherit.promotion_wizard_view', False)
                    return {
                        'name': _('Apply Promotions'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'promotion.wizard',
                        'views': [(success_form.id, 'form')],
                        'view_id': success_form.id,
                        'target': 'new',
                        'context': {
                            'default_sale_id': record.id,
                            'default_promotion_text': program_str,
                        }
                    }
        return super(SaleOrderInherit, self).action_confirm()

    def _create_new_no_code_promo_reward_lines(self):
        '''Apply new programs that are applicable'''
        self.ensure_one()
        order = self
        programs = order._get_applicable_no_code_promo_program()
        programs = programs._keep_only_most_interesting_auto_applied_global_discount_program()
        promo_discount1 = []
        promo_discount2 = []
        promo_discount3 = []
        for program in programs:
            # VFE REF in master _get_applicable_no_code_programs already filters programs
            # why do we need to reapply this bunch of checks in _check_promo_code ????
            # We should only apply a little part of the checks in _check_promo_code...
            error_status = program._check_promo_code(order, False)
            if not error_status.get('error'):
                if program.promo_applicability == 'on_next_order':
                    order.state != 'cancel' and order._create_reward_coupon(program)
                elif program.discount_line_product_id.id not in self.order_line.mapped('product_id').ids:
                    if program.promotion_type == 'by_domain':
                        products = self.env['product.product'].search(safe_eval(program.rule_products_domain))
                    elif program.promotion_type == 'by_category':
                        categs = program.category_id + program.category_id2 + program.category_id3
                        products = self.env['product.product'].search([('pos_categ_id', 'in', categs.ids)])
                    if program.discount_on == 'discount_1':
                        promo_discount1.append(program.discount_percentage)
                    elif program.discount_on == 'discount_2':
                        promo_discount2.append(program.discount_percentage)
                    else:
                        promo_discount3.append(program.discount_percentage)
                    if program.reward_type == 'discount' and program.discount_apply_on == 'on_order_line':
                        if program.line_applicability == 'on_filter':
                            lines = self.order_line.filtered(lambda l: l.product_id in products)
                        else:
                            lines = self.order_line
                        for line in lines:
                            if program.discount_type == 'percentage':
                                line.write({
                                    'discount': sum(promo_discount1),
                                    'discount2': sum(promo_discount2),
                                    'discount3': sum(promo_discount3),
                                })
                                # else:
                                #     line.write({
                                #         'discount': 0,
                                #         'price_subtotal': line.price_subtotal - program.discount_fixed_amount
                                #     })
                    elif program.reward_type == 'product':
                        if program.line_applicability == 'on_filter':
                            lines = self.order_line.filtered(lambda l: l.product_id in products)
                        else:
                            lines = self.order_line
                        if lines:
                            free_lines = self.order_line.filtered(lambda l: l.product_id == program.reward_product_id)
                            for line in free_lines:
                                if program.discount_on == 'discount_1':
                                    field = 'discount'
                                elif program.discount_on == 'discount_2':
                                    field = 'discount2'
                                else:
                                    field = 'discount3'
                                line.write({
                                    field: 100/line.product_uom_qty * program.reward_product_quantity
                                })
                    elif program.reward_type == 'category':
                        if program.line_applicability == 'on_filter':
                            lines = self.order_line.filtered(lambda l: l.product_id in products)
                        else:
                            lines = self.order_line
                        if lines:
                            free_lines = self.order_line.filtered(lambda l: l.product_id.pos_categ_id in program.product_categ_id)
                            for line in free_lines:
                                if program.discount_on == 'discount_1':
                                    field = 'discount'
                                elif program.discount_on == 'discount_2':
                                    field = 'discount2'
                                else:
                                    field = 'discount3'
                                line.write({
                                    field: 100 / line.product_uom_qty * program.category_quantity
                                })
                    else:
                        self.write({'order_line': [(0, False, value) for value in self._get_reward_line_values(program)]})
                order.no_code_promo_program_ids |= program

    def recompute_coupon_lines_wiz(self):
        view = self.env.ref('mm_promotion_inherit.get_data_wizard_from_view')
        return {
            'name': _('Promotion Wizard'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'get.data.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
        }

    def _get_reward_line_values(self, program):
        self.ensure_one()
        self = self.with_context(lang=self.partner_id.lang)
        program = program.with_context(lang=self.partner_id.lang)
        if program.reward_type == 'discount':
            return self._get_reward_values_discount(program)
        elif program.reward_type == 'discount2':
            return self._get_reward_values_discount2(program)
        # done
        elif program.reward_type == 'product':
            if program.promotion_type == 'by_category':
                # done
                return [self._get_reward_values_product_category(program)]
            else:
                # done
                return [self._get_reward_values_product(program)]

        elif program.reward_type == 'category':
            if program.promotion_type == 'by_category':
                return [self._get_reward_values_category(program)]
            else:
                return [self._get_reward_values_category_domain2(program)]

    def _get_reward_values_discount2(self, program):
        if program.discount_type == 'fixed_amount':
            return self._get_reward_values_fixed_amount2(program)
        else:
            return self._get_reward_values_percentage_amount2(program)
    def _get_base_order_lines2(self, program):
        """ Returns the sale order lines not linked to the given program.
        """
        return self.order_line.filtered(lambda x: not x._is_not_sellable_line() or x.is_reward_line)

    # def _get_reward_values_percentage_amount2(self, program):
    #     # Invalidate multiline fixed_price discount line as they should apply after % discount
    #     fixed_price_products = self._get_applied_programs().filtered(
    #         lambda p: p.discount_type == 'fixed_amount').mapped('discount_line_product_id')
    #     self.order_line.filtered(lambda l: l.product_id in fixed_price_products).write({'price_unit': 0})
    #
    #     reward_dict = {}
    #     lines = self._get_paid_order_lines()
    #     amount_total = sum([any(line.tax_id.mapped('price_include')) and line.price_total or line.price_subtotal
    #                         for line in self._get_base_order_lines2(program)])
    #     if program.discount_apply_on == 'cheapest_product':
    #         line = self._get_cheapest_line()
    #         if line:
    #             discount_line_amount = min(line.price_reduce * (program.discount_percentage / 100), amount_total)
    #             if discount_line_amount:
    #                 taxes = self.fiscal_position_id.map_tax(line.tax_id)
    #
    #                 reward_dict[line.tax_id] = {
    #                     'name': _("Discount: %s", program.name),
    #                     'product_id': program.discount_line_product_id.id,
    #                     'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
    #                     'product_uom_qty': 1.0,
    #                     'product_uom': program.discount_line_product_id.uom_id.id,
    #                     'is_reward_line': True,
    #                     'tax_id': [(4, tax.id, False) for tax in taxes],
    #                 }
    #     elif program.discount_apply_on in ['specific_products', 'on_order']:
    #         if program.discount_apply_on == 'specific_products':
    #             # We should not exclude reward line that offer this product since we need to offer only the discount on the real paid product (regular product - free product)
    #             free_product_lines = self.env['coupon.program'].search([('reward_type', '=', 'product'), ('reward_product_id', 'in', program.discount_specific_product_ids.ids)]).mapped('discount_line_product_id')
    #             lines = lines.filtered(lambda x: x.product_id in (program.discount_specific_product_ids | free_product_lines))
    #
    #         # when processing lines we should not discount more than the order remaining total
    #         currently_discounted_amount = 0
    #         for line in lines:
    #             discount_line_amount = min(self._get_reward_values_discount_percentage_per_line(program, line), amount_total - currently_discounted_amount)
    #
    #             if discount_line_amount:
    #
    #                 if line.tax_id in reward_dict:
    #                     reward_dict[line.tax_id]['price_unit'] -= discount_line_amount
    #                 else:
    #                     taxes = self.fiscal_position_id.map_tax(line.tax_id)
    #
    #                     reward_dict[line.tax_id] = {
    #                         'name': _(
    #                             "Discount 2: %(program)s - On Order",
    #                             program=program.name,
    #                             taxes=", ".join(taxes.mapped('name')),
    #                         ),
    #                         'product_id': program.discount_line_product_id.id,
    #                         'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
    #                         'product_uom_qty': 1.0,
    #                         'product_uom': program.discount_line_product_id.uom_id.id,
    #                         'is_reward_line': True,
    #                         'tax_id': [(4, tax.id, False) for tax in taxes],
    #                     }
    #                     currently_discounted_amount += discount_line_amount
    #
    #     # If there is a max amount for discount, we might have to limit some discount lines or completely remove some lines
    #     max_amount = program._compute_program_amount('discount_max_amount', self.currency_id)
    #     if max_amount > 0:
    #         amount_already_given = 0
    #         for val in list(reward_dict):
    #             amount_to_discount = amount_already_given + reward_dict[val]["price_unit"]
    #             if abs(amount_to_discount) > max_amount:
    #                 reward_dict[val]["price_unit"] = - (max_amount - abs(amount_already_given))
    #                 add_name = formatLang(self.env, max_amount, currency_obj=self.currency_id)
    #                 reward_dict[val]["name"] += "( " + _("limited to ") + add_name + ")"
    #             amount_already_given += reward_dict[val]["price_unit"]
    #             if reward_dict[val]["price_unit"] == 0:
    #                 del reward_dict[val]
    #     return reward_dict.values()
    #
    # def _get_reward_values_percentage_amount2(self, program):
    #     # Invalidate multiline fixed_price discount line as they should apply after % discount
    #     fixed_price_products = self._get_applied_programs().filtered(
    #         lambda p: p.discount_type == 'fixed_amount').mapped('discount_line_product_id')
    #     self.order_line.filtered(lambda l: l.product_id in fixed_price_products).write({'price_unit': 0})
    #
    #     reward_dict = {}
    #     lines = self._get_paid_order_lines()
    #     amount_total = sum([any(line.tax_id.mapped('price_include')) and line.price_total or line.price_subtotal
    #                         for line in self._get_base_order_lines(program)])
    #     if program.discount_apply_on == 'cheapest_product':
    #         line = self._get_cheapest_line()
    #         if line:
    #             discount_line_amount = min(line.price_reduce * (program.discount_percentage / 100), amount_total)
    #             if discount_line_amount:
    #                 taxes = self.fiscal_position_id.map_tax(line.tax_id)
    #
    #                 reward_dict[line.tax_id] = {
    #                     'name': _("Discount: %s", program.name),
    #                     'product_id': program.discount_line_product_id.id,
    #                     'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
    #                     'product_uom_qty': 1.0,
    #                     'product_uom': program.discount_line_product_id.uom_id.id,
    #                     'is_reward_line': True,
    #                     'tax_id': [(4, tax.id, False) for tax in taxes],
    #                 }
    #     elif program.discount_apply_on in ['specific_products', 'on_order']:
    #         if program.discount_apply_on == 'specific_products':
    #             # We should not exclude reward line that offer this product since we need to offer only the discount on the real paid product (regular product - free product)
    #             free_product_lines = self.env['coupon.program'].search([('reward_type', '=', 'product'), ('reward_product_id', 'in', program.discount_specific_product_ids.ids)]).mapped('discount_line_product_id')
    #             lines = lines.filtered(lambda x: x.product_id in (program.discount_specific_product_ids | free_product_lines))
    #
    #         # when processing lines we should not discount more than the order remaining total
    #         currently_discounted_amount = 0
    #         for line in lines:
    #             discount_line_amount = min(self._get_reward_values_discount_percentage_per_line(program, line), amount_total - currently_discounted_amount)
    #
    #             if discount_line_amount:
    #
    #                 if line.tax_id in reward_dict:
    #                     reward_dict[line.tax_id]['price_unit'] -= discount_line_amount
    #                 else:
    #                     taxes = self.fiscal_position_id.map_tax(line.tax_id)
    #
    #                     reward_dict[line.tax_id] = {
    #                         'name': _(
    #                             "Discount: %(program)s - On product with following taxes: %(taxes)s",
    #                             program=program.name,
    #                             taxes=", ".join(taxes.mapped('name')),
    #                         ),
    #                         'product_id': program.discount_line_product_id.id,
    #                         'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
    #                         'product_uom_qty': 1.0,
    #                         'product_uom': program.discount_line_product_id.uom_id.id,
    #                         'is_reward_line': True,
    #                         'tax_id': [(4, tax.id, False) for tax in taxes],
    #                     }
    #                     currently_discounted_amount += discount_line_amount
    #
    #     # If there is a max amount for discount, we might have to limit some discount lines or completely remove some lines
    #     max_amount = program._compute_program_amount('discount_max_amount', self.currency_id)
    #     if max_amount > 0:
    #         amount_already_given = 0
    #         for val in list(reward_dict):
    #             amount_to_discount = amount_already_given + reward_dict[val]["price_unit"]
    #             if abs(amount_to_discount) > max_amount:
    #                 reward_dict[val]["price_unit"] = - (max_amount - abs(amount_already_given))
    #                 add_name = formatLang(self.env, max_amount, currency_obj=self.currency_id)
    #                 reward_dict[val]["name"] += "( " + _("limited to ") + add_name + ")"
    #             amount_already_given += reward_dict[val]["price_unit"]
    #             if reward_dict[val]["price_unit"] == 0:
    #                 del reward_dict[val]
    #     return reward_dict.values()

    def _get_valid_product_domain(self, products, promo):
        if promo.promotion_type == 'by_domain':
            prom_products = self.env['product.product'].search(safe_eval(promo.rule_products_domain))
            if products in prom_products:
                return True
        else:
            categs = promo.category_id + promo.category_id2 + promo.category_id3
            prom_products = self.env['product.product'].search([('pos_categ_id', 'in', categs.ids)])
            if products in prom_products:
                return True

    def _get_line_promotions(self, line, programs):
        promotions = []
        for program in programs:
            if program._is_valid_partner(self.partner_id):
                program_amount = program._compute_program_amount('rule_minimum_amount', self.currency_id)
                if (program.rule_minimum_amount_tax_inclusion == 'tax_included' and program_amount <= (
                        self.amount_untaxed + self.amount_tax) and (program.rule_maximum_amount == 0 or program.rule_maximum_amount >= (
                        self.amount_untaxed + self.amount_tax))) or \
                        (program_amount <= self.amount_untaxed and (program.rule_maximum_amount == 0 or program.rule_maximum_amount >= self.amount_untaxed)) :
                    # if program.line_applicability == 'on_all':
                    #     if program.reward_type == 'discount':
                    #         if program.discount_apply_on == 'on_order_line':
                    #             promotions.append(program)
                    #     elif program.reward_type == 'product':
                    #         if line.product_id == program.reward_product_id:
                    #             multiple_lines = self.order_line.filtered(lambda x: x.product_id == program.reward_product_id)
                    #             if sum(multiple_lines.mapped('product_uom_qty')) >= ((program.category_qty if program.promotion_type == 'by_category' else program.rule_min_quantity) + program.reward_product_quantity):
                    #                 promotions.append(program)
                    #             else:
                    #                 if line.product_uom_qty >= program.reward_product_quantity + (program.category_qty if program.promotion_type == 'by_category' else program.rule_min_quantity):
                    #                     promotions.append(program)
                    #     elif program.reward_type == 'category':
                    #         if line.product_id.pos_categ_id == program.product_categ_id:
                    #             multiple_lines = self.order_line.filtered(
                    #                 lambda x: x.product_id.pos_categ_id == program.product_categ_id)
                    #             if sum(multiple_lines.mapped('product_uom_qty')) >= (
                    #                     (program.category_qty if program.promotion_type == 'by_category' else program.rule_min_quantity) + program.category_quantity):
                    #                 promotions.append(program)
                    #             else:
                    #                 if line.product_uom_qty >= ((program.category_qty if program.promotion_type == 'by_category' else program.rule_min_quantity) + program.category_quantity):
                    #                     promotions.append(program)
                    # else:
                    if program.promotion_type == 'by_domain':
                        if self._get_valid_product_domain(line.product_id, program):
                            if program.reward_type == 'discount':
                                if program.discount_apply_on == 'on_order_line':
                                    promotions.append(program)
                            if program.reward_type == 'product':
                                if line.product_id == program.reward_product_id:
                                    multiple_lines = self.order_line.filtered(lambda x: x.product_id == program.reward_product_id)
                                    if sum(multiple_lines.mapped('product_uom_qty')) >= (program.rule_min_quantity + program.reward_product_quantity):
                                        promotions.append(program)
                                    else:
                                        if line.product_uom_qty >= program.rule_min_quantity + program.reward_product_quantity:
                                            promotions.append(program)
                            if program.reward_type == 'category':
                                if line.product_id.pos_categ_id == program.product_categ_id:
                                    multiple_lines = self.order_line.filtered(
                                        lambda x: x.product_id.pos_categ_id == program.product_categ_id)
                                    if sum(multiple_lines.mapped('product_uom_qty')) >= (
                                            program.rule_min_quantity + program.category_quantity):
                                        promotions.append(program)
                                    else:
                                        if line.product_uom_qty >= (program.rule_min_quantity + program.category_quantity):
                                            promotions.append(program)
                    else:
                        if self._get_valid_product_domain(line.product_id, program):
                            if program.reward_type == 'discount':
                                if program.discount_apply_on == 'on_order_line':
                                    multiple_lines = self.order_line.filtered(
                                        lambda x: x.product_id.pos_categ_id in (program.category_id + program.category_id2 + program.category_id3))
                                    if program.max_category_qty:
                                        if program.category_qty <= sum(multiple_lines.mapped(
                                                'product_uom_qty')) <= program.max_category_qty:
                                            promotions.append(program)
                                    else:
                                        if sum(multiple_lines.mapped('product_uom_qty')) >= (program.category_qty):
                                            promotions.append(program)
                                    # if program.max_category_qty:
                                    #     if program.category_qty <= line.product_uom_qty <= program.max_category_qty:
                                    #         promotions.append(program)
                                    # else:
                                    #     if line.product_uom_qty >= program.category_qty:
                                    #         promotions.append(program)
                            if program.reward_type == 'product':
                                if line.product_id == program.reward_product_id:
                                    multiple_lines = self.order_line.filtered(lambda x: x.product_id == program.reward_product_id)
                                    if sum(multiple_lines.mapped('product_uom_qty')) >= (program.category_qty + program.reward_product_quantity):
                                        if program.max_category_qty:
                                            if program.category_qty <= sum(multiple_lines.mapped('product_uom_qty')) <= program.max_category_qty:
                                                promotions.append(program)
                                        else:
                                            promotions.append(program)
                                    else:
                                        if line.product_uom_qty >= (program.category_qty + program.reward_product_quantity):
                                            if program.max_category_qty:
                                                if program.category_qty <= line.product_uom_qty <= program.max_category_qty:
                                                    promotions.append(program)
                                            else:
                                                promotions.append(program)
                            if program.reward_type == 'category':
                                if line.product_id.pos_categ_id == program.product_categ_id:
                                    multiple_lines = self.order_line.filtered(
                                        lambda x: x.product_id.pos_categ_id == program.product_categ_id)
                                    if sum(multiple_lines.mapped('product_uom_qty')) >= (
                                            program.category_qty + program.category_quantity):
                                        if program.max_category_qty:
                                            if program.category_qty <= sum(multiple_lines.mapped('product_uom_qty')) <= program.max_category_qty:
                                                promotions.append(program)
                                        else:
                                            promotions.append(program)
                                    else:
                                        if line.product_uom_qty >= (program.category_qty + program.category_quantity):
                                            if program.max_category_qty:
                                                if program.category_qty <= line.product_uom_qty <= program.max_category_qty:
                                                    promotions.append(program)
                                            else:
                                                promotions.append(program)
        return promotions

    def _get_free_promo_apply_line(self, promo_lines, promo):
        # line_to_apply = promo_lines.filtered(lambda x: x.price_unit == min(promo_lines.mapped('price_unit')))
        line_to_apply = sorted(promo_lines, key=lambda x: float(x.price_unit))
        lines_reviewed = []
        # if len(set(promo_lines.mapped('price_unit'))) == 1:
        for line in line_to_apply:
            free_count = int(sum(promo_lines.mapped('product_uom_qty')) / ((promo.category_qty if promo.promotion_type == 'by_category' else promo.rule_min_quantity) + promo.category_quantity)) * (promo.category_quantity if promo.reward_type == 'category' else promo.reward_product_quantity)
            discount = ((free_count * line.price_unit) / (line.price_unit * line.product_uom_qty)) * 100
            if discount <= 100:
                lines_reviewed.append(line)

        return lines_reviewed
        # else:
        # return line_to_apply

    def _get_free_promo_apply_line2(self, promo_lines, promo):
        # line_to_apply = promo_lines.filtered(lambda x: x.price_unit == min(promo_lines.mapped('price_unit')))
        line_to_apply = sorted(promo_lines, key=lambda x: float(x.price_unit))
        lines_reviewed = []
        free_unit_price=line_to_apply[0].price_unit

        free_count = int(sum(promo_lines.mapped('product_uom_qty')) / ((promo.category_qty if promo.promotion_type == 'by_category' else promo.rule_min_quantity) + promo.category_quantity)) * (promo.category_quantity if promo.reward_type == 'category' else promo.reward_product_quantity)
        free_price=free_count*free_unit_price
        discount=free_price/sum(promo_lines.mapped('price_subtotal'))

        # if len(set(promo_lines.mapped('price_unit'))) == 1:
        for line in line_to_apply:
            discount = ((free_count * line.price_unit) / (line.price_unit * line.product_uom_qty)) * 100
            if discount <= 100:
                lines_reviewed.append(line)

        return lines_reviewed
        # else:
        # return line_to_apply

    def _get_free_line_discount(self, line, promo):
        if promo.reward_type == 'category':
            multiple_lines = self.order_line.filtered(lambda x: x.product_id.pos_categ_id == promo.product_categ_id)
            if len(multiple_lines) > 1:
                total_order_qty=sum(multiple_lines.mapped('product_uom_qty'))
                total_order_price = 0
                for l in multiple_lines:
                    total_order_price += l.price_unit*l.product_uom_qty
                if total_order_qty >= ((promo.category_qty if promo.promotion_type == 'by_category' else promo.rule_min_quantity)  + promo.category_quantity):
                    #apply_line = self._get_free_promo_apply_line(multiple_lines, promo)
                    #if apply_line and apply_line[0] == line:
                    least_price=min(multiple_lines.mapped('price_unit'))
                    free_count = int(sum(multiple_lines.mapped('product_uom_qty')) / ((promo.category_qty if promo.promotion_type == 'by_category' else promo.rule_min_quantity)  + promo.category_quantity)) * promo.category_quantity
                    discount = ((free_count * least_price) / total_order_price) * 100
                    return discount
                    #else:
                    #    return 0
            else:
                free_count = int(line.product_uom_qty / (promo.category_qty + promo.category_quantity)) * promo.category_quantity
                discount = ((free_count * line.price_unit) / (line.price_unit * line.product_uom_qty)) * 100
#                discount = ((free_count * line.price_unit) / sum(line.mapped(price_subtotal))
                return discount
        if promo.reward_type == 'product':
            multiple_lines = self.order_line.filtered(lambda x: x.product_id == promo.reward_product_id)
            if len(multiple_lines) > 1:
                if sum(multiple_lines.mapped('product_uom_qty')) >= ((promo.category_qty if promo.promotion_type == 'by_category' else promo.rule_min_quantity) + promo.reward_product_quantity):
                    apply_line = self._get_free_promo_apply_line(multiple_lines, promo)
                    if apply_line and apply_line[0] == line:
                        free_count = int(sum(multiple_lines.mapped('product_uom_qty')) / ((promo.category_qty if promo.promotion_type == 'by_category' else promo.rule_min_quantity) + promo.reward_product_quantity)) * promo.reward_product_quantity
                        discount = ((free_count * line.price_unit) / (line.price_unit * line.product_uom_qty)) * 100
                        return discount
                    else:
                        return 0
            else:
                free_count = int(line.product_uom_qty / ((promo.category_qty if promo.promotion_type == 'by_category' else promo.rule_min_quantity) + promo.reward_product_quantity)) * promo.reward_product_quantity
                discount = ((free_count * line.price_unit) / (line.price_unit * line.product_uom_qty)) * 100
                return discount

    def _update_existing_reward_lines(self):
        '''Update values for already applied rewards'''
        self.ensure_one()
        applied_promotions = self.env['coupon.program']
        applied_programs = self.env['coupon.program'].search([]).filtered(lambda p: p.promo_code_usage == 'no_code_needed' and p.promo_applicability == 'on_current_order')
        for line in self.order_line:
            line_promotions = self._get_line_promotions(line, applied_programs)
            discount_1 = 0
            discount_2 = 0
            discount_3 = 0
            for promo in line_promotions:
                applied_promotions += promo
                if promo.reward_type == 'discount':
                    if promo.discount_on == 'discount_1':
                        discount_1 = discount_1 + promo.discount_percentage
                    elif promo.discount_on == 'discount_2':
                        discount_2 = discount_2 + promo.discount_percentage
                    else:
                        discount_3 = discount_3 + promo.discount_percentage

                if promo.reward_type == 'category' or promo.reward_type == 'product':
                    value = self._get_free_line_discount(line, promo)
                    if promo.discount_on == 'discount_1':
                        discount_1 = discount_1 + value
                    elif promo.discount_on == 'discount_2':
                        discount_2 = discount_2 + value
                    else:
                        discount_3 = discount_3 + value
            line.write({
                'discount': discount_1,
                'discount2': discount_2,
                'discount3': discount_3,
            })
        if applied_promotions:
            msg = "<b>" + _("Applied Promotions.") + "</b><ul>"
            for record in set(applied_promotions):
                msg += "<li> %s: <br/>" % record.name
            self.message_post(body=msg)
        # def update_line(order, lines, values):
        #     '''Update the lines and return them if they should be deleted'''
        #     lines_to_remove = self.env['sale.order.line']
        #     # Check commit 6bb42904a03 for next if/else
        #     # Remove reward line if price or qty equal to 0
        #     if values['product_uom_qty'] and values['price_unit']:
        #         lines.write(values)
        #     else:
        #         if program.reward_type != 'free_shipping':
        #             # Can't remove the lines directly as we might be in a recordset loop
        #             lines_to_remove += lines
        #         else:
        #             values.update(price_unit=0.0)
        #             lines.write(values)
        #     return lines_to_remove
        #
        # self.ensure_one()
        # order = self
        # applied_programs = order._get_applied_programs_with_rewards_on_current_order()
        # promo_discount1 = []
        # promo_discount2 = []
        # promo_discount3 = []
        # for program in applied_programs.sorted(lambda ap: ap.reward_type == 'discount'):
        #     values = order._get_reward_line_values(program)
        #     lines = order.order_line.filtered(lambda line: line.product_id == program.discount_line_product_id)
        #     if program.reward_type == 'discount':
        #         lines_to_remove = lines
        #         lines_to_add = []
        #         lines_to_keep = []
        #         # Values is what discount lines should really be, lines is what we got in the SO at the moment
        #         # 1. If values & lines match, we should update the line (or delete it if no qty or price?)
        #         #    As removing a lines remove all the other lines linked to the same program, we need to save them
        #         #    using lines_to_keep
        #         # 2. If the value is not in the lines, we should add it
        #         # 3. if the lines contains a tax not in value, we should remove it
        #         for value in values:
        #             value_found = False
        #             for line in lines:
        #                 # Case 1.
        #                 if not len(set(line.tax_id.mapped('id')).symmetric_difference(set([v[1] for v in value['tax_id']]))):
        #                     value_found = True
        #                     # Working on Case 3.
        #                     # update_line update the line to the correct value and returns them if they should be unlinked
        #                     update_to_remove = update_line(order, line, value)
        #                     if not update_to_remove:
        #                         lines_to_keep += [(0, False, value)]
        #                         lines_to_remove -= line
        #             # Working on Case 2.
        #             if not value_found:
        #                 lines_to_add += [(0, False, value)]
        #         # Case 3.
        #         line_update = []
        #         if lines_to_remove:
        #             line_update += [(3, line_id, 0) for line_id in lines_to_remove.ids]
        #             line_update += lines_to_keep
        #         line_update += lines_to_add
        #         order.write({'order_line': line_update})
        #         # Case 3.
        #         lines_to_remove.unlink()
        #         if program.discount_on == 'discount_1':
        #             promo_discount1.append(program.discount_percentage)
        #         elif program.discount_on == 'discount_2':
        #             promo_discount2.append(program.discount_percentage)
        #         else:
        #             promo_discount3.append(program.discount_percentage)
        #         if program.discount_apply_on == 'on_order_line':
        #             if program.promotion_type == 'by_domain':
        #                 products = self.env['product.product'].search(safe_eval(program.rule_products_domain))
        #             elif program.promotion_type == 'by_category':
        #                 categs = program.category_id + program.category_id2 + program.category_id3
        #                 products = self.env['product.product'].search([('pos_categ_id', 'in', categs.ids)])
        #             if program.line_applicability == 'on_filter':
        #                 lines = self.order_line.filtered(lambda l: l.product_id in products)
        #             else:
        #                 lines = self.order_line
        #             for line in lines:
        #                 if program.discount_type == 'percentage':
        #                     line.write({
        #                         'discount': sum(promo_discount1),
        #                         'discount2': sum(promo_discount2),
        #                         'discount3': sum(promo_discount3),
        #                     })
        #     elif program.reward_type == 'discount2':
        #         lines_to_remove = lines
        #         lines_to_add = []
        #         lines_to_keep = []
        #         # Values is what discount lines should really be, lines is what we got in the SO at the moment
        #         # 1. If values & lines match, we should update the line (or delete it if no qty or price?)
        #         #    As removing a lines remove all the other lines linked to the same program, we need to save them
        #         #    using lines_to_keep
        #         # 2. If the value is not in the lines, we should add it
        #         # 3. if the lines contains a tax not in value, we should remove it
        #         for value in values:
        #             value_found = False
        #             for line in lines:
        #                 # Case 1.
        #                 if not len(set(line.tax_id.mapped('id')).symmetric_difference(
        #                         set([v[1] for v in value['tax_id']]))):
        #                     value_found = True
        #                     # Working on Case 3.
        #                     # update_line update the line to the correct value and returns them if they should be unlinked
        #                     update_to_remove = update_line(order, line, value)
        #                     if not update_to_remove:
        #                         lines_to_keep += [(0, False, value)]
        #                         lines_to_remove -= line
        #             # Working on Case 2.
        #             if not value_found:
        #                 lines_to_add += [(0, False, value)]
        #         # Case 3.
        #         line_update = []
        #         if lines_to_remove:
        #             line_update += [(3, line_id, 0) for line_id in lines_to_remove.ids]
        #             line_update += lines_to_keep
        #         line_update += lines_to_add
        #         order.write({'order_line': line_update})
        #     elif program.reward_type == 'product':
        #         if program.promotion_type == 'by_domain':
        #             products = self.env['product.product'].search(safe_eval(program.rule_products_domain))
        #         elif program.promotion_type == 'by_category':
        #             categs = program.category_id + program.category_id2 + program.category_id3
        #             products = self.env['product.product'].search([('pos_categ_id', 'in', categs.ids)])
        #         if program.line_applicability == 'on_filter':
        #             lines = self.order_line.filtered(lambda l: l.product_id in products)
        #         else:
        #             lines = self.order_line
        #         if lines:
        #             free_lines = self.order_line.filtered(
        #                 lambda l: l.product_id == program.reward_product_id)
        #             for line in free_lines:
        #                 if program.discount_on == 'discount_1':
        #                     field = 'discount'
        #                 elif program.discount_on == 'discount_2':
        #                     field = 'discount2'
        #                 else:
        #                     field = 'discount3'
        #                 line.write({
        #                     field: 100 / line.product_uom_qty * program.reward_product_quantity
        #                 })
        #     elif program.reward_type == 'category':
        #         if program.promotion_type == 'by_domain':
        #             products = self.env['product.product'].search(safe_eval(program.rule_products_domain))
        #         elif program.promotion_type == 'by_category':
        #             categs = program.category_id + program.category_id2 + program.category_id3
        #             products = self.env['product.product'].search([('pos_categ_id', 'in', categs.ids)])
        #         if program.line_applicability == 'on_filter':
        #             lines = self.order_line.filtered(lambda l: l.product_id in products)
        #         else:
        #             lines = self.order_line
        #         if lines:
        #             free_lines = self.order_line.filtered(
        #                 lambda l: l.product_id.pos_categ_id in program.product_categ_id)
        #             for line in free_lines:
        #                 if program.discount_on == 'discount_1':
        #                     field = 'discount'
        #                 elif program.discount_on == 'discount_2':
        #                     field = 'discount2'
        #                 else:
        #                     field = 'discount3'
        #                 line.write({
        #                     field: 100 / line.product_uom_qty * program.category_quantity
        #                 })
        #     else:
        #         update_line(order, lines, values[0]).unlink()
    # done
    def _get_reward_values_category_domain(self, program):
        products_domain = ast.literal_eval(program.rule_products_domain)
        price_unit = 0
        for line in self.order_line:
            reward_qty = 0
            taxes_id = None
            taxes = None
            product_id = None
            if line.product_id.pos_categ_id.id == program.product_categ_id.id:
                taxes_id = line.product_id.taxes_id
                product_id = line.product_id
                taxes = taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
                taxes = self.fiscal_position_id.map_tax(taxes)

                products = self.env['product.product'].search(products_domain)
                max_product_qty = 0
                total_qty = 0
                run = 0
                order_lines = (self.order_line - self._get_reward_lines()).filtered(
                    lambda x: program._get_valid_products(x.product_id))
                for product in products:
                    for line in self.order_line:
                        if product.id == line.product_id.id:
                            run += 1
                            price_unit = product_id.lst_price
                            max_product_qty += line.product_uom_qty
                            total_qty += line.product_uom_qty
                if run >= 1:
                    if program._get_valid_products(product_id):
                        # number of times the program should be applied
                        program_in_order = max_product_qty // (program.rule_min_quantity + program.category_quantity)
                        # multipled by the reward qty
                        reward_product_qty = program.category_quantity * program_in_order
                        # do not give more free reward than products
                        reward_product_qty = min(reward_product_qty, total_qty)
                        if program.rule_minimum_amount:
                            order_total = sum(order_lines.mapped('price_total')) - (
                                    program.category_quantity * product_id.lst_price)
                            print("order_total", order_total)
                            reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
                    else:
                        program_in_order = max_product_qty // program.rule_min_quantity
                        reward_product_qty = min(program.category_quantity * program_in_order, total_qty)

                    reward_qty = min(int(int(max_product_qty / program.rule_min_quantity) * program.category_quantity),
                                     reward_product_qty)

            return {
                'product_id': program.discount_line_product_id.id,
                'price_unit': - price_unit,
                'product_uom_qty': program.category_quantity,
                'is_reward_line': True,
                'name': _("Free Product in ") + program.product_categ_id.name,
                'product_uom': product_id.uom_id.id,
                'tax_id': [(4, tax.id, False) for tax in taxes],
            }

    def _get_reward_values_category_domain2(self, program):
        products_domain = ast.literal_eval(program.rule_products_domain)
        products = self.env['product.product'].search(products_domain)

        order_lines = (self.order_line - self._get_reward_lines()).filtered(
            lambda x: program._get_valid_products(x.product_id))

        max_product_qty = sum(order_lines.mapped('product_uom_qty')) or 1
        total_qty = sum(
            self.order_line.filtered(lambda x: x.product_id == program.product_categ_id).mapped('product_uom_qty'))
        product_categ_id = fields.Many2one(related='product_id.product_tmpl_id.categ_id', string='Product Category')


        total_product_qty = 0
        product_qty=0
        price_unit = 0
        for product in products:
            for line in self.order_line:
                if product.id == line.product_id.id:
                    product_qty += 1
                    price_unit = line.product_id.lst_price
                    total_product_qty += line.product_uom_qty
                    total_qty += line.product_uom_qty
                if product_qty >= 1:
                    if program._get_valid_products(line.product_id):
                        # number of times the program should be applied
                        program_in_order = total_product_qty // (program.rule_min_quantity + program.category_quantity)
                        # multipled by the reward qty
                        reward_product_qty = program.category_quantity * program_in_order
                        # do not give more free reward than products
                        reward_product_qty = min(reward_product_qty, total_qty)
                        if program.rule_minimum_amount:
                            order_total = sum(order_lines.mapped('price_total')) - (
                                    program.category_quantity * line.product_id.lst_price)
                            print("order_total", order_total)
                            reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
                    else:
                        program_in_order = total_product_qty // program.rule_min_quantity
                        reward_product_qty = min(program.category_quantity * program_in_order, total_qty)

                    reward_qty = min(int(int(total_product_qty / program.rule_min_quantity) * program.category_quantity),
                                     reward_product_qty)

            return {
                'product_id': program.discount_line_product_id.id,
                'price_unit': - price_unit,
                'product_uom_qty': program.category_quantity,
                'is_reward_line': True,
                'name': _("Free Product in ") + program.product_categ_id.name,
                'product_uom': line.product_id.uom_id.id,
                'tax_id': [(4, tax.id, False) for tax in line.taxes],
            }


    # done
    def _get_reward_values_category(self, program):
        domain = ast.literal_eval(program.rule_products_domain)
        price_unit = 0

        reward_qty = 0
        reward_qty2 = 0
        reward_qty3 = 0
        total_reward_qty = 0
        for line in self.order_line:
            taxes_id = None
            taxes = None
            product_id = None
            if line.product_id.pos_categ_id.id == program.product_categ_id.id:
                taxes_id = line.product_id.taxes_id
                product_id = line.product_id

                taxes = taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
                taxes = self.fiscal_position_id.map_tax(taxes)

                if program.category_id:
                    products = self.env['product.product'].search([('pos_categ_id', '=', program.category_id.id)])
                    max_product_qty = 0
                    total_qty = 0
                    run = 0
                    order_lines = (self.order_line - self._get_reward_lines()).filtered(
                        lambda x: program._get_valid_products(x.product_id))
                    for product in products:
                        for line in self.order_line:
                            if product.id == line.product_id.id:
                                run += 1
                                price_unit = product_id.lst_price
                                max_product_qty += line.product_uom_qty
                                total_qty += line.product_uom_qty
                    if run >= 1:
                        if program._get_valid_products(product_id):
                            # number of times the program should be applied
                            program_in_order = max_product_qty // (program.category_qty + program.category_quantity)
                            # multipled by the reward qty
                            reward_product_qty = program.category_quantity * program_in_order
                            # do not give more free reward than products
                            reward_product_qty = min(reward_product_qty, total_qty)
                            if program.rule_minimum_amount:
                                order_total = sum(order_lines.mapped('price_total')) - (
                                        program.category_quantity * product_id.lst_price)
                                print("order_total", order_total)
                                reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
                        else:
                            program_in_order = max_product_qty // program.category_qty
                            reward_product_qty = min(program.category_quantity * program_in_order, total_qty)

                        reward_qty = min(int(int(max_product_qty / program.category_qty) * program.category_quantity),
                                         reward_product_qty)
                if program.category_id2:
                    products = self.env['product.product'].search([('pos_categ_id', '=', program.category_id2.id)])
                    max_product_qty = 0
                    total_qty = 0
                    run = 0
                    order_lines = (self.order_line - self._get_reward_lines()).filtered(
                        lambda x: program._get_valid_products(x.product_id))
                    for product in products:
                        for line in self.order_line:
                            if product.id == line.product_id.id:
                                run += 1
                                price_unit = product_id.lst_price
                                max_product_qty += line.product_uom_qty
                                total_qty += line.product_uom_qty
                    if run >= 1:
                        if program._get_valid_products(product_id):
                            # number of times the program should be applied
                            program_in_order = max_product_qty // (program.category_qty2 + program.category_quantity)
                            # multipled by the reward qty
                            reward_product_qty = program.category_quantity * program_in_order
                            # do not give more free reward than products
                            reward_product_qty = min(reward_product_qty, total_qty)
                            if program.rule_minimum_amount:
                                order_total = sum(order_lines.mapped('price_total')) - (
                                        program.category_quantity * product_id.lst_price)
                                reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
                        else:
                            program_in_order = max_product_qty // program.category_qty2
                            reward_product_qty = min(program.category_quantity * program_in_order, total_qty)

                        reward_qty2 = min(int(int(max_product_qty / program.category_qty2) * program.category_quantity),
                                          reward_product_qty)
                if program.category_id3:
                    products = self.env['product.product'].search([('pos_categ_id', '=', program.category_id3.id)])
                    max_product_qty = 0
                    total_qty = 0
                    run = 0
                    order_lines = (self.order_line - self._get_reward_lines()).filtered(
                        lambda x: program._get_valid_products(x.product_id))
                    for product in products:
                        for line in self.order_line:
                            if product.id == line.product_id.id:
                                run += 1
                                price_unit = product_id.lst_price
                                max_product_qty += line.product_uom_qty
                                total_qty += line.product_uom_qty
                    if run >= 1:
                        if program._get_valid_products(product_id):
                            # number of times the program should be applied
                            program_in_order = max_product_qty // (program.category_qty3 + program.category_quantity)
                            # multipled by the reward qty
                            reward_product_qty = program.category_quantity * program_in_order
                            # do not give more free reward than products
                            reward_product_qty = min(reward_product_qty, total_qty)
                            if program.rule_minimum_amount:
                                order_total = sum(order_lines.mapped('price_total')) - (
                                        program.category_quantity * product_id.lst_price)
                                reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
                        else:
                            program_in_order = max_product_qty // program.category_qty3
                            reward_product_qty = min(program.category_quantity * program_in_order, total_qty)

                        reward_qty3 = min(int(int(max_product_qty / program.category_qty3) * program.category_quantity),
                                          reward_product_qty)

                total_reward_qty = reward_qty + reward_qty2 + reward_qty3

                return {
                    'product_id': program.discount_line_product_id.id,
                    'price_unit': - price_unit,
                    'product_uom_qty': program.category_quantity,
                    'is_reward_line': True,
                    'name': _("Free Product in") + program.product_categ_id.name,
                    # 'product_uom': product_id.uom_id.id,
                    # 'tax_id': [(4, tax.id, False) for tax in taxes],
                }

    def mm_create_line(self, reward_line):
        self.write({'order_line': [(0, False, value) for value in reward_line]})

    # done
    def _get_reward_values_product(self, program):
        domain = ast.literal_eval(program.rule_products_domain)
        price_unit = 0
        reward_qty = 0
        taxes = program.reward_product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes = self.fiscal_position_id.map_tax(taxes)

        products = self.env['product.product'].search(domain)
        max_product_qty = 0
        total_qty = 0
        run = 0
        order_lines = (self.order_line - self._get_reward_lines()).filtered(
            lambda x: program._get_valid_products(x.product_id))
        for product in products:
            for line in self.order_line:
                if product.id == line.product_id.id:
                    run += 1
                    price_unit = program.reward_product_id.lst_price
                    max_product_qty += line.product_uom_qty
                    total_qty += line.product_uom_qty
        if run >= 1:
            if program._get_valid_products(program.reward_product_id):
                # number of times the program should be applied
                program_in_order = max_product_qty // (program.rule_min_quantity + program.reward_product_quantity)
                # multipled by the reward qty
                reward_product_qty = program.reward_product_quantity * program_in_order
                # do not give more free reward than products
                reward_product_qty = min(reward_product_qty, total_qty)
                if program.rule_minimum_amount:
                    order_total = sum(order_lines.mapped('price_total')) - (
                            program.reward_product_quantity * program.reward_product_id.lst_price)
                    print("order_total", order_total)
                    reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
            else:
                program_in_order = max_product_qty // program.rule_min_quantity
                reward_product_qty = min(program.reward_product_quantity * program_in_order, total_qty)

            reward_qty = min(int(int(max_product_qty / program.rule_min_quantity) * program.reward_product_quantity),
                             reward_product_qty)

        return {
            'product_id': program.discount_line_product_id.id,
            'price_unit': - price_unit,
            'product_uom_qty': reward_qty,
            'is_reward_line': True,
            'name': _("Free Product") + " - " + program.reward_product_id.name,
            'product_uom': program.reward_product_id.uom_id.id,
            'tax_id': [(4, tax.id, False) for tax in taxes],
        }

    # done
    def _get_reward_values_product_category(self, program):
        price_unit = 0

        reward_qty = 0
        reward_qty2 = 0
        reward_qty3 = 0

        taxes = program.reward_product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes = self.fiscal_position_id.map_tax(taxes)

        if program.category_id:
            products = self.env['product.product'].search([('pos_categ_id', '=', program.category_id.id)])
            max_product_qty = 0
            total_qty = 0
            run = 0
            order_lines = (self.order_line - self._get_reward_lines()).filtered(
                lambda x: program._get_valid_products(x.product_id))
            for product in products:
                for line in self.order_line:
                    if product.id == line.product_id.id:
                        run += 1
                        price_unit = program.reward_product_id.lst_price
                        max_product_qty += line.product_uom_qty
                        total_qty += line.product_uom_qty
            if run >= 1:
                if program._get_valid_products(program.reward_product_id):
                    # number of times the program should be applied
                    program_in_order = max_product_qty // (program.category_qty + program.rule_min_quantity)
                    # multipled by the reward qty
                    reward_product_qty = program.rule_min_quantity * program_in_order
                    # do not give more free reward than products
                    reward_product_qty = min(reward_product_qty, total_qty)
                    if program.rule_minimum_amount:
                        order_total = sum(order_lines.mapped('price_total')) - (
                                program.rule_min_quantity * program.reward_product_id.lst_price)
                        print("order_total", order_total)
                        reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
                else:
                    program_in_order = max_product_qty // program.category_qty
                    reward_product_qty = min(program.rule_min_quantity * program_in_order, total_qty)

                reward_qty = min(int(int(max_product_qty / program.category_qty) * program.reward_product_quantity),
                                 reward_product_qty)
        if program.category_id2:
            products = self.env['product.product'].search([('pos_categ_id', '=', program.category_id2.id)])
            max_product_qty = 0
            total_qty = 0
            run = 0
            order_lines = (self.order_line - self._get_reward_lines()).filtered(
                lambda x: program._get_valid_products(x.product_id))
            for product in products:
                for line in self.order_line:
                    if product.id == line.product_id.id:
                        run += 1
                        price_unit = program.reward_product_id.lst_price
                        max_product_qty += line.product_uom_qty
                        total_qty += line.product_uom_qty
            if run >= 1:
                if program._get_valid_products(program.reward_product_id):
                    # number of times the program should be applied
                    program_in_order = max_product_qty // (program.category_qty2 + program.reward_product_quantity)
                    # multipled by the reward qty
                    reward_product_qty = program.reward_product_quantity * program_in_order
                    # do not give more free reward than products
                    reward_product_qty = min(reward_product_qty, total_qty)
                    if program.rule_minimum_amount:
                        order_total = sum(order_lines.mapped('price_total')) - (
                                program.reward_product_quantity * program.reward_product_id.lst_price)
                        reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
                else:
                    program_in_order = max_product_qty // program.category_qty2
                    reward_product_qty = min(program.reward_product_quantity * program_in_order, total_qty)

                reward_qty2 = min(int(int(max_product_qty / program.category_qty2) * program.reward_product_quantity),
                                  reward_product_qty)
        if program.category_id3:
            products = self.env['product.product'].search([('pos_categ_id', '=', program.category_id3.id)])
            max_product_qty = 0
            total_qty = 0
            run = 0
            order_lines = (self.order_line - self._get_reward_lines()).filtered(
                lambda x: program._get_valid_products(x.product_id))
            for product in products:
                for line in self.order_line:
                    if product.id == line.product_id.id:
                        run += 1
                        price_unit = program.reward_product_id.lst_price
                        max_product_qty += line.product_uom_qty
                        total_qty += line.product_uom_qty
            if run >= 1:
                if program._get_valid_products(program.reward_product_id):
                    # number of times the program should be applied
                    program_in_order = max_product_qty // (program.category_qty3 + program.reward_product_quantity)
                    # multipled by the reward qty
                    reward_product_qty = program.reward_product_quantity * program_in_order
                    # do not give more free reward than products
                    reward_product_qty = min(reward_product_qty, total_qty)
                    if program.rule_minimum_amount:
                        order_total = sum(order_lines.mapped('price_total')) - (
                                program.reward_product_quantity * program.reward_product_id.lst_price)
                        reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
                else:
                    program_in_order = max_product_qty // program.category_qty3
                    reward_product_qty = min(program.reward_product_quantity * program_in_order, total_qty)

                reward_qty3 = min(int(int(max_product_qty / program.category_qty3) * program.rule_min_quantity),
                                  reward_product_qty)

        total_reward_qty = reward_qty + reward_qty2 + reward_qty3

        return {
            'product_id': program.discount_line_product_id.id,
            'price_unit': - price_unit,
            'product_uom_qty': total_reward_qty,
            'is_reward_line': True,
            'name': _("Free Product") + " - " + program.reward_product_id.name,
            'product_uom': program.reward_product_id.uom_id.id,
            'tax_id': [(4, tax.id, False) for tax in taxes],
        }


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'
    category = fields.Char(string='Category', compute='get_category')

    def get_category(self):
        product_categ_id = fields.Many2one(related='product_id.product_tmpl_id.categ_id', string='Product Category')

