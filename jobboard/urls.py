from django.urls import path
from . import views

urlpatterns = [
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/job/<int:pk>/approve/", views.approve_job, name="approve_job"),
    path("admin/export/jobs/", views.export_jobs_csv, name="export_jobs_csv"),
    path("admin/user/<int:pk>/toggle-active/", views.admin_toggle_user_active, name="admin_toggle_user_active"),
    path("admin/user/<int:pk>/change-role/", views.admin_change_user_role, name="admin_change_user_role"),

    path("jobseeker/dashboard/", views.jobseeker_dashboard, name="jobseeker_dashboard"),
    path("jobseeker/map/", views.jobseeker_map_viewer, name="jobseeker_map_viewer"),
    path("jobseeker/map/preferences/commute-radius/", views.update_commute_radius_preference, name="update_commute_radius_preference"),
    path("jobseeker/search/", views.jobseeker_search, name="jobseeker_search"),
    path("job/<int:pk>/", views.job_detail, name="job_detail"),
    path("job/<int:pk>/apply/", views.apply_for_job, name="job_apply"),
    
    # One-click apply routes
    path("job/<int:pk>/one-click-apply/", views.one_click_apply_form, name="one_click_apply_form"),
    path("job/<int:pk>/one-click-apply/submit/", views.one_click_apply_submit, name="one_click_apply_submit"),
    path("application/<int:pk>/confirmation/", views.one_click_apply_confirmation, name="one_click_apply_confirmation"),

    path("recruiter/dashboard/", views.recruiter_dashboard, name="recruiter_dashboard"),
    path("recruiter/job/new/", views.job_create, name="job_create"),
    path("recruiter/job/<int:pk>/edit/", views.job_edit, name="job_edit"),
    path("recruiter/job/<int:pk>/delete/", views.job_delete, name="job_delete"),
    path("recruiter/kanban/", views.recruiter_kanban, name="recruiter_kanban"),
    path("recruiter/application/<int:pk>/", views.recruiter_application_detail, name="recruiter_application_detail"),
    path("recruiter/application/<int:pk>/update-status/", views.update_application_status, name="update_application_status"),
    path("recruiter/applicant-map/", views.recruiter_applicant_map, name="recruiter_applicant_map"),

    # Messaging (Story 13)
    path("messaging/", views.recruiter_messaging, name="messaging"),
    path("messaging/<int:receiver_id>/", views.recruiter_messaging, name="messaging_conversation"),
    path("messaging/send/", views.send_message, name="send_message"),
    # Keep old URL as alias
    path("recruiter/messaging/", views.recruiter_messaging, name="recruiter_messaging"),

    # Email candidates (Story 14)
    path("recruiter/email/<int:user_id>/", views.email_candidate, name="email_candidate"),

    # Saved searches (Story 15)
    path("recruiter/saved-searches/", views.saved_searches, name="saved_searches"),
    path("recruiter/save-search/", views.save_search, name="save_search"),
    path("recruiter/saved-search/<int:pk>/delete/", views.delete_saved_search, name="delete_saved_search"),
    path("recruiter/candidate/<int:user_id>/save/", views.save_candidate, name="save_candidate"),
    path("recruiter/candidate/<int:user_id>/remove/", views.remove_saved_candidate, name="remove_saved_candidate"),

    path("recruiter/talent-search/", views.recruiter_talent_search, name="recruiter_talent_search"),
]
