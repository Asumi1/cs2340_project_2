from django.urls import path
from . import views

urlpatterns = [
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    path("jobseeker/dashboard/", views.jobseeker_dashboard, name="jobseeker_dashboard"),
    path("jobseeker/map/", views.jobseeker_map_viewer, name="jobseeker_map_viewer"),
    path("jobseeker/search/", views.jobseeker_search, name="jobseeker_search"),

    path("recruiter/dashboard/", views.recruiter_dashboard, name="recruiter_dashboard"),
    path("recruiter/job/new/", views.job_create, name="job_create"),
    path("recruiter/job/<int:pk>/edit/", views.job_edit, name="job_edit"),
    path("recruiter/job/<int:pk>/delete/", views.job_delete, name="job_delete"),
    path("recruiter/kanban/", views.recruiter_kanban, name="recruiter_kanban"),
    path("recruiter/messaging/", views.recruiter_messaging, name="recruiter_messaging"),
    path("recruiter/talent-search/", views.recruiter_talent_search, name="recruiter_talent_search"),
]
