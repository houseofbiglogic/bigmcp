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

    def test_instructions_aggregation_call(self):
        """The aggregation call recommended by the instructions works as written, through call_method."""
        self.assertIn('formatted_read_group', self.server._instructions())
        groups = self._call('call_method', model='res.partner', method='formatted_read_group',
                            kwargs={'domain': [], 'groupby': ['is_company'], 'aggregates': ['__count']})
        self.assertEqual(sum(group['__count'] for group in groups), self.env['res.partner'].search_count([]))

    def test_list_models(self):
        """list_models finds a model by technical name, under the module that defines it."""
        models = self._call('list_models', query='res.partner')
        self.assertIn('res.partner', models['base'])

    def test_list_models_is_complete(self):
        """Without a query every readable model is listed; 'module' keeps the models that module defines."""
        models = self._call('list_models')
        readable = [
            name for name in self.env['ir.model'].search([]).mapped('model')
            if name in self.env and self.env[name].has_access('read')
        ]
        self.assertEqual(sum(len(group) for group in models.values()), len(readable))
        self.assertEqual(models['bigmcp'], {'mcp.note': 'MCP Note', 'mcp.server': 'MCP Server'})
        self.assertEqual(self._call('list_models', module='bigmcp'), {'bigmcp': models['bigmcp']})

    def test_describe_model(self):
        """describe_model returns fields, model-specific methods and both note scopes."""
        info = self._call('describe_model', model='res.partner')
        self.assertEqual(info['fields']['name']['type'], 'char')
        self.assertIn('address_get', info['methods'])
        self.assertNotIn('search_read', info['methods'])
        self.assertIn('Customers and vendors', info['notes'])
        self.assertIn('Archive instead', info['method_notes']['unlink'])

    def test_describe_model_generic_methods_on_request(self):
        """Methods every model has, from BaseModel or added through 'base', are only listed on request."""
        methods = self._call('describe_model', model='res.partner', include_fields=False)['methods']
        self.assertNotIn('web_read', methods)
        methods = self._call('describe_model', model='res.partner', include_fields=False,
                             include_orm_methods=True)['methods']
        self.assertIn('web_read', methods)
        self.assertIn('search_read', methods)

    def test_describe_model_flags_unsearchable_fields(self):
        """Only the fields a domain cannot use carry the 'searchable' flag, set to False."""
        fields = self._call('describe_model', model='res.partner', include_methods=False)['fields']
        self.assertIs(fields['contact_address']['searchable'], False)
        self.assertNotIn('searchable', fields['name'])

    def test_describe_model_help_only_for_named_fields(self):
        """The overview keeps every selection option but no help text; naming a field adds the help."""
        overview = self._call('describe_model', model='res.partner', include_methods=False)['fields']
        self.assertNotIn('help', overview['tz'])
        detail = self._call('describe_model', model='res.partner', fields=['tz'], include_methods=False)['fields']
        self.assertEqual(list(detail), ['tz'])
        self.assertIn('help', detail['tz'])
        self.assertEqual(detail['tz']['selection'], overview['tz']['selection'])

    def test_binary_fields_come_back_as_size(self):
        """Reads return the size of a binary field; the content needs an explicit bin_size=False."""
        attachment = self.env['ir.attachment'].create({'name': 'mcp.txt', 'raw': b'hello'})
        rows = self._call('search_read', model='ir.attachment',
                          domain=[['id', '=', attachment.id]], fields=['datas'])['records']
        self.assertNotEqual(rows[0]['datas'], 'aGVsbG8=')
        rows = self._call('call_method', model='ir.attachment', method='read',
                          ids=[attachment.id], args=[['datas']])
        self.assertNotEqual(rows[0]['datas'], 'aGVsbG8=')
        rows = self._call('call_method', model='ir.attachment', method='read',
                          ids=[attachment.id], args=[['datas']], context={'bin_size': False})
        self.assertEqual(rows[0]['datas'], 'aGVsbG8=')

    def test_search_read_total_and_archived(self):
        """'total' counts every match beyond the page; archived records only come with active_test=False."""
        partners = self.env['res.partner'].create([{'name': f'MCP Count {i}'} for i in range(3)])
        partners[0].action_archive()
        domain = [['id', 'in', partners.ids]]
        result = self._call('search_read', model='res.partner', domain=domain, limit=1)
        self.assertEqual(result['total'], 2)
        self.assertEqual(len(result['records']), 1)
        result = self._call('search_read', model='res.partner', domain=domain, context={'active_test': False})
        self.assertEqual(result['total'], 3)
        self.assertEqual(len(result['records']), 3)

    def test_call_method_keeps_caller_context(self):
        """The context of the calling environment (language, companies...) survives a call_method call."""
        partner = self.env['res.partner'].create({'name': 'MCP Archived'})
        partner.action_archive()
        result = self.server.with_context(active_test=False)._call_tool('call_method', {
            'model': 'res.partner', 'method': 'search_count', 'args': [[['id', '=', partner.id]]]})
        self.assertEqual(result['content'][0]['text'], '1')

    def test_oversized_result_is_truncated(self):
        """A result above the configured token limit is cut there and ends with the narrowing hint."""
        self.env['ir.config_parameter'].set_param('bigmcp.max_result_tokens', 10)
        text = self.server._call_tool('list_models', {})['content'][0]['text']
        self.assertEqual(text.index('\n[Truncated'), 30)

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
                          domain=[['id', '=', partner_id]], fields=['name', 'phone'])['records']
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
