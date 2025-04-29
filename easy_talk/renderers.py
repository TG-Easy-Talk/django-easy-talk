from django.forms.renderers import TemplatesSetting
from django.forms.widgets import Input


class CustomFormRenderer(TemplatesSetting):
    form_template_name = 'custom_form.html'
    field_template_name = 'custom_field.html'

    def render(self, template_name, context, renderer=None):
        form = context.get('form', None)
        fields = context.get('fields', None)
        
        if form and hasattr(form, 'label_suffix'):
            # Remover o sufixo de label padrão do Django (que é um dois-pontos ":")
            form.label_suffix = ''

        if fields:
            for bound_field, errors in fields:
                # Adicionar um placeholder vazio padrão para o form-floating do Bootstrap funcionar
                bound_field.field.widget.attrs.setdefault('placeholder', '')

                # Adicionar classes de CSS aos campos dependendo do tipo de widget
                if isinstance(bound_field.field.widget, Input):
                    bound_field.field.widget.attrs.setdefault('class', 'form-control border border-secondary-subtle')

        return super().render(template_name, context, renderer)