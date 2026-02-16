from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        RECRUITER = "RECRUITER", "Recruiter"
        JOBSEEKER = "JOBSEEKER", "Job seeker"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.JOBSEEKER)

    def __str__(self):
        return self.username

class RecruiterProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)

    def clean(self):
        if hasattr(self.user, "jobseekerprofile"):
            raise ValidationError("User already has a JobSeekerProfile.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} (Recruiter)"

class JobSeekerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    major = models.CharField(max_length=120, blank=True)
    headline = models.CharField(max_length=255, blank=True, help_text="A short professional headline")
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True, help_text="Current city/region")
    skills = models.TextField(blank=True, help_text="Comma-separated skills")
    education = models.TextField(blank=True, help_text="Education details")
    work_experience = models.TextField(blank=True, help_text="Work experience details")
    linkedin_url = models.URLField(max_length=200, blank=True)
    portfolio_url = models.URLField(max_length=200, blank=True)
    resume_file = models.FileField(upload_to='resumes/', blank=True, null=True)
    
    # Privacy Settings
    is_resume_public = models.BooleanField(default=True, help_text="Allow recruiters to see your resume")

    def clean(self):
        if hasattr(self.user, "recruiterprofile"):
            raise ValidationError("User already has a RecruiterProfile.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} (Job Seeker)"