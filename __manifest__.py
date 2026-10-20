# -*- coding: utf-8 -*-
{
    'name': 'BigMCP - Odoo MCP Server',
    'version': '19.0.2.0.0',
    'category': 'Biglogic',
    'summary': 'Expose the whole Odoo ORM to AI assistants over the Model Context Protocol',
    'description': """
BigMCP - Odoo MCP Server
========================

A stateless Model Context Protocol (Streamable HTTP, JSON-RPC 2.0) endpoint at
``POST /mcp``. Instead of hand-written tools per workflow, the assistant discovers
models, fields and public methods through the ``api_doc`` reflection layer and
then reads or calls them through generic tools, always as the authenticated
Odoo user (API key, Bearer header). Administrators document the API for the
assistant with notes attached globally, to a model or to a single method.
    """,
    'author': 'BigLogic',
    'website': 'https://biglogic.tech',
    'license': 'LGPL-3',
    'depends': ['api_doc'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'models/mcp_note.xml',
        'views/res_config_settings_views.xml',
        'data/mcp_note_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
