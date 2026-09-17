# -*- coding: utf-8 -*-
import inspect
import json
import logging

from odoo import models
from odoo.exceptions import UserError
from odoo.service.model import call_kw, get_public_method
from odoo.tools import json_default

from odoo.addons.api_doc.controllers.api_doc import is_public_method, parse_signature

_logger = logging.getLogger(__name__)

# Attributes of fields_get() worth sending to an assistant; falsy values are dropped.
FIELD_ATTRIBUTES = ('type', 'string', 'help', 'required', 'readonly', 'relation', 'selection')

INSTRUCTIONS = """You are connected to an Odoo ERP through its ORM.
Workflow: list_models -> describe_model -> (describe_method) -> search_read / call_method.
Every model supports the standard ORM methods even when describe_model does not list them:
search_read, search_count, read, create, write, unlink, name_search, default_get, copy,
read_group, fields_get. Domains are lists of [field, operator, value] triplets combined
with prefix operators '&', '|', '!'. Relational fields are written as ids; x2many fields
use command tuples such as [4, id], [3, id], [6, 0, [ids]], [0, 0, {values}].
All calls run as the authenticated Odoo user: access rights and record rules apply."""

TOOLS = [
    {
        "name": "list_models",
        "title": "List models",
        "description": "Search the models the current user can read, by technical name or label.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Substring matched against the technical name (e.g. 'sale.order') and the label."},
                "limit": {"type": "integer", "default": 50},
            },
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "describe_model",
        "title": "Describe model",
        "description": "Fields (type, label, relation, selection) and public methods of a model, plus the administrator notes attached to it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Technical model name, e.g. 'res.partner'."},
                "include_fields": {"type": "boolean", "default": True},
                "include_methods": {"type": "boolean", "default": True},
                "include_orm_methods": {"type": "boolean", "default": False, "description": "Also list the generic ORM methods every model inherits."},
            },
            "required": ["model"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "describe_method",
        "title": "Describe method",
        "description": "Signature, parameters, docstring and administrator notes of one public method.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "method": {"type": "string"},
            },
            "required": ["model", "method"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "search_read",
        "title": "Search and read records",
        "description": "Search records with an Odoo domain and return the requested fields.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "domain": {"type": "array", "items": {}, "default": [], "description": "Odoo domain, e.g. [['customer_rank', '>', 0], ['country_id.code', '=', 'TR']]."},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to return; defaults to display_name only."},
                "limit": {"type": "integer", "default": 80},
                "offset": {"type": "integer", "default": 0},
                "order": {"type": "string", "description": "e.g. 'create_date desc'."},
            },
            "required": ["model"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "call_method",
        "title": "Call a model method",
        "description": "Call any public method of a model: create, write, unlink, action_confirm, ... "
                       "Pass record ids in 'ids' for record methods; leave it empty for model-level methods such as create or default_get. "
                       "Recordset results are returned as ids.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "method": {"type": "string"},
                "ids": {"type": "array", "items": {"type": "integer"}, "default": []},
                "args": {"type": "array", "items": {}, "default": [], "description": "Positional arguments after the recordset."},
                "kwargs": {"type": "object", "default": {}},
                "context": {"type": "object", "default": {}, "description": "Extra context keys, e.g. {'lang': 'tr_TR'}."},
            },
            "required": ["model", "method"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": True},
    },
]
TOOLS_BY_NAME = {tool['name']: tool for tool in TOOLS}


class McpInvalidParams(Exception):
    """Raised when tools/call names an unknown tool or omits a required argument."""


def _json_dumps(value):
    """Serialize a tool result; dates become strings and anything unknown falls back to str()."""
    return json.dumps(value, default=json_default, ensure_ascii=False, indent=1)


class McpServer(models.AbstractModel):
    _name = 'mcp.server'
    _description = 'MCP Server'

    # ------------------------------------------------------------------
    # Protocol-facing helpers used by the controller
    # ------------------------------------------------------------------
    def _instructions(self):
        """Server instructions sent at initialize: the static workflow text plus every global note."""
        notes = self.env['mcp.note']._notes_text()
        return INSTRUCTIONS + (f"\n\nNotes from the administrator:\n{notes}" if notes else "")

    def _tool_definitions(self):
        """Tool list advertised by tools/list."""
        return TOOLS

    def _call_tool(self, name, arguments):
        """Validate the arguments, run the tool inside a savepoint and wrap the outcome as an MCP result."""
        tool = TOOLS_BY_NAME.get(name)
        if tool is None:
            raise McpInvalidParams(f"Unknown tool: {name}")
        missing = [k for k in tool['inputSchema'].get('required', []) if k not in arguments]
        if missing:
            raise McpInvalidParams(f"Missing required arguments: {', '.join(missing)}")
        _logger.info("MCP tool %s by uid %s: %s", name, self.env.uid, arguments)
        try:
            with self.env.cr.savepoint():
                result = getattr(self, f"_tool_{name}")(**arguments)
        except Exception as exc:  # noqa: BLE001 - the assistant must see the error text
            _logger.info("MCP tool %s failed: %s", name, exc)
            return {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}
        return {"content": [{"type": "text", "text": _json_dumps(result)}]}

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    def _tool_list_models(self, query=None, limit=50):
        """Models readable by the user whose technical name or label contains the query."""
        domain = ['|', ('model', 'ilike', query), ('name', 'ilike', query)] if query else []
        result = []
        for ir_model in self.env['ir.model'].sudo().search(domain, order='model'):
            if ir_model.model in self.env and self.env[ir_model.model].has_access('read'):
                result.append({'model': ir_model.model, 'name': ir_model.name})
                if len(result) >= limit:
                    break
        return result

    def _tool_describe_model(self, model, include_fields=True, include_methods=True, include_orm_methods=False):
        """Compact fields_get() output, public method signatures and the notes attached to the model."""
        Model = self._model(model)
        Model.check_access('read')
        Note = self.env['mcp.note']
        result = {
            'model': model,
            'name': self.env['ir.model']._get(model).name,
            'notes': Note._notes_text(model),
        }
        if include_fields:
            result['fields'] = {
                name: {k: v for k, v in attrs.items() if v not in (False, None, '', [])}
                for name, attrs in Model.fields_get(attributes=FIELD_ATTRIBUTES).items()
            }
        if include_methods:
            result['methods'] = self._public_methods(Model, include_orm_methods)
            result['method_notes'] = Note._method_notes(model)
        return result

    def _tool_describe_method(self, model, method):
        """api_doc reflection of one public method plus the notes attached to it."""
        Model = self._model(model)
        get_public_method(Model, method)  # raises for private, unknown or unsafe names
        introducing = self._introducing_class(Model, method)
        info = parse_signature(getattr(introducing, method)).as_dict()
        info.update({
            'model': model,
            'method': method,
            'defined_in': introducing._name or 'core',
            'module': introducing._module or 'core',
            'notes': self.env['mcp.note']._notes_text(model, method),
        })
        return info

    def _tool_search_read(self, model, domain=None, fields=None, limit=80, offset=0, order=None):
        """Plain search_read; without an explicit field list only display_name is returned."""
        Model = self._model(model)
        return Model.search_read(domain or [], fields or ['display_name'], offset=offset, limit=limit, order=order)

    def _tool_call_method(self, model, method, ids=None, args=None, kwargs=None, context=None):
        """Generic RPC call with the same semantics as Odoo's /json/2 endpoint."""
        Model = self._model(model)
        kwargs = dict(kwargs or {})
        if context:
            kwargs['context'] = context
        args = list(args or [])
        if not getattr(get_public_method(Model, method), '_api_model', False):
            args.insert(0, list(ids or []))
        return call_kw(Model, method, args, kwargs)

    # ------------------------------------------------------------------
    # Reflection helpers
    # ------------------------------------------------------------------
    def _model(self, model):
        """Return the model recordset or raise a readable error for the assistant."""
        if model not in self.env:
            raise UserError(self.env._("Unknown model %s. Use list_models to find the technical name.", model))
        return self.env[model]

    @staticmethod
    def _introducing_class(Model, method):
        """The class that first defines the method in the MRO, as api_doc does for grouping."""
        return next(cls for cls in reversed(type(Model).mro()) if hasattr(cls, method))

    def _public_methods(self, Model, include_orm_methods):
        """Map public method names to one-line signatures; BaseModel methods are skipped unless asked."""
        cls = type(Model)
        result = {}
        for name in dir(cls):
            if not is_public_method(Model, name):
                continue
            introducing = self._introducing_class(Model, name)
            if not include_orm_methods and not getattr(introducing, '_name', None):
                continue
            result[name] = self._signature(getattr(cls, name))
        return result

    @staticmethod
    def _signature(method):
        """Render '(arg1, arg2=default)' without self/cls; '(...)' when introspection is impossible."""
        try:
            params = inspect.signature(method).parameters.values()
        except (TypeError, ValueError):
            return '(...)'
        return '(' + ', '.join(str(p) for p in params if p.name not in ('self', 'cls')) + ')'
