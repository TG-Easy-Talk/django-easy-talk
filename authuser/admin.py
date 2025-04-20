from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

class UsuarioAdmin(BaseUserAdmin):
    list_display = ('email', 'nome', 'sobrenome', 'is_staff', 'is_active')
    list_filter  = ('is_staff', 'is_active')
    ordering     = ('email',)