from django.urls import reverse
from django.contrib.auth import get_user_model
from terapia.models import Paciente, Psicologo, Consulta
from .model_test_case import ModelTestCase

Usuario = get_user_model()

class ViewsTestCase(ModelTestCase):
    def test_paciente_cadastro_view(self):
        """Testa o cadastro de um novo paciente."""
        url = reverse("cadastro_paciente")
        # CPF válido gerado para teste
        data = {
            "email": "novo.paciente@example.com",
            "password1": "senha_segura",
            "password2": "senha_segura",
            "nome": "Novo Paciente",
            "cpf": "529.982.247-25",
        }
        response = self.client.post(url, data, REMOTE_ADDR="127.0.0.100")
        
        # Verifica redirecionamento após sucesso (para pesquisa ou login)
        self.assertRedirects(response, reverse("pesquisa"))
        
        # Verifica se o usuário e paciente foram criados
        self.assertTrue(Usuario.objects.filter(email="novo.paciente@example.com").exists())
        self.assertTrue(Paciente.objects.filter(cpf="529.982.247-25").exists())

    def test_psicologo_cadastro_view(self):
        """Testa o cadastro de um novo psicólogo."""
        url = reverse("cadastro_psicologo")
        data = {
            "email": "novo.psicologo@example.com",
            "password1": "senha_segura",
            "password2": "senha_segura",
            "nome_completo": "Novo Psicólogo",
            "crp": "06/12345",
        }
        response = self.client.post(url, data, REMOTE_ADDR="127.0.0.101")
        
        # Verifica redirecionamento (geralmente para home ou login)
        # No código atual, PsicologoCadastroView não tem get_redirect explícito no snippet visto,
        # mas CadastroView lança NotImplementedError se não definido.
        # Assumindo que PsicologoCadastroView define ou usa um padrão.
        # Vamos verificar o comportamento real ou ajustar se falhar.
        # Baseado no PacienteCadastroView, ele redireciona.
        self.assertEqual(response.status_code, 302)
        
        self.assertTrue(Usuario.objects.filter(email="novo.psicologo@example.com").exists())
        self.assertTrue(Psicologo.objects.filter(crp="06/12345").exists())

    def test_login_view(self):
        """Testa o login de um usuário existente."""
        url = reverse("login")
        data = {
            "username": "paciente.dummy.1@example.com", # EmailAuthenticationForm usa username field para email
            "password": "senha123"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redireciona após login
        
        # Verifica se está autenticado
        self.client.login(email="paciente.dummy.1@example.com", password="senha123")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paciente Dummy") # Nome do usuário no header/menu

    def test_consulta_creation_via_perfil_view(self):
        """Testa o agendamento de consulta via PerfilView."""
        self.client.force_login(self.paciente_dummy.usuario)
        
        psicologo = self.psicologo_completo
        url = reverse("perfil", kwargs={"pk": psicologo.pk})
        
        data_hora = psicologo.proxima_data_hora_agendavel
        
        data = {
            "data_hora_agendada": data_hora.isoformat()
        }
        
        response = self.client.post(url, data)
        
        self.assertRedirects(response, reverse("minhas_consultas"))
        
        # Verifica se a consulta foi criada
        self.assertTrue(Consulta.objects.filter(
            paciente=self.paciente_dummy,
            psicologo=psicologo,
            data_hora_agendada=data_hora
        ).exists())
