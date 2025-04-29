from django.forms.renderers import TemplatesSetting
from django.forms.utils import ErrorList
from django.forms.widgets import Input


class CustomErrorList(ErrorList):
    # template_name = 'custom_error_list.html'
    error_class = 'abacaxi'
    

class CustomFormRenderer(TemplatesSetting):
    form_template_name = 'custom_form.html'
    field_template_name = 'custom_field.html'

    def render(self, template_name, context, renderer=None):
        form = context.get('form', None)
        fields = context.get('fields', None)

        if form:
            form.label_suffix = ''
            # form.error_class = CustomErrorList

        if fields:
            for bound_field, errors in fields:
                # Adicionar um placeholder vazio padrão para o form-floating do Bootstrap funcionar
                bound_field.field.widget.attrs.setdefault('placeholder', '')

                # Adicionar classes de CSS aos campos dependendo do tipo de widget
                if isinstance(bound_field.field.widget, Input):
                    if bound_field.errors:
                        bound_field.field.widget.attrs.setdefault('class', 'form-control border is-invalid')
                    else:
                        bound_field.field.widget.attrs.setdefault('class', 'form-control border')

        return super().render(template_name, context, renderer)