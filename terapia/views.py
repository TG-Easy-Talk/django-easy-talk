from django.shortcuts import render
from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = "home.html"

class ConsultaView(TemplateView):
    template_name = "consulta.html"

class PerfilView(TemplateView):
    template_name = "perfil.html"

class PesquisaView(TemplateView):
    template_name = "pesquisa.html"