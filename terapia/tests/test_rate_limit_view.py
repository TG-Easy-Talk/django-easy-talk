from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings

class RateLimitViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')

    def test_login_rate_limit_page(self):
        # LOGIN_ATTEMPTS is 5 by default in settings.py
        # We need to exceed it.
        
        # We need to make sure we are using the same IP or whatever key is used.
        # The view uses key='ip'. Client() uses 127.0.0.1 by default.

        # Attempt login 5 times (allowed)
        for _ in range(5):
            response = self.client.post(self.login_url, {'username': 'wrong', 'password': 'password'})
            # Should be 200 (form error) or 302 (success)
            # Since credentials are wrong, it returns 200 with form errors.
            self.assertNotEqual(response.status_code, 429)

        # 6th attempt should be blocked
        response = self.client.post(self.login_url, {'username': 'wrong', 'password': 'password'})
        
        self.assertEqual(response.status_code, 429)
        self.assertTemplateUsed(response, 'conta/rate_limit.html')
        self.assertContains(response, "Muitas tentativas", status_code=429)
        self.assertContains(response, "Identificamos um número alto de solicitações recentes", status_code=429)
