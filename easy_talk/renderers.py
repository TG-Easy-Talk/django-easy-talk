from django.forms.renderers import TemplatesSetting
from django.forms import widgets


class CustomFormRenderer(TemplatesSetting):

    def render(self, template_name, context, renderer=None):
        form = context.get('form', None)
        fields = context.get('fields', None)

        if form:
            form.label_suffix = ''

        if fields:
            for bound_field, errors in fields:
                # Adicionar um placeholder vazio padrão para o form-floating do Bootstrap funcionar
                bound_field.field.widget.attrs.setdefault('placeholder', '')

                # Adicionar classes de CSS aos campos dependendo do tipo de widget
                if isinstance(bound_field.field.widget, widgets.Input):

                    classes = 'form-control'

                    if bound_field.errors:
                        classes += ' is-invalid'
                    elif form.is_bound and bound_field.field.widget.input_type not in ['email', 'password']:
                        classes += ' is-valid'

                    bound_field.field.widget.attrs.setdefault('class', classes)

                elif isinstance(bound_field.field.widget, widgets.Select):
                    classes = 'form-select'

                    bound_field.field.widget.attrs.setdefault('class', classes)

        return super().render(template_name, context, renderer)