from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Job, Application, Interview
from .forms import JobForm, ApplicationForm, ScreeningQuestionFormSet
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

@staff_member_required
def admin_dashboard(request):
    pending_jobs = Job.objects.filter(is_approved=False, is_active=True).order_by('-created_at')
    active_jobs_count = Job.objects.filter(is_approved=True, is_active=True).count()
    total_users_count = CustomUser.objects.count()
    
    context = {
        'pending_jobs': pending_jobs,
        'active_jobs_count': active_jobs_count,
        'total_users_count': total_users_count,
    }
    return render(request, 'jobboard/AdminDashboard.html', context)

@staff_member_required
def approve_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if 'approve' in request.POST:
        job.is_approved = True
        job.save()
        messages.success(request, f"Job {job.title} has been approved.")
    elif 'reject' in request.POST:
        job.is_active = False
        job.save()
        messages.warning(request, f"Job {job.title} has been rejected and deactivated.")
    
    return redirect('admin_dashboard')

@login_required
def jobseeker_dashboard(request):
    jobs = Job.objects.filter(is_active=True, is_approved=True).order_by('-created_at')[:5]
    
    # Get user's recent applications
    my_applications = Application.objects.filter(applicant=request.user).order_by('-applied_at')[:5]
    
    # Process skills for display
    user_skills = []
    if hasattr(request.user, 'jobseekerprofile') and request.user.jobseekerprofile.skills:
        user_skills = [s.strip() for s in request.user.jobseekerprofile.skills.split(',') if s.strip()]

    context = {
        'jobs': jobs,
        'my_applications': my_applications,
        'user_skills': user_skills,
    }
    return render(request, "jobboard/JobSeekerDashboard.html", context)

@login_required
def jobseeker_map_viewer(request):
    # Only show jobs that are active and approved and have coordinates
    jobs = Job.objects.filter(is_active=True, is_approved=True, latitude__isnull=False, longitude__isnull=False)
    return render(request, "jobboard/JobSeekerMapViewer.html", {"jobs": jobs})

@login_required
def jobseeker_search(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    job_type = request.GET.get('job_type', '')
    min_salary = request.GET.get('min_salary', '')
    visa = request.GET.get('visa_sponsorship', '')

    # Only show jobs that are active and approved
    jobs = Job.objects.filter(is_active=True, is_approved=True).order_by('-created_at')

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(company_name__icontains=query) |
            Q(description__icontains=query) |
            Q(skills__icontains=query)
        )
    
    if location:
        jobs = jobs.filter(location__icontains=location)
    
    if job_type:
        jobs = jobs.filter(job_type=job_type)
        
    if min_salary:
        try:
            jobs = jobs.filter(salary_max__gte=min_salary)
        except (ValueError, TypeError):
            pass
            
    if visa == 'on':
        jobs = jobs.filter(visa_sponsorship=True)
    
    context = {
        'jobs': jobs, 
        'query': query, 
        'location': location,
        'job_type': job_type,
        'min_salary': min_salary,
        'visa': visa,
        'count': jobs.count()
    }
    return render(request, "jobboard/JobSeekerSearch.html", context)

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
        formset = ScreeningQuestionFormSet(request.POST, prefix='questions')
        
        if form.is_valid() and formset.is_valid():
            job = form.save(commit=False)
            job.recruiter = request.user
            # Get company name from profile
            try:
                profile = RecruiterProfile.objects.get(user=request.user)
                job.company_name = profile.company_name
            except RecruiterProfile.DoesNotExist:
                job.company_name = "Unknown Company"
            
            job.save()
            
            # Save formset
            formset.instance = job
            formset.save()
            
            messages.success(request, 'Job posted successfully!')
            return redirect('recruiter_dashboard')
    else:
        form = JobForm()
        formset = ScreeningQuestionFormSet(prefix='questions')
        
    return render(request, 'jobboard/job_form.html', {
        'form': form, 
        'formset': formset,
        'title': 'Post a New Job'
    })

@login_required
@recruiter_required
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk, recruiter=request.user)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        formset = ScreeningQuestionFormSet(request.POST, instance=job, prefix='questions')
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Job updated successfully!')
            return redirect('recruiter_dashboard')
    else:
        form = JobForm(instance=job)
        formset = ScreeningQuestionFormSet(instance=job, prefix='questions')
        
    return render(request, 'jobboard/job_form.html', {
        'form': form, 
        'formset': formset,
        'title': 'Edit Job'
    })

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
@recruiter_required
def recruiter_kanban(request):
    jobs = Job.objects.filter(recruiter=request.user, is_active=True).order_by('-created_at')
    
    # Get selected job from query param or default to first job
    selected_job_id = request.GET.get('job_id')
    selected_job = None
    
    if selected_job_id:
        selected_job = jobs.filter(pk=selected_job_id).first()
    elif jobs.exists():
        selected_job = jobs.first()

    # Dictionary to hold applications by status
    grouped_applications = {
        'APPLIED': [],
        'SCREENING': [],
        'INTERVIEW': [],
        'OFFER': [],
        'HIRED': [],
        'REJECTED': []
    }
    
    # Fetch applications if a job is selected
    if selected_job:
        apps = Application.objects.filter(job=selected_job).select_related('applicant__jobseekerprofile').order_by('-applied_at')
        for app in apps:
            if app.status in grouped_applications:
                grouped_applications[app.status].append(app)

    # Create stats
    total_applications_count = 0
    if selected_job:
        total_applications_count = Application.objects.filter(job=selected_job).count()

    context = {
        'jobs': jobs,
        'selected_job': selected_job,
        'kanban_columns': grouped_applications,
        'total_applications_count': total_applications_count
    }
    return render(request, "jobboard/RecruiterKanban.html", context)

@login_required
def recruiter_messaging(request):
    return render(request, "jobboard/RecruiterMessaging.html")

@login_required
@recruiter_required
def recruiter_talent_search(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    
    # Only show profiles that are set to public
    profiles = JobSeekerProfile.objects.filter(is_resume_public=True)

    if query:
        profiles = profiles.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(skills__icontains=query) |
            Q(major__icontains=query) |
            Q(headline__icontains=query)
        )
    
    if location:
        profiles = profiles.filter(location__icontains=location)

    context = {
        'profiles': profiles, 
        'query': query,
        'location': location
    }
    return render(request, "jobboard/RecruiterTalentSearch.html", context)

@login_required
@recruiter_required
def recruiter_application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    
    # Security Check: Ensure the logged-in recruiter owns the job for this application
    if application.job.recruiter != request.user:
        messages.error(request, "You do not have permission to view this application.")
        return redirect('recruiter_dashboard')

    context = {
        'application': application,
        'job': application.job,
        'applicant': application.applicant,
        'profile': getattr(application.applicant, 'jobseekerprofile', None)
    }
    return render(request, "jobboard/RecruiterApplicationDetail.html", context)

@login_required
@recruiter_required
def update_application_status(request, pk):
    application = get_object_or_404(Application, pk=pk)
    
    # Security Check: Ensure the logged-in recruiter owns the job for this application
    if application.job.recruiter != request.user:
        messages.error(request, "You do not have permission to modify this application.")
        return redirect('recruiter_dashboard')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status in dict(Application.STATUS_CHOICES):
            application.status = new_status
            application.save()
            messages.success(request, f"Application status updated to {application.get_status_display()}.")
        else:
            messages.error(request, "Invalid status provided.")
    
    return redirect(f'/jobboard/recruiter/kanban/?job_id={application.job.id}')

@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    # Only allow unapproved jobs to be seen by the recruiter or an admin
    if not job.is_approved and not request.user.is_staff and job.recruiter != request.user:
        return redirect('jobseeker_search')
    
    # Check if user has already applied
    has_applied = False
    if request.user.role == CustomUser.Role.JOBSEEKER:
        has_applied = Application.objects.filter(job=job, applicant=request.user).exists()
    
    form = ApplicationForm()

    context = {
        'job': job,
        'has_applied': has_applied,
        'form': form
    }
    return render(request, "jobboard/JobDetail.html", context)

@login_required
def apply_for_job(request, pk):
    if request.user.role != CustomUser.Role.JOBSEEKER:
        messages.error(request, "Only job seekers can apply for jobs.")
        return redirect('job_detail', pk=pk)
        
    job = get_object_or_404(Job, pk=pk)
    
    if Application.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, "You have already applied to this job.")
        return redirect('job_detail', pk=pk)
        
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            application.save()
            messages.success(request, "Application submitted successfully!")
            return redirect('jobseeker_dashboard')
            
    return redirect('job_detail', pk=pk)
