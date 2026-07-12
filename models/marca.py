from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Marca(models.Model):
    _name = 'caa.marca'
    _description = 'Marcas'

    name = fields.Char(string="Marca",required=True)
    caa_corr = fields.Char(string="Prefijo para correlativo", required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('caa_corr'):
                vals['caa_corr'] = vals['caa_corr'].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('caa_corr'):
            vals['caa_corr'] = vals['caa_corr'].strip().upper()
        return super().write(vals)

    @api.constrains('caa_corr')
    def _check_caa_corr_unico(self):
        for record in self:
            if not record.caa_corr:
                continue
            duplicado = self.search([
                ('caa_corr', '=', record.caa_corr),
                ('id', '!=', record.id),
            ], limit=1)
            if duplicado:
                raise ValidationError(
                    "El prefijo '%s' ya lo usa la marca '%s'. Cada marca debe "
                    "tener un prefijo de correlativo unico para evitar que se "
                    "dupliquen las referencias de producto." % (
                        record.caa_corr, duplicado.name)
                )
