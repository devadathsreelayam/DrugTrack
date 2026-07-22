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


class RoleAccessTests(TestCase):
    def test_admin_user_is_redirected_to_admin_dashboard_from_patient_pages(self):
        admin = User.objects.create_user(username='adminuser', password='StrongPass123!', user_type='admin')
        admin.is_staff = True
        admin.save()
        self.client.force_login(admin)

        response = self.client.get(reverse('dashboard'), follow=True)

        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_home_redirects_admin_to_admin_dashboard(self):
        admin = User.objects.create_user(username='homeadmin', password='StrongPass123!', user_type='admin')
        admin.is_staff = True
        admin.save()
        self.client.force_login(admin)

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('admin_dashboard'))
