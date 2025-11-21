from django.forms.renderers import TemplatesSetting
from django.forms import widgets
from django import forms


class CustomFormRenderer(TemplatesSetting):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def get_widget_classes(self, widget):
        return [widget.attrs.get('class', '')]
    

    def update_widget_classes(self, widget, classes):
        widget.attrs.update({'class': ' '.join(classes)})


    def render(self, template_name, context, renderer=None):
        form = context.get('form')
        fields = context.get('fields')

        if form:
            form.label_suffix = ''

        if fields:
            for bound_field, errors in fields:
                # Adicionar um placeholder vazio caso já não haja algum para o form-floating do Bootstrap funcionar
                bound_field.field.widget.attrs.setdefault('placeholder', '')

                # Adicionar classes do Bootstrap dependendo do tipo de widget
                classes = self.get_widget_classes(bound_field.field.widget)

                if isinstance(bound_field.field.widget, widgets.Input) \
                or isinstance(bound_field.field.widget, widgets.Textarea):
                    classes.append('form-control')

                elif isinstance(bound_field.field.widget, widgets.Select):
                    classes.append('form-select')

                self.update_widget_classes(bound_field.field.widget, classes)

        return super().render(template_name, context, renderer)


class FormComValidacaoRenderer(CustomFormRenderer):
    def render(self, template_name, context, renderer=None):
        form = context.get('form')
        fields = context.get('fields')

        if fields:
            for bound_field, errors in fields:
                classes = self.get_widget_classes(bound_field.field.widget)

                # Adicionar classes de validação do Bootstrap
                if bound_field.errors:
                    classes.append('is-invalid')

                # elif form.is_bound and bound_field.html_name not in ['username', 'password', 'password1', 'password2']:
                #     classes.append('is-valid')

                self.update_widget_classes(bound_field.field.widget, classes)

        return super().render(template_name, context, renderer)
    

class FormDeFiltrosRenderer(CustomFormRenderer):
    def render(self, template_name, context, renderer=None):
        fields = context.get('fields')

        if fields:
            for bound_field, errors in fields:
                classes = self.get_widget_classes(bound_field.field.widget)

                # Remover o focus ring dos inputs no filtro para melhorar a estética
                if isinstance(bound_field.field.widget, widgets.Input):
                    classes.append('shadow-none')

                # Adicionar o label do próprio campo como empty_label para os ModelChoiceFields
                # Em vez de aparecer "-------" como opção selecionada, aparece a label do campo
                elif isinstance(bound_field.field, forms.ModelChoiceField):
                    bound_field.field.empty_label = bound_field.field.label

                self.update_widget_classes(bound_field.field.widget, classes)

        return super().render(template_name, context, renderer)
