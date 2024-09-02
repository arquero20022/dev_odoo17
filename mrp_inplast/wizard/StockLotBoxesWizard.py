from odoo import _, api, fields, models
from odoo.exceptions import UserError

class StockLotBoxesWizard(models.TransientModel):
    _name = 'stock.lot.boxes.wizard'
    _description = 'Add boxes to Stock Lot'

    lot_id = fields.Many2one(
        'stock.lot', required=True,
        default=lambda self: self.env.context.get('lot_id', None)
    )
    pnt_barcode_input = fields.Text('Boxes read')
    pnt_processed_barcodes = fields.Many2many('stock.lot', string="Boxes")
    processed_count = fields.Integer(
        string="Processed Count", compute='_compute_counts', store=True
    )
    remaining_count = fields.Integer(
        string="Remaining to Max", compute='_compute_counts', store=True
    )
    show_confirmation = fields.Boolean(default=False)

    @api.depends('pnt_processed_barcodes')
    def _compute_counts(self):
        for record in self:
            box_qty = record.lot_id.product_id.pnt_box_qty
            record.processed_count = len(record.pnt_processed_barcodes)
            record.remaining_count = max(0, box_qty - record.processed_count)

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if self.lot_id:
            lots = self.env['stock.lot'].search([('parent_id', '=', self.lot_id.id)])
            self.pnt_processed_barcodes = [(6, 0, lots.ids)]
            self.pnt_barcode_input = ''
        else:
            self.pnt_processed_barcodes = [(5, 0, 0)]

    def _process_barcode_input(self):
        for record in self:
            max_boxes = record.lot_id.product_id.pnt_box_qty
            if max_boxes == 0:
                raise UserError(_("Box quantity = 0 please set a box quantity."))

            if not record.pnt_barcode_input:
                continue

            line = record.pnt_barcode_input
            lots_to_process = line.split('MO')
            lots_to_process = [lot.strip() for lot in lots_to_process if lot.strip()]
            subproduct = None

            if not lots_to_process:
                continue

            matching_record = None
            for packing_record in record.lot_id.product_id.pnt_parent_id.pnt_packing_ids:
                pallet_qty = record.lot_id.product_id.pnt_parent_qty
                if pallet_qty == 0:
                    raise UserError(_("Parent quantity = 0 please set a parent quantity."))
                box_qty = record.lot_id.product_id.pnt_box_qty
                division = pallet_qty // box_qty
                check_qty = packing_record.pnt_parent_qty

                if division == check_qty:
                    matching_record = packing_record.id
                    break

            if matching_record:
                subproduct = self.env['product.product'].search([
                    ('pnt_product_type', '=', 'packing'),
                    ('id', '=', matching_record),
                    ('id', 'in', record.lot_id.product_id.pnt_parent_id.pnt_packing_ids.ids),
                ], limit=1)
            else:
                raise UserError(_("No subproduct with type 'box' and correct quantity was found."))

            existing_lots = self.env['stock.lot'].search([('parent_id', '=', record.lot_id.id)])
            existing_lots_count = len(existing_lots)

            if existing_lots_count + len(lots_to_process) > max_boxes:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Error"),
                        "message": _("You have exceeded the allowed box quantity. No new lots were created."),
                        "sticky": False,
                        "type": "danger",
                    },
                }

            try:
                for lot in lots_to_process:
                    lot_name = 'MO' + lot
                    exist = self.env['stock.lot'].search([('name', '=', lot_name)])
                    if not exist:
                        new_lot = self.env['stock.lot'].create({
                            'product_id': subproduct.id,
                            'name': lot_name,
                            'parent_id': record.lot_id.id,
                        })
                    lots = self.env['stock.lot'].search([('parent_id', '=', record.lot_id.id)])
                    record.pnt_processed_barcodes = [(6, 0, lots.ids)]
            except Exception as e:
                raise UserError(_("Error processing barcodes: %s") % str(e))

            if record.lot_id:
                record.lot_id.related_boxes_ids = [(6, 0, record.pnt_processed_barcodes.ids)]

    def _process_lot_removal(self):
        if not self.pnt_barcode_input:
            raise UserError(_("Please enter a lot name to remove."))

        lot_names = self.pnt_barcode_input.split('MO')
        lot_names = [lot_name.strip() for lot_name in lot_names if lot_name.strip()]

        if not lot_names:
            raise UserError(_("Please enter at least one valid lot name."))

        not_found_lots = []

        for lot_name in lot_names:
            lot_name_full = 'MO' + lot_name
            lot_to_remove = self.env['stock.lot'].search(
                [('name', '=', lot_name_full), ('parent_id', '=', self.lot_id.id)]
            )
            if not lot_to_remove:
                not_found_lots.append(lot_name_full)

        if not_found_lots:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Lots Not Found"),
                    "message": _("The following lots do not exist and no lots were removed: %s") % ', '.join(not_found_lots),
                    "sticky": False,
                    "type": "danger",
                },
            }

        for lot_name in lot_names:
            lot_name_full = 'MO' + lot_name
            lot_to_remove = self.env['stock.lot'].search(
                [('name', '=', lot_name_full), ('parent_id', '=', self.lot_id.id)]
            )
            lot_to_remove.unlink()

        if self.lot_id:
            lots = self.env['stock.lot'].search([('parent_id', '=', self.lot_id.id)])
            self.pnt_processed_barcodes = [(6, 0, lots.ids)]

    def trigger_remove_lot(self):
        self.show_confirmation = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot.boxes.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def confirm_remove_lot(self):
        try:
            action = self._process_lot_removal()
            if action:
                return action
        except UserError as e:
            self._onchange_lot_id()
            self.show_confirmation = False
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": str(e),
                    "sticky": False,
                    "type": "danger",
                },
            }
        else:
            self.show_confirmation = False
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.lot.boxes.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

    def cancel_remove_lot(self):
        self.show_confirmation = False
        self._onchange_lot_id()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot.boxes.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def add_lots(self):
        action = self._process_barcode_input()
        if action:
            return action
        self._onchange_lot_id()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot.boxes.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
