# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class McpNote(models.Model):
    """Administrator documentation shown to MCP clients.

    Scope is derived from the filled fields: no model means a global note sent
    with the server instructions, a model alone documents that model, a model
    plus a method documents that single method.
    """
    _name = 'mcp.note'
    _description = 'MCP Note'
    _order = 'sequence, id'

    name = fields.Char(string='Title', required=True)
    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(
        'ir.model', string='Model', ondelete='cascade',
        help="Leave empty for a global note sent to every client at connection time.")
    model_name = fields.Char(related='model_id.model', store=True)
    method = fields.Char(help="Optional: attach the note to one public method of the model.")
    content = fields.Text(required=True)

    @api.constrains('model_id', 'method')
    def _check_method_has_model(self):
        """A method note only makes sense on a model."""
        for note in self:
            if note.method and not note.model_id:
                raise ValidationError(self.env._("A method note needs a model."))

    def _notes_text(self, model=None, method=None):
        """Join the notes of one scope (global, model or method) into a bullet list; empty string if none."""
        notes = self.search([('model_name', '=', model or False), ('method', '=', method or False)])
        return "\n".join(f"- {note.name}: {note.content}" for note in notes)

    def _method_notes(self, model):
        """Method-level notes of a model as {method: text}, so describe_model can point at them."""
        result = {}
        for note in self.search([('model_name', '=', model), ('method', '!=', False)]):
            result.setdefault(note.method, []).append(f"- {note.name}: {note.content}")
        return {method: "\n".join(lines) for method, lines in result.items()}
