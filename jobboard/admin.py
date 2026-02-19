from django.contrib import admin
from .models import Job, Application, ScreeningQuestion, ApplicationAnswer, Interview

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company_name", "recruiter", "is_active", "is_approved", "created_at")
    list_filter = ("is_active", "is_approved", "job_type")
    search_fields = ("title", "company_name", "location", "skills")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "applicant", "status", "applied_at")
    list_filter = ("status",)
    search_fields = ("job__title", "applicant__username", "applicant__email")


admin.site.register(ScreeningQuestion)
admin.site.register(ApplicationAnswer)
admin.site.register(Interview)
