# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

from odoo.addons.bigmcp.models.mcp_server import McpInvalidParams

_logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "odoo-bigmcp", "version": "1.0.0"}


def _error(msg_id, code, message):
    """Build a JSON-RPC 2.0 error envelope."""
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


class McpController(http.Controller):
    """Streamable HTTP transport for MCP: a single stateless JSON-RPC 2.0 endpoint.

    Authentication is Odoo's bearer scheme (``Authorization: Bearer <api key>``),
    so every call runs with the access rights of the key's owner.
    """

    @http.route('/mcp', type='http', auth='bearer', methods=['POST'], csrf=False)
    def mcp(self, **kwargs):
        """Parse the JSON-RPC body (single message or batch), dispatch it and return JSON."""
        if not request.env.user.has_group('bigmcp.group_user'):
            return self._json_response(
                _error(None, -32000, "User is not a member of the MCP User group."), status=403)
        try:
            body = json.loads(request.httprequest.get_data())
        except ValueError:
            return self._json_response(_error(None, -32700, "Parse error"), status=400)

        messages = body if isinstance(body, list) else [body]
        responses = [r for r in map(self._handle, messages) if r is not None]
        if not responses:
            # Notifications only: the spec asks for 202 Accepted with no body.
            return request.make_response('', status=202)
        return self._json_response(responses if isinstance(body, list) else responses[0])

    @staticmethod
    def _json_response(payload, status=200):
        """Serialize the JSON-RPC payload with the given HTTP status."""
        return request.make_json_response(payload, status=status)

    def _handle(self, message):
        """Route one JSON-RPC message to its handler; notifications (no id) return None."""
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
            return _error(None, -32600, "Invalid Request")
        msg_id = message.get('id')
        method = message.get('method')
        params = message.get('params') or {}
        if not isinstance(method, str):
            return _error(msg_id, -32600, "Invalid Request")
        if method.startswith('notifications/'):
            return None
        handler = self._HANDLERS.get(method)
        if handler is None:
            return _error(msg_id, -32601, f"Method not found: {method}")
        try:
            return {"jsonrpc": "2.0", "id": msg_id, "result": handler(self, params)}
        except McpInvalidParams as exc:
            return _error(msg_id, -32602, str(exc))

    def _initialize(self, params):
        """Handshake: advertise the tools capability and the server instructions."""
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
            "instructions": request.env['mcp.server']._instructions(),
        }

    def _ping(self, params):
        """Liveness check."""
        return {}

    def _tools_list(self, params):
        """Return the static tool definitions."""
        return {"tools": request.env['mcp.server']._tool_definitions()}

    def _tools_call(self, params):
        """Execute one tool; execution errors come back as a tool result, not a JSON-RPC error."""
        name = params.get('name')
        arguments = params.get('arguments') or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise McpInvalidParams("tools/call needs a 'name' string and an 'arguments' object.")
        return request.env['mcp.server']._call_tool(name, arguments)

    _HANDLERS = {
        'initialize': _initialize,
        'ping': _ping,
        'tools/list': _tools_list,
        'tools/call': _tools_call,
        'resources/list': lambda self, params: {"resources": []},
        'resources/templates/list': lambda self, params: {"resourceTemplates": []},
        'prompts/list': lambda self, params: {"prompts": []},
    }
