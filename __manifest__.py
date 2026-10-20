# -*- coding: utf-8 -*-
{
    'name': 'BigMCP - Odoo MCP Server',
    'version': '19.0.2.0.1',
    'category': 'Biglogic',
    'summary': 'Expose the whole Odoo ORM to AI assistants over the Model Context Protocol',
    # No 'description': Odoo renders README.rst as the module description.
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
