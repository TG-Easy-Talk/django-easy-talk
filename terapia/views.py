from django.shortcuts import render
from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = "home.html"

def perfil(request):
    return render(request, "perfil.html")

class ConsultaView(TemplateView):
    template_name = "consulta.html"