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