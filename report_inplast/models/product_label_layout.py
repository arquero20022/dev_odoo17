from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    print_format = fields.Selection(
        selection_add=[
            ("warehouse", "Warehouse Label"),
            ("production", "Production Label"),
        ],
        ondelete={
            "warehouse": "set default",
            "production": "set default",
        },
    )

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()

        #añadir lógia nuvos selection
        if "x" in self.print_format:
            if self.rows == 6 and self.columns == 5:
                xml_id = "custom_azarey.pnt_report_producttemplate_label"

        return xml_id, data