from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Job, Application, Interview
from .forms import JobForm
from accounts.models import CustomUser, RecruiterProfile, JobSeekerProfile
from django.db.models import Q
from django.utils import timezone

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
    
    # Stats for dashboard
    total_applicants = Application.objects.filter(job__recruiter=request.user).count()
    interviews_count = Application.objects.filter(job__recruiter=request.user, status='INTERVIEW').count()
    
    # Pending tasks (Applications needing review)
    pending_applications = Application.objects.filter(
        job__recruiter=request.user, 
        status='APPLIED'
    ).order_by('applied_at')[:5]

    # Upcoming Interviews (Today)
    today = timezone.now().date()
    # Filter strictly for today for the "Today's Schedule" section
    todays_interviews = Interview.objects.filter(
        recruiter=request.user, 
        date_time__date=today
    ).order_by('date_time')

    context = {
        'jobs': jobs,
        'total_applicants': total_applicants,
        'interviews_count': interviews_count,
        'pending_applications': pending_applications,
        'todays_interviews': todays_interviews,
        'today': today,
    }
    return render(request, "jobboard/RecruiterDashboard.html", context)

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
@recruiter_required
def recruiter_talent_search(request):
    query = request.GET.get('q', '')
    profiles = JobSeekerProfile.objects.all()

    if query:
        profiles = profiles.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(skills__icontains=query) |
            Q(major__icontains=query)
        )

    context = {'profiles': profiles, 'query': query}
    return render(request, "jobboard/RecruiterTalentSearch.html", context)
