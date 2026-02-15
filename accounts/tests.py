from django.test import TestCase, Client
from django.urls import reverse
from .models import CustomUser, JobSeekerProfile, RecruiterProfile

class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('signup')
        self.login_url = reverse('login')
        self.home_url = reverse('home')

    def test_signup_page_status_code(self):
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/signup.html')

    def test_login_page_status_code(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_signup_creates_jobseeker(self):
        data = {
            'username': 'testseeker',
            'email': 'seeker@example.com',
            'first_name': 'Test',
            'last_name': 'Seeker',
            'role': 'JOBSEEKER',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
        }
        response = self.client.post(self.signup_url, data, follow=True)
        
        # Expect redirect to home
        self.assertRedirects(response, self.home_url)
        
        # Check user created
        self.assertTrue(CustomUser.objects.filter(username='testseeker').exists())
        user = CustomUser.objects.get(username='testseeker')
        self.assertEqual(user.role, 'JOBSEEKER')
        
        # Check profile created
        self.assertTrue(JobSeekerProfile.objects.filter(user=user).exists())
        self.assertFalse(RecruiterProfile.objects.filter(user=user).exists())

    def test_signup_creates_recruiter(self):
        data = {
            'username': 'testrecruiter',
            'email': 'recruiter@example.com',
            'first_name': 'Test',
            'last_name': 'Recruiter',
            'role': 'RECRUITER',
            'company_name': 'TechCorp',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
        }
        response = self.client.post(self.signup_url, data, follow=True)
        self.assertRedirects(response, self.home_url)
        
        user = CustomUser.objects.get(username='testrecruiter')
        self.assertEqual(user.role, 'RECRUITER')
        self.assertTrue(RecruiterProfile.objects.filter(user=user).exists())
        profile = RecruiterProfile.objects.get(user=user)
        self.assertEqual(profile.company_name, 'TechCorp')

