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
# Upper bound of one tool result when the 'bigmcp.max_result_tokens' parameter is not set.
DEFAULT_MAX_RESULT_TOKENS = 25000
# There is no tokenizer on the server: tokens are estimated, on the safe side for JSON.
CHARS_PER_TOKEN = 3

INSTRUCTIONS = """You are connected to an Odoo ERP through its ORM.
Workflow: list_models -> describe_model -> (describe_method) -> search_read / call_method.
Every model supports the standard ORM methods even when describe_model does not list them:
search_read, search_count, read, create, write, unlink, name_search, default_get, copy,
formatted_read_group, fields_get. Domains are lists of [field, operator, value] triplets combined
with prefix operators '&', '|', '!'. Relational fields are written as ids; x2many fields
use command tuples such as [4, id], [3, id], [6, 0, [ids]], [0, 0, {values}].
For counts, totals and rankings never add up search_read rows, they stop at 'limit': call
search_count, or formatted_read_group with kwargs such as {"domain": [...],
"groupby": ["partner_id", "date_order:month"], "aggregates": ["amount_total:sum", "__count"]}.
All calls run as the authenticated Odoo user: access rights and record rules apply."""

TOOLS = [
    {
        "name": "list_models",
        "title": "List models",
        "description": "Every model the current user can read, grouped by the module that defines it: {module: {model: label}}. "
                       "All matches are returned, there is no limit: narrow the list with 'query' and/or 'module'. "
                       "When a business term finds nothing, try another word or list the whole module "
                       "(e.g. invoices are 'account.move', labelled 'Journal Entry').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Substring matched against the technical name (e.g. 'sale.order') and the label."},
                "module": {"type": "string", "description": "Technical module name as shown in the result keys, e.g. 'sale': only the models that module defines."},
            },
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "describe_model",
        "title": "Describe model",
        "description": "Fields (type, label, relation, selection) and public methods of a model, plus the administrator notes attached to it. "
                       "Without 'fields' every field is listed without its help text. "
                       "Fields marked searchable=false are computed on the fly: they can be read but not filtered, sorted or grouped on.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Technical model name, e.g. 'res.partner'."},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Only describe these fields, help text included."},
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
        "description": "Search records with an Odoo domain and return {total, records}: 'total' counts every record matching the domain, "
                       "'records' holds one page of them with the requested fields (see 'limit' and 'offset'). "
                       "Archived records are left out. Binary fields come back as their size, not their content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "domain": {"type": "array", "items": {}, "default": [], "description": "Odoo domain, e.g. [['customer_rank', '>', 0], ['country_id.code', '=', 'TR']]."},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to return; defaults to display_name only."},
                "limit": {"type": "integer", "default": 80},
                "offset": {"type": "integer", "default": 0},
                "order": {"type": "string", "description": "e.g. 'create_date desc'."},
                "context": {"type": "object", "default": {}, "description": "Extra context keys, e.g. {'lang': 'tr_TR'}. Pass {'active_test': false} "
                                                                            "to include archived records, only when the user explicitly asks for them."},
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
                       "Recordset results are returned as ids. Read-only methods such as read return binary fields as their size; "
                       "pass context {'bin_size': false} to get the base64 content.",
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
    """Serialize a tool result without whitespace; dates become strings and anything unknown falls back to str()."""
    return json.dumps(value, default=json_default, ensure_ascii=False, separators=(',', ':'))


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
        return {"content": [{"type": "text", "text": self._truncate(_json_dumps(result))}]}

    def _truncate(self, text):
        """Cut a tool result above the configured token limit and tell the assistant how to narrow the request."""
        # Settings drops the parameter when the field is emptied or set to 0: the default applies again.
        max_tokens = int(self.env['ir.config_parameter'].sudo().get_param(
            'bigmcp.max_result_tokens', DEFAULT_MAX_RESULT_TOKENS))
        max_chars = max_tokens * CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        return (f"{text[:max_chars]}\n[Truncated: the result is about {len(text) // CHARS_PER_TOKEN} tokens, "
                f"only the first {max_tokens} are shown. The call itself completed, do not repeat it as is: "
                "ask for fewer fields or fewer records.]")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    def _tool_list_models(self, query=None, module=None):
        """Every model readable by the user that matches the query, as {defining module: {model: label}}.

        Models created from the interface belong to no module and are grouped under 'custom'.
        """
        domain = ['|', ('model', 'ilike', query), ('name', 'ilike', query)] if query else []
        result = {}
        for ir_model in self.env['ir.model'].sudo().search(domain, order='model'):
            if ir_model.model not in self.env:
                continue
            Model = self.env[ir_model.model]
            defining_module = Model._original_module or 'custom'
            if module and module != defining_module:
                continue
            if Model.has_access('read'):
                result.setdefault(defining_module, {})[ir_model.model] = ir_model.name
        return result

    def _tool_describe_model(self, model, fields=None, include_fields=True, include_methods=True, include_orm_methods=False):
        """Field descriptions, public method signatures and the notes attached to the model."""
        Model = self._model(model)
        Model.check_access('read')
        Note = self.env['mcp.note']
        result = {
            'model': model,
            'name': self.env['ir.model']._get(model).name,
            'notes': Note._notes_text(model),
        }
        if include_fields:
            result['fields'] = self._describe_fields(Model, fields)
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

    def _tool_search_read(self, model, domain=None, fields=None, limit=80, offset=0, order=None, context=None):
        """One page of search_read with binaries as sizes, next to the number of records matching the domain.

        The total lets the assistant tell a complete result from a page cut at the limit. Without an
        explicit field list only display_name is returned.
        """
        Model = self._model(model).with_context(**{'bin_size': True, **(context or {})})
        domain = domain or []
        return {
            'total': Model.search_count(domain),
            'records': Model.search_read(domain, fields or ['display_name'], offset=offset, limit=limit, order=order),
        }

    def _tool_call_method(self, model, method, ids=None, args=None, kwargs=None, context=None):
        """Generic RPC call with the same semantics as Odoo's /json/2 endpoint."""
        Model = self._model(model)
        kwargs = dict(kwargs or {})
        context = dict(context or {})
        if self._is_readonly_method(Model, method):
            context.setdefault('bin_size', True)
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

    def _describe_fields(self, Model, names):
        """fields_get() without falsy values; the help text is only sent for fields requested by name.

        'searchable' works the other way round: it is only sent when False, to flag the
        non-stored fields without a search method that a domain cannot use.
        """
        attributes = FIELD_ATTRIBUTES if names else [a for a in FIELD_ATTRIBUTES if a != 'help']
        result = {}
        for name, attrs in Model.fields_get(allfields=names, attributes=[*attributes, 'searchable']).items():
            searchable = attrs.pop('searchable')
            result[name] = {k: v for k, v in attrs.items() if v not in (False, None, '', [])}
            if not searchable:
                result[name]['searchable'] = False
        return result

    @staticmethod
    def _is_readonly_method(Model, method):
        """Whether the method is flagged @api.readonly somewhere in the MRO, as /web/dataset/call_kw checks it."""
        for cls in type(Model).mro():
            func = getattr(cls, method, None)
            if func is not None and hasattr(func, '_readonly'):
                return func._readonly
        return False

    @staticmethod
    def _introducing_class(Model, method):
        """The class that first defines the method in the MRO, as api_doc does for grouping."""
        return next(cls for cls in reversed(type(Model).mro()) if hasattr(cls, method))

    def _public_methods(self, Model, include_orm_methods):
        """Map public method names to one-line signatures; generic methods are skipped unless asked.

        Generic means present on every model: defined by BaseModel itself or added to it by a module
        through the 'base' model (web_read, get_views...).
        """
        cls = type(Model)
        result = {}
        for name in dir(cls):
            if not is_public_method(Model, name):
                continue
            introducing = self._introducing_class(Model, name)
            if not include_orm_methods and getattr(introducing, '_name', None) in (None, 'base'):
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
