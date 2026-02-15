from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Job
from .forms import JobForm
from accounts.models import CustomUser, RecruiterProfile

# Helper to ensure only recruiters access certain views
def recruiter_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role != CustomUser.Role.RECRUITER:
            return redirect('home') # or forbidden page
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
def admin_dashboard(request):
    return render(request, "jobboard/AdminDashboard.html")

@login_required
def jobseeker_dashboard(request):
    jobs = Job.objects.filter(is_active=True).order_by('-created_at')
    return render(request, "jobboard/JobSeekerDashboard.html", {'jobs': jobs})

@login_required
def jobseeker_map_viewer(request):
    return render(request, "jobboard/JobSeekerMapViewer.html")

@login_required
def jobseeker_search(request):
    return render(request, "jobboard/JobSeekerSearch.html")

@login_required
@recruiter_required
def recruiter_dashboard(request):
    jobs = Job.objects.filter(recruiter=request.user).order_by('-created_at')
    return render(request, "jobboard/RecruiterDashboard.html", {'jobs': jobs})

@login_required
@recruiter_required
def job_create(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.recruiter = request.user
            # Get company name from profile
            try:
                profile = RecruiterProfile.objects.get(user=request.user)
                job.company_name = profile.company_name
            except RecruiterProfile.DoesNotExist:
                job.company_name = "Unknown Company"
            
            job.save()
            messages.success(request, 'Job posted successfully!')
            return redirect('recruiter_dashboard')
    else:
        form = JobForm()
    return render(request, 'jobboard/job_form.html', {'form': form, 'title': 'Post a New Job'})

@login_required
@recruiter_required
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk, recruiter=request.user)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job updated successfully!')
            return redirect('recruiter_dashboard')
    else:
        form = JobForm(instance=job)
    return render(request, 'jobboard/job_form.html', {'form': form, 'title': 'Edit Job'})

@login_required
@recruiter_required
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk, recruiter=request.user)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job deleted successfully!')
        return redirect('recruiter_dashboard')
    return render(request, 'jobboard/job_confirm_delete.html', {'job': job})

@login_required
def recruiter_kanban(request):
    return render(request, "jobboard/RecruiterKanban.html")

@login_required
def recruiter_messaging(request):
    return render(request, "jobboard/RecruiterMessaging.html")

@login_required
def recruiter_talent_search(request):
    return render(request, "jobboard/RecruiterTalentSearch.html")
