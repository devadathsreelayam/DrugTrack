from django.test import TestCase
from django.urls import reverse

from .models import User


class SignupStage3Tests(TestCase):
    def test_stage3_allows_blank_optional_health_details(self):
        user = User.objects.create_user(username='testuser', password='StrongPass123!')
        self.client.force_login(user)

        response = self.client.post(
            reverse('signup_stage3'),
            {'bp': '', 'cholesterol': '', 'na_to_k': ''},
            follow=True,
        )

        self.assertRedirects(response, reverse('signup_stage4'))
        self.assertFalse(hasattr(user, 'health_profile'))
