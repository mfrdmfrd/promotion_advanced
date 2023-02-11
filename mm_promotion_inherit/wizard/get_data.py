# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class GsGetDataWizard(models.TransientModel):
    _name = "get.data.wizard"

    coupon_program_id = fields.Many2one('coupon.program', string="Promotion")
    product_category_id = fields.Many2one('product.product', string="Free Product")
    hide_field = fields.Boolean()

    @api.onchange('coupon_program_id')
    def domain_partner_id(self):
        if self.coupon_program_id.reward_type != 'category':
            self.hide_field = True
        else:
            self.hide_field = False

        if self.coupon_program_id.product_categ_id:
            active_id = self.env.context.get('active_id')
            sale_order = self.env['sale.order'].search([('id', '=', active_id)])
            product_id = []
            for line in sale_order.order_line:
                product_id.append(line.product_id.id)
            if self.coupon_program_id.reward_type != 'category':
                return {'domain': {'product_category_id': [('pos_categ_id', '=', self.coupon_program_id.product_categ_id.id),('id', 'in', product_id)]}}
            else:
                return {'domain': {'product_category_id': [('id', 'in', product_id)]}}

    def action_get_data(self):
        active_id = self.env.context.get('active_id')
        sale_order = self.env['sale.order'].search([('id', '=', active_id)])
        program = self.coupon_program_id
        product = self.product_category_id
        sale_order._remove_invalid_reward_lines()
        reward_line = sale_order._get_reward_line_values(program, product)
        sale_order.mm_create_line(reward_line)
