from odoo import models, fields, api, _


class PromotionWizard(models.TransientModel):
    _name = "promotion.wizard"

    sale_id = fields.Many2one('sale.order', string="Sale Order")
    promotion_text = fields.Text()

    def action_confirm(self):
        for record in self:
            record.sale_id.promotion_wizard = True
            record.sale_id.action_confirm()
