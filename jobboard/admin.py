from django.contrib import admin
from .models import Job, Application, ScreeningQuestion, ApplicationAnswer, Interview, Message, SavedSearch, SavedCandidate, Notification

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


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "content", "timestamp", "is_read")
    list_filter = ("is_read",)
    search_fields = ("sender__username", "receiver__username", "content")


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ("recruiter", "name", "query", "location", "skill", "created_at")


@admin.register(SavedCandidate)
class SavedCandidateAdmin(admin.ModelAdmin):
    list_display = ("recruiter", "candidate", "created_at")
    search_fields = ("recruiter__username", "candidate__username", "candidate__email")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_message", "is_read", "created_at")
    list_filter = ("is_read",)


admin.site.register(ScreeningQuestion)
admin.site.register(ApplicationAnswer)
admin.site.register(Interview)
