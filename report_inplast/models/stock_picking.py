from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def get_template_report(self):
        return "report_inplast.pnt_report_delivery_document"


    def get_move_lines_by_parent_lot(self):
        lines = []
        parent_lot = ""
        for line in self.move_line_ids:
            if parent_lot != line.lot_id.parent_id.name:
                parent_lot = line.lot_id.parent_id.name
                lines.append(line)
        return lines
