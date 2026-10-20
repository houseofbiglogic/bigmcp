# -*- coding: utf-8 -*-
from odoo import fields, models

from .mcp_server import DEFAULT_CACHE_TTL_MINUTES, DEFAULT_MAX_RESULT_TOKENS


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bigmcp_max_result_tokens = fields.Integer(
        string="MCP Result Limit (tokens)",
        config_parameter='bigmcp.max_result_tokens',
        default=DEFAULT_MAX_RESULT_TOKENS,
        help="Largest result one MCP tool call may return to the assistant; longer results are cut. "
             "Tokens are estimated at 3 characters each.")
    bigmcp_cache_ttl_minutes = fields.Integer(
        string="MCP Cache Duration (minutes)",
        config_parameter='bigmcp.cache_ttl_minutes',
        default=DEFAULT_CACHE_TTL_MINUTES,
        help="How long MCP clients may reuse the tool list and the server instructions (global notes) "
             "before asking again. A new global note reaches the assistant after at most this delay. "
             "Empty or 0 restores the default.")
    bigmcp_allowed_origins = fields.Char(
        string="MCP Allowed Origins",
        config_parameter='bigmcp.allowed_origins',
        default='*',
        help="Browser origins allowed to call /mcp: '*' (the default) allows any, otherwise a comma separated "
             "list such as https://claude.ai. Odoo's own address is always allowed. "
             "Requests without an Origin header (server to server) are never blocked.")
