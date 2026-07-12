from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import date

class ProductTemplate(models.Model):
    _inherit = "product.template"

    caa_ref = fields.Integer(string="Correlativo Interno", required=True, default=0)
    marca_id = fields.Many2one(comodel_name='caa.marca', string="Marca", required=False)
    caa_serie = fields.Char(string="Serie")
    caa_nota = fields.Char(string="Nota")
    caa_observacion = fields.Char(string="Observacion")
    caa_intercambio = fields.Char(string="Intercambio")

    @api.onchange('marca_id')
    def onchange_marca_id(self):
        self.asigna_correlativo()

    @api.onchange('categ_id')
    def onchange_categ_id(self):
        self.asigna_correlativo()

    def asigna_correlativo(self):
        for record in self:
            if record.marca_id.caa_corr and record.categ_id.caa_corr:
                domain = [
                    ('marca_id', '=', record.marca_id.id),
                    ('categ_id', '=', record.categ_id.id),
                ]
                origen_id = record._origin.id
                if origen_id:
                    domain.append(('id', '!=', origen_id))
                siguiente = self.env['product.template'].search(
                    domain, order='caa_ref desc', limit=1)
                sig_corr = siguiente.caa_ref + 1 if siguiente else 1

                record.caa_ref = sig_corr
                record.default_code = self._caa_build_default_code(
                    record.categ_id.caa_corr, record.marca_id.caa_corr, sig_corr)
            else:
                # No se fuerza "Sin Asignar" aqui: este onchange corre
                # mientras se llena el formulario (antes de grabar) y ese
                # texto ya existe en cientos de productos, lo que dispara
                # la advertencia nativa de Odoo de "referencia duplicada"
                # en pleno tecleo. Se deja en blanco; "Sin Asignar" solo se
                # asigna al grabar (create/write) y unicamente si el
                # usuario no escribio nada manualmente.
                record.default_code = False

    @api.model
    def _caa_build_default_code(self, categ_corr, marca_corr, correlativo):
        return "%s-%s-%s" % (categ_corr, marca_corr, str(correlativo).rjust(4, '0'))

    @api.model_create_multi
    def create(self, vals_list):
        self._caa_asigna_correlativos_batch(vals_list)
        return super().create(vals_list)

    def _caa_asigna_correlativos_batch(self, vals_list):
        """Calcula caa_ref/default_code para altas masivas (creacion normal e
        importacion nativa de Odoo), que no disparan los onchange de la UI.
        Solo asigna cuando el producto trae marca y categoria con prefijo."""
        marca_corr_cache = {}
        categ_corr_cache = {}
        siguiente_cache = {}

        for vals in vals_list:
            marca_id = vals.get('marca_id')
            categ_id = vals.get('categ_id')
            if not marca_id or not categ_id:
                if not vals.get('default_code'):
                    vals['default_code'] = 'Sin Asignar'
                continue

            if marca_id not in marca_corr_cache:
                marca_corr_cache[marca_id] = self.env['caa.marca'].browse(marca_id).caa_corr
            if categ_id not in categ_corr_cache:
                categ_corr_cache[categ_id] = self.env['product.category'].browse(categ_id).caa_corr

            marca_corr = marca_corr_cache[marca_id]
            categ_corr = categ_corr_cache[categ_id]
            if not marca_corr or not categ_corr:
                if not vals.get('default_code'):
                    vals['default_code'] = 'Sin Asignar'
                continue

            clave = (categ_id, marca_id)
            if clave not in siguiente_cache:
                ultimo = self.search([
                    ('categ_id', '=', categ_id),
                    ('marca_id', '=', marca_id),
                ], order='caa_ref desc', limit=1)
                siguiente_cache[clave] = ultimo.caa_ref if ultimo else 0

            siguiente_cache[clave] += 1
            vals['caa_ref'] = siguiente_cache[clave]
            vals['default_code'] = self._caa_build_default_code(
                categ_corr, marca_corr, siguiente_cache[clave])

    def write(self, vals):
        if not (vals.get('marca_id') or vals.get('categ_id')):
            return super().write(vals)

        siguiente_cache = {}
        for record in self:
            marca_id = vals.get('marca_id', record.marca_id.id)
            categ_id = vals.get('categ_id', record.categ_id.id)
            record_vals = vals

            if marca_id and categ_id:
                marca_corr = self.env['caa.marca'].browse(marca_id).caa_corr
                categ_corr = self.env['product.category'].browse(categ_id).caa_corr
                if marca_corr and categ_corr:
                    clave = (categ_id, marca_id)
                    if clave not in siguiente_cache:
                        ultimo = self.search([
                            ('categ_id', '=', categ_id),
                            ('marca_id', '=', marca_id),
                            ('id', 'not in', self.ids),
                        ], order='caa_ref desc', limit=1)
                        siguiente_cache[clave] = ultimo.caa_ref if ultimo else 0
                    siguiente_cache[clave] += 1
                    record_vals = dict(vals, caa_ref=siguiente_cache[clave],
                                        default_code=self._caa_build_default_code(
                                            categ_corr, marca_corr, siguiente_cache[clave]))

            super(ProductTemplate, record).write(record_vals)
        return True

    def copy(self, default=None):
        nuevo = super().copy(default=default)
        if nuevo.marca_id and nuevo.categ_id and nuevo.marca_id.caa_corr and nuevo.categ_id.caa_corr:
            ultimo = self.search([
                ('categ_id', '=', nuevo.categ_id.id),
                ('marca_id', '=', nuevo.marca_id.id),
                ('id', '!=', nuevo.id),
            ], order='caa_ref desc', limit=1)
            sig_corr = ultimo.caa_ref + 1 if ultimo else 1
            nuevo.write({
                'caa_ref': sig_corr,
                'default_code': self._caa_build_default_code(
                    nuevo.categ_id.caa_corr, nuevo.marca_id.caa_corr, sig_corr),
            })
        return nuevo
