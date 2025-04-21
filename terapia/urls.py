from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('consulta/', views.ConsultaView.as_view(), name='consulta'),
    path('perfil/', views.perfil, name='perfil'),
]
