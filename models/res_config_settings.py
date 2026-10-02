# -*- coding: utf-8 -*-
from odoo import fields, models

from .mcp_server import DEFAULT_MAX_RESULT_TOKENS


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bigmcp_max_result_tokens = fields.Integer(
        string="MCP Result Limit (tokens)",
        config_parameter='bigmcp.max_result_tokens',
        default=DEFAULT_MAX_RESULT_TOKENS,
        help="Largest result one MCP tool call may return to the assistant; longer results are cut. "
             "Tokens are estimated at 3 characters each.")
