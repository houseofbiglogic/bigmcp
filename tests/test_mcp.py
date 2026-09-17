# -*- coding: utf-8 -*-
import json

from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.bigmcp.models.mcp_server import McpInvalidParams


class TestMcpTools(TransactionCase):
    """Tool behaviour through the mcp.server model, independent of the transport."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = cls.env['mcp.server']
        partner_model = cls.env['ir.model']._get('res.partner')
        cls.env['mcp.note'].create([
            {'name': 'Partners', 'model_id': partner_model.id, 'content': 'Customers and vendors.'},
            {'name': 'Deleting', 'model_id': partner_model.id, 'method': 'unlink', 'content': 'Archive instead.'},
        ])

    def _call(self, name, **arguments):
        """Run a tool and return the decoded JSON of a successful result."""
        result = self.server._call_tool(name, arguments)
        self.assertFalse(result.get('isError'), result['content'][0]['text'])
        return json.loads(result['content'][0]['text'])

    def test_instructions_contain_global_notes(self):
        """The seeded global note is part of the initialize instructions."""
        self.assertIn('unlink = delete', self.server._instructions())

    def test_list_models(self):
        """list_models finds a model by technical name."""
        models = self._call('list_models', query='res.partner')
        self.assertIn('res.partner', [m['model'] for m in models])

    def test_describe_model(self):
        """describe_model returns fields, model-specific methods and both note scopes."""
        info = self._call('describe_model', model='res.partner')
        self.assertEqual(info['fields']['name']['type'], 'char')
        self.assertIn('address_get', info['methods'])
        self.assertNotIn('search_read', info['methods'])
        self.assertIn('Customers and vendors', info['notes'])
        self.assertIn('Archive instead', info['method_notes']['unlink'])

    def test_describe_method(self):
        """describe_method returns the api_doc signature and the method note."""
        info = self._call('describe_method', model='res.partner', method='unlink')
        self.assertIn('signature', info)
        self.assertEqual(info['defined_in'], 'core')
        self.assertIn('Archive instead', info['notes'])

    def test_call_method_round_trip(self):
        """create, write, search_read and unlink work through the generic tools."""
        partner_id = self._call('call_method', model='res.partner', method='create',
                                args=[{'name': 'MCP Test Partner'}])
        self._call('call_method', model='res.partner', method='write',
                   ids=[partner_id], args=[{'phone': '123'}])
        rows = self._call('search_read', model='res.partner',
                          domain=[['id', '=', partner_id]], fields=['name', 'phone'])
        self.assertEqual(rows[0]['phone'], '123')
        self._call('call_method', model='res.partner', method='unlink', ids=[partner_id])
        self.assertFalse(self.env['res.partner'].browse(partner_id).exists())

    def test_private_method_is_a_tool_error(self):
        """Private methods are refused and reported as a tool error, not an exception."""
        result = self.server._call_tool('call_method', {'model': 'res.partner', 'method': '_compute_display_name'})
        self.assertTrue(result['isError'])

    def test_unknown_tool_and_missing_args(self):
        """Protocol-level mistakes raise McpInvalidParams for the -32602 error."""
        with self.assertRaises(McpInvalidParams):
            self.server._call_tool('nope', {})
        with self.assertRaises(McpInvalidParams):
            self.server._call_tool('describe_model', {})


@tagged('post_install', '-at_install')
class TestMcpEndpoint(HttpCase):
    """JSON-RPC transport at /mcp with bearer authentication."""

    def setUp(self):
        super().setUp()
        user = self.env.ref('base.user_admin')
        self.env.ref('bigmcp.group_user').write({'user_ids': [(4, user.id)]})
        key = self.env['res.users.apikeys'].with_user(user)._generate(None, 'mcp test', False)
        self.headers = {'Authorization': f'Bearer {key}'}

    def _rpc(self, method, params=None, msg_id=1):
        """POST one JSON-RPC message and return the HTTP response."""
        payload = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
        if msg_id is not None:
            payload['id'] = msg_id
        return self.url_open('/mcp', json=payload, headers=self.headers)

    def test_initialize_and_tools_list(self):
        """Handshake returns the protocol version; tools/list advertises call_method."""
        init = self._rpc('initialize').json()['result']
        self.assertEqual(init['protocolVersion'], '2025-06-18')
        self.assertIn('unlink = delete', init['instructions'])
        tools = self._rpc('tools/list').json()['result']['tools']
        self.assertIn('call_method', [t['name'] for t in tools])

    def test_tools_call(self):
        """A tool call over HTTP returns MCP content."""
        result = self._rpc('tools/call', {'name': 'list_models', 'arguments': {'query': 'res.users'}}).json()['result']
        self.assertIn('res.users', result['content'][0]['text'])

    def test_notification_returns_202(self):
        """Notifications get 202 Accepted and no body."""
        response = self._rpc('notifications/initialized', msg_id=None)
        self.assertEqual(response.status_code, 202)

    def test_unknown_method(self):
        """Unknown JSON-RPC methods return -32601."""
        self.assertEqual(self._rpc('nope').json()['error']['code'], -32601)

    def test_without_key_is_unauthorized(self):
        """No bearer header and no session means 401."""
        response = self.url_open('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'ping'})
        self.assertEqual(response.status_code, 401)
