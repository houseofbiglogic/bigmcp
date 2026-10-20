# -*- coding: utf-8 -*-
import base64
import json
import logging

from odoo import http
from odoo.http import request
from odoo.modules.module import get_manifest

from odoo.addons.bigmcp.models.mcp_server import McpInvalidParams

_logger = logging.getLogger(__name__)

# Modern revisions carry the protocol version in every request's _meta and need no handshake.
MODERN_VERSIONS = ("2026-07-28",)
# Legacy revisions open with an initialize handshake; the client's choice is echoed when known.
LEGACY_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
DEFAULT_LEGACY_VERSION = "2025-06-18"
META_PROTOCOL_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"
META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"
# The server version follows the module version so it never drifts from the manifest.
SERVER_INFO = {"name": "odoo-bigmcp", "version": get_manifest('bigmcp')['version']}
# Error codes reserved by the MCP specification (2026-07-28).
HEADER_MISMATCH = -32020
UNSUPPORTED_PROTOCOL_VERSION = -32022


class McpHttpError(Exception):
    """A JSON-RPC error that must be delivered with a specific HTTP status (modern requests only)."""

    def __init__(self, status, code, message, data=None):
        super().__init__(message)
        self.status, self.code, self.message, self.data = status, code, message, data


def _error(msg_id, code, message, data=None):
    """Build a JSON-RPC 2.0 error envelope."""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": error}


def _decode_header(value):
    """Undo the '=?base64?...?=' sentinel encoding clients use for non-ASCII header values."""
    if value and value.startswith("=?base64?") and value.endswith("?="):
        try:
            return base64.b64decode(value[9:-2]).decode()
        except (ValueError, UnicodeDecodeError):
            return None
    return value


def _is_modern(message):
    """A modern request names its protocol version in params._meta; anything else is legacy."""
    params = message.get('params') if isinstance(message, dict) else None
    meta = params.get('_meta') if isinstance(params, dict) else None
    return isinstance(meta, dict) and META_PROTOCOL_VERSION in meta


class McpController(http.Controller):
    """Streamable HTTP transport for MCP: a single stateless JSON-RPC 2.0 endpoint serving two eras.

    Modern clients (2026-07-28) carry version and capabilities in every request;
    legacy clients open with ``initialize`` and are served the revision they ask for.
    Authentication is Odoo's bearer scheme (``Authorization: Bearer <api key>``),
    so every call runs with the access rights of the key's owner.
    """

    @http.route('/mcp', type='http', auth='bearer', methods=['POST'], csrf=False)
    def mcp(self, **kwargs):
        """Check group and Origin, parse the body and dispatch it to the era it belongs to."""
        if not request.env.user.has_group('bigmcp.group_user'):
            return self._json_response(
                _error(None, -32000, "User is not a member of the MCP User group."), status=403)
        origin = request.httprequest.headers.get('Origin')
        if origin and not request.env['mcp.server']._origin_allowed(origin, request.httprequest.host_url):
            return self._json_response(_error(None, -32600, "Origin not allowed."), status=403)
        try:
            body = json.loads(request.httprequest.get_data())
        except ValueError:
            return self._json_response(_error(None, -32700, "Parse error"), status=400)

        if isinstance(body, list):
            if any(_is_modern(message) for message in body):
                return self._json_response(
                    _error(None, -32600, "Batching is not supported since protocol version 2026-07-28."), status=400)
            responses = [r for r in map(self._handle_legacy, body) if r is not None]
            if not responses:
                # Notifications only: the spec asks for 202 Accepted with no body.
                return request.make_response('', status=202)
            return self._json_response(responses)
        if _is_modern(body):
            return self._handle_modern(body)
        response = self._handle_legacy(body)
        if response is None:
            return request.make_response('', status=202)
        return self._json_response(response)

    @staticmethod
    def _json_response(payload, status=200):
        """Serialize the JSON-RPC payload with the given HTTP status."""
        return request.make_json_response(payload, status=status)

    # ------------------------------------------------------------------
    # Legacy era: initialize handshake, protocol versions up to 2025-11-25
    # ------------------------------------------------------------------
    def _handle_legacy(self, message):
        """Route one legacy JSON-RPC message to its handler; notifications (no id) return None."""
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
            return _error(None, -32600, "Invalid Request")
        msg_id = message.get('id')
        method = message.get('method')
        params = message.get('params') or {}
        if not isinstance(method, str):
            return _error(msg_id, -32600, "Invalid Request")
        if method.startswith('notifications/'):
            return None
        handler = self._LEGACY_HANDLERS.get(method)
        if handler is None:
            return _error(msg_id, -32601, f"Method not found: {method}")
        try:
            return {"jsonrpc": "2.0", "id": msg_id, "result": handler(self, params)}
        except McpInvalidParams as exc:
            return _error(msg_id, -32602, str(exc))

    def _initialize(self, params):
        """Handshake: echo the requested revision when known, advertise the tools capability and the instructions."""
        requested = params.get('protocolVersion')
        return {
            "protocolVersion": requested if requested in LEGACY_VERSIONS else DEFAULT_LEGACY_VERSION,
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

    _LEGACY_HANDLERS = {
        'initialize': _initialize,
        'ping': _ping,
        'tools/list': _tools_list,
        'tools/call': _tools_call,
        'resources/list': lambda self, params: {"resources": []},
        'resources/templates/list': lambda self, params: {"resourceTemplates": []},
        'prompts/list': lambda self, params: {"prompts": []},
    }

    # ------------------------------------------------------------------
    # Modern era: per-request metadata, protocol version 2026-07-28
    # ------------------------------------------------------------------
    def _handle_modern(self, message):
        """Validate a modern request, run its handler and return the HTTP response the spec prescribes."""
        msg_id = message.get('id')
        method = message.get('method')
        if message.get('jsonrpc') != '2.0' or not isinstance(method, str):
            return self._json_response(_error(msg_id, -32600, "Invalid Request"), status=400)
        if msg_id is None:
            # Notifications get 202 Accepted with no body.
            return request.make_response('', status=202)
        try:
            self._check_modern_request(message)
            handler = self._MODERN_HANDLERS.get(method)
            if handler is None:
                raise McpHttpError(404, -32601, f"Method not found: {method}")
            result = handler(self, message['params'])
        except McpHttpError as exc:
            return self._json_response(_error(msg_id, exc.code, exc.message, exc.data), status=exc.status)
        except McpInvalidParams as exc:
            return self._json_response(_error(msg_id, -32602, str(exc)))
        result.update(resultType="complete", _meta={META_SERVER_INFO: SERVER_INFO})
        return self._json_response({"jsonrpc": "2.0", "id": msg_id, "result": result})

    def _check_modern_request(self, message):
        """Enforce the required _meta fields, a supported protocol version and the mirrored HTTP headers."""
        params = message['params']
        meta = params['_meta']
        missing = [key for key in (META_PROTOCOL_VERSION, META_CLIENT_CAPABILITIES) if key not in meta]
        if missing:
            raise McpHttpError(400, -32602, f"Missing required _meta fields: {', '.join(missing)}")
        version = meta[META_PROTOCOL_VERSION]
        if version not in MODERN_VERSIONS:
            raise McpHttpError(400, UNSUPPORTED_PROTOCOL_VERSION, "Unsupported protocol version",
                               {"supported": list(MODERN_VERSIONS), "requested": version})
        expected = {'MCP-Protocol-Version': version, 'Mcp-Method': message['method']}
        if message['method'] == 'tools/call':
            expected['Mcp-Name'] = params.get('name')
        headers = request.httprequest.headers
        for name, value in expected.items():
            got = _decode_header(headers.get(name))
            if got != value:
                raise McpHttpError(400, HEADER_MISMATCH,
                                   f"Header mismatch: {name} header value {got!r} does not match body value {value!r}")

    def _discover(self, params):
        """Supported versions, capabilities, identity and instructions in one cacheable result."""
        server = request.env['mcp.server']
        return {
            "supportedVersions": list(MODERN_VERSIONS),
            "capabilities": {"tools": {}},
            "instructions": server._instructions(),
            **server._cache_hints(),
        }

    def _tools_list_modern(self, params):
        """The static tool definitions with their cache hints."""
        return {**self._tools_list(params), **request.env['mcp.server']._cache_hints()}

    _MODERN_HANDLERS = {
        'server/discover': _discover,
        'tools/list': _tools_list_modern,
        'tools/call': _tools_call,
    }
