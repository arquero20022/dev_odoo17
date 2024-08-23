from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def get_quantity_done_by_lot(self):
        for record in self:
            quantity = 0.0
            sml = self.search([('picking_id', '=', record.picking_id.id),('lot_id.parent_id', '=', record.lot_id.parent_id.id)])
            for line in sml:
                quantity += line.quantity

            record.quantity_done_by_lot = quantity

    quantity_done_by_lot = fields.Float(compute='get_quantity_done_by_lot')

