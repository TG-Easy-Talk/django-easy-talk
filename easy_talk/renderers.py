from django.forms.renderers import TemplatesSetting


class FormComValidacaoRenderer(TemplatesSetting):

    def render(self, template_name, context, renderer=None):
        form = context.get('form', None)
        fields = context.get('fields', None)

        if form:
            form.label_suffix = ''

        if fields:
            for bound_field, errors in fields:
                # Adicionar um placeholder vazio caso já não haja algum para o form-floating do Bootstrap funcionar
                bound_field.field.widget.attrs.setdefault('placeholder', '')

                # Adicionar classes de validação do Bootstrap
                classes = [bound_field.field.widget.attrs.get('class', '')]

                if bound_field.errors:
                    classes.append('is-invalid')

                elif form.is_bound and bound_field.field.widget.input_type not in ['email', 'password']:
                    classes.append('is-valid')

                bound_field.field.widget.attrs.setdefault('class', ' '.join(classes))

        return super().render(template_name, context, renderer)
