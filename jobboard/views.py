from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from .models import Job, Application, Interview
from .forms import JobForm, ApplicationForm, ScreeningQuestionFormSet
from accounts.models import CustomUser, RecruiterProfile, JobSeekerProfile
from django.db.models import Q, Count
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

import csv
from django.http import HttpResponse

@staff_member_required
def export_jobs_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="job_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Title', 'Company', 'Location', 'Job Type', 'Posted At', 'Is Approved', 'Total Applications'])

    jobs = Job.objects.all().order_by('-created_at')
    for job in jobs:
        app_count = Application.objects.filter(job=job).count()
        writer.writerow([
            job.title,
            job.company_name,
            job.location,
            job.get_job_type_display(),
            job.created_at.strftime("%b %d, %Y %H:%M"),
            "Yes" if job.is_approved else "No",
            app_count
        ])

    return response

@login_required
def jobseeker_dashboard(request):
    jobs = Job.objects.filter(is_active=True, is_approved=True).order_by('-created_at')[:5]
    
    # Get user's recent applications
    my_applications = Application.objects.filter(applicant=request.user).order_by('-applied_at')[:5]
    applied_job_ids = set(
        Application.objects.filter(applicant=request.user).values_list('job_id', flat=True)
    )
    one_click_job = Job.objects.filter(is_active=True, is_approved=True).exclude(
        pk__in=applied_job_ids
    ).order_by('-created_at').first()
    
    # Process skills for display
    user_skills = []
    if hasattr(request.user, 'jobseekerprofile') and request.user.jobseekerprofile.skills:
        user_skills = [s.strip() for s in request.user.jobseekerprofile.skills.split(',') if s.strip()]

    context = {
        'jobs': jobs,
        'my_applications': my_applications,
        'user_skills': user_skills,
        'one_click_job': one_click_job,
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
    
    applied_job_ids = set()
    if request.user.role == CustomUser.Role.JOBSEEKER:
        applied_job_ids = set(
            Application.objects.filter(applicant=request.user).values_list('job_id', flat=True)
        )

    context = {
        'jobs': jobs, 
        'query': query, 
        'location': location,
        'job_type': job_type,
        'min_salary': min_salary,
        'visa': visa,
        'count': jobs.count(),
        'applied_job_ids': applied_job_ids,
    }
    return render(request, "jobboard/JobSeekerSearch.html", context)

@login_required
def one_click_apply_form(request, pk):
    """Display the one-click apply form with pre-filled data"""
    if request.user.role != CustomUser.Role.JOBSEEKER:
        messages.error(request, "Only job seekers can apply for jobs.")
        return redirect('job_detail', pk=pk)
    
    job = get_object_or_404(Job, pk=pk)
    
    # Check if already applied
    if Application.objects.filter(job=job, applicant=request.user).exists():
        next_job = Job.objects.filter(is_active=True, is_approved=True).exclude(
            applications__applicant=request.user
        ).order_by('-created_at').first()
        if next_job:
            messages.info(request, "You already applied to that job. Showing the next available one-click job.")
            return redirect('one_click_apply_form', pk=next_job.pk)
        messages.warning(request, "You have already applied to all currently available jobs.")
        return redirect('jobseeker_search')
    
    # Get user's profile data for pre-filling
    user_profile = request.user.jobseekerprofile if hasattr(request.user, 'jobseekerprofile') else None
    
    context = {
        'job': job,
        'user_profile': user_profile,
    }
    return render(request, 'jobboard/OneClickApplyForm.html', context)


@login_required
@require_http_methods(["POST"])
def one_click_apply_submit(request, pk):
    """Handle one-click apply submission"""
    if request.user.role != CustomUser.Role.JOBSEEKER:
        return JsonResponse({'error': 'Only job seekers can apply'}, status=403)
    
    job = get_object_or_404(Job, pk=pk)
    
    # Check if already applied
    if Application.objects.filter(job=job, applicant=request.user).exists():
        return JsonResponse({'error': 'You have already applied to this job'}, status=400)
    
    try:
        # Create application
        application = Application.objects.create(
            job=job,
            applicant=request.user,
            status='APPLIED',
            cover_letter=request.POST.get('tailored_note', ''),
        )
        
        # Handle resume file if provided
        if 'resume' in request.FILES:
            application.resume = request.FILES['resume']
            application.save()
        
        redirect_url = reverse('one_click_apply_confirmation', kwargs={'pk': application.id})
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Application submitted successfully!',
                'application_id': application.id,
                'redirect_url': redirect_url
            })
        return redirect('one_click_apply_confirmation', pk=application.id)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=400)


@login_required
def one_click_apply_confirmation(request, pk):
    """Display confirmation page after successful application"""
    application = get_object_or_404(Application, pk=pk)
    
    # Ensure user can only view their own application
    if application.applicant != request.user:
        return redirect('jobseeker_dashboard')
    
    context = {
        'application': application,
        'job': application.job,
    }
    return render(request, 'jobboard/OneClickApplyConfirmation.html', context)

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
    jobs = Job.objects.filter(recruiter=request.user, is_active=True).annotate(
        application_count=Count("applications")
    ).order_by('-created_at')
    
    # Get selected job from query param or default to first job
    selected_job_id = request.GET.get('job_id')
    selected_job = None
    
    if selected_job_id:
        selected_job = jobs.filter(pk=selected_job_id).first()
    elif jobs.exists():
        # Prefer the first job that already has candidates.
        selected_job = jobs.filter(application_count__gt=0).first() or jobs.first()

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
        total_applications_count = selected_job.application_count

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
    skill = request.GET.get('skill', '')
    
    # Only show profiles that are set to public
    profiles = JobSeekerProfile.objects.filter(is_resume_public=True)

    if query:
        profiles = profiles.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(skills__icontains=query) |
            Q(major__icontains=query) |
            Q(headline__icontains=query) |
            Q(work_experience__icontains=query)
        )
    
    if location:
        profiles = profiles.filter(location__icontains=location)
    
    if skill:
        profiles = profiles.filter(skills__icontains=skill)

    # Get all unique skills for the dropdown
    all_skills_raw = JobSeekerProfile.objects.filter(is_resume_public=True).exclude(skills__isnull=True).exclude(skills='').values_list('skills', flat=True)
    all_skills = set()
    for skill_list in all_skills_raw:
        if skill_list:
            skills_split = [s.strip() for s in skill_list.split(',')]
            all_skills.update(skills_split)
    all_skills = sorted(list(all_skills))

    context = {
        'profiles': profiles, 
        'query': query,
        'location': location,
        'skill': skill,
        'all_skills': all_skills
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

def one_click_apply(request):
    return render(request, "one-click_apply.html")
