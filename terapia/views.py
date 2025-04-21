from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.contrib.auth import get_user_model
from .models import Paciente, Psicologo
from .forms import PacienteSignUpForm, PsicologoSignUpForm  # Import corrigido
from django.contrib.auth import login
from django.views.generic import FormView  # ← importe FormView aqui :contentReference[oaicite:1]{index=1}
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class PacienteSignUpView(FormView):
    template_name = 'registration/signup.html'
    form_class = PacienteSignUpForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class PsicologoSignUpView(FormView):
    template_name = 'registration/signup.html'
    form_class = PsicologoSignUpForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


def login_view(request):
    # instancia o form, vinculado ao POST se houver
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        # se válido, loga o usuário
        login(request, form.get_user())
        return redirect('home')

    # renderiza sempre com o 'form' no contexto
    return render(request, 'registration/login.html', {
        'form': form
    })


def home(request):
    return render(request, 'base.html')
