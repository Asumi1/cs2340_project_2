from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Can remove @login_required if public access desired.
# For dashboards, leaving it is usually correct.

@login_required
def admin_dashboard(request):
    return render(request, "jobboard/AdminDashboard.html")

@login_required
def jobseeker_dashboard(request):
    return render(request, "jobboard/JobSeekerDashboard.html")

@login_required
def jobseeker_map_viewer(request):
    return render(request, "jobboard/JobSeekerMapViewer.html")

@login_required
def jobseeker_search(request):
    return render(request, "jobboard/JobSeekerSearch.html")

@login_required
def recruiter_dashboard(request):
    return render(request, "jobboard/RecruiterDashboard.html")

@login_required
def recruiter_kanban(request):
    return render(request, "jobboard/RecruiterKanban.html")

@login_required
def recruiter_messaging(request):
    return render(request, "jobboard/RecruiterMessaging.html")

@login_required
def recruiter_talent_search(request):
    return render(request, "jobboard/RecruiterTalentSearch.html")
