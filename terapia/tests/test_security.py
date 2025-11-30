from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings

class SecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_login_rate_limit(self):
        url = reverse('login')
        # Limit is 5/h. 5 requests should pass, 6th should fail.
        for i in range(5):
            response = self.client.post(url, {'username': 'test', 'password': 'password'})
            self.assertNotEqual(response.status_code, 429, f"Request {i+1} blocked prematurely")

        response = self.client.post(url, {'username': 'test', 'password': 'password'})
        self.assertEqual(response.status_code, 429, "6th login request should be blocked")

    def test_registration_rate_limit(self):
        # Limit is 3/h.
        urls = [reverse('cadastro_paciente'), reverse('cadastro_psicologo')]
        
        for url in urls:
            cache.clear() # Clear cache between testing different endpoints if they share limits or just to be clean
            for i in range(3):
                response = self.client.post(url, {}) # Empty post is enough to trigger rate limit check
                self.assertNotEqual(response.status_code, 429, f"Request {i+1} to {url} blocked prematurely")

            response = self.client.post(url, {})
            self.assertEqual(response.status_code, 429, f"4th request to {url} should be blocked")
