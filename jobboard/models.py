from django.db import models
from django.conf import settings

class Job(models.Model):
    JOB_TYPES = (
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERNSHIP', 'Internship'),
    )

    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posted_jobs')
    title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField()
    job_type = models.CharField(max_length=50, choices=JOB_TYPES, default='FULL_TIME')
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    skills = models.CharField(max_length=500, blank=True, help_text="Comma-separated list of required skills")
    visa_sponsorship = models.BooleanField(default=False, help_text="Does this job offer visa sponsorship?")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} at {self.company_name}"

class Application(models.Model):
    STATUS_CHOICES = (
        ('APPLIED', 'Applied'),
        ('SCREENING', 'Screening'),
        ('INTERVIEW', 'Interview'),
        ('OFFER', 'Offer'),
        ('HIRED', 'Hired'),
        ('REJECTED', 'Rejected'),
    )

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPLIED')
    cover_letter = models.TextField(blank=True, null=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('job', 'applicant')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.applicant} applied to {self.job}"

class ScreeningQuestion(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='screening_questions')
    question_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text

class ApplicationAnswer(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ScreeningQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()

    def __str__(self):
        return f"Answer to {self.question} by {self.application.applicant}"

class Interview(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conducted_interviews')
    date_time = models.DateTimeField()
    location = models.CharField(max_length=255, default='Remote')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['date_time']

    def __str__(self):
        return f"Interview for {self.application.job.title} with {self.application.applicant} on {self.date_time}"
