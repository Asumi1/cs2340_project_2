from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .models import Job, Application, Interview, Message, SavedSearch, Notification
from .forms import JobForm, ApplicationForm, ScreeningQuestionFormSet, EmailCandidateForm
from accounts.models import CustomUser, RecruiterProfile, JobSeekerProfile
from django.db.models import Q, Count
from django.utils import timezone
import csv

# Helper to ensure only recruiters access certain views
def recruiter_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role != CustomUser.Role.RECRUITER:
            return redirect('home') # or forbidden page
        return view_func(request, *args, **kwargs)
    return wrapper

@staff_member_required
def admin_dashboard(request):
    moderation_jobs = Job.objects.filter(is_active=True).order_by('-created_at')
    pending_jobs = moderation_jobs.filter(is_approved=False)
    active_jobs_count = moderation_jobs.filter(is_approved=True).count()
    total_users_count = CustomUser.objects.count()

    # User management (Story 19)
    user_search = request.GET.get('user_search', '')
    role_filter = request.GET.get('role_filter', '')
    all_users = CustomUser.objects.all().order_by('-date_joined')
    if user_search:
        all_users = all_users.filter(
            Q(username__icontains=user_search) |
            Q(email__icontains=user_search) |
            Q(first_name__icontains=user_search) |
            Q(last_name__icontains=user_search)
        )
    if role_filter:
        all_users = all_users.filter(role=role_filter)
    
    context = {
        'moderation_jobs': moderation_jobs,
        'pending_jobs': pending_jobs,
        'active_jobs_count': active_jobs_count,
        'total_users_count': total_users_count,
        'all_users': all_users,
        'user_search': user_search,
        'role_filter': role_filter,
    }
    return render(request, 'jobboard/AdminDashboard.html', context)

@staff_member_required
def approve_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if 'approve' in request.POST:
        job.is_approved = True
        job.is_active = True
        job.save()
        messages.success(request, f"Job {job.title} has been approved.")
    elif 'reject' in request.POST or 'remove' in request.POST:
        job.is_active = False
        job.is_approved = False
        job.save()
        messages.warning(request, f"Job {job.title} has been removed from public listings.")
    
    return redirect('admin_dashboard')

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


@staff_member_required
@require_http_methods(["POST"])
def admin_toggle_user_active(request, pk):
    """Toggle a user's is_active status"""
    target_user = get_object_or_404(CustomUser, pk=pk)
    if target_user == request.user:
        messages.error(request, "You cannot deactivate yourself.")
        return redirect('admin_dashboard')
    target_user.is_active = not target_user.is_active
    target_user.save()
    status = "activated" if target_user.is_active else "deactivated"
    messages.success(request, f"User {target_user.username} has been {status}.")
    return redirect('admin_dashboard')


@staff_member_required
@require_http_methods(["POST"])
def admin_change_user_role(request, pk):
    """Change a user's role"""
    target_user = get_object_or_404(CustomUser, pk=pk)
    new_role = request.POST.get('role', '')
    if new_role in [CustomUser.Role.RECRUITER, CustomUser.Role.JOBSEEKER]:
        old_role = target_user.role
        target_user.role = new_role
        target_user.save()
        if new_role == CustomUser.Role.JOBSEEKER:
            if RecruiterProfile.objects.filter(user=target_user).exists():
                RecruiterProfile.objects.filter(user=target_user).delete()
            if not JobSeekerProfile.objects.filter(user=target_user).exists():
                JobSeekerProfile.objects.create(user=target_user)
        elif new_role == CustomUser.Role.RECRUITER:
            if JobSeekerProfile.objects.filter(user=target_user).exists():
                JobSeekerProfile.objects.filter(user=target_user).delete()
            if not RecruiterProfile.objects.filter(user=target_user).exists():
                RecruiterProfile.objects.create(user=target_user, company_name="Pending")
        messages.success(request, f"User {target_user.username} role changed from {old_role} to {new_role}.")
    else:
        messages.error(request, "Invalid role specified.")
    return redirect('admin_dashboard')

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

    # Story 6: Job recommendations based on skills
    recommended_jobs = []
    if user_skills:
        q_filter = Q()
        for skill in user_skills:
            q_filter |= Q(skills__icontains=skill)
        recommended_jobs = list(
            Job.objects.filter(q_filter, is_active=True, is_approved=True)
            .exclude(pk__in=applied_job_ids)
            .distinct()
            .order_by('-created_at')[:6]
        )
        # Calculate match score for each recommended job
        for rj in recommended_jobs:
            job_skills = [s.strip().lower() for s in rj.skills.split(',') if s.strip()] if rj.skills else []
            user_skills_lower = [s.lower() for s in user_skills]
            matching = len(set(user_skills_lower) & set(job_skills))
            total = max(len(set(user_skills_lower) | set(job_skills)), 1)
            rj.match_score = int((matching / total) * 100)
        recommended_jobs.sort(key=lambda j: j.match_score, reverse=True)

    # Unread message count
    unread_messages = Message.objects.filter(receiver=request.user, is_read=False).count()

    context = {
        'jobs': jobs,
        'my_applications': my_applications,
        'user_skills': user_skills,
        'one_click_job': one_click_job,
        'recommended_jobs': recommended_jobs,
        'unread_messages': unread_messages,
    }
    return render(request, "jobboard/JobSeekerDashboard.html", context)

@login_required
@ensure_csrf_cookie
def jobseeker_map_viewer(request):
    # Only show jobs that are active and approved and have coordinates
    jobs = Job.objects.filter(is_active=True, is_approved=True, latitude__isnull=False, longitude__isnull=False)
    preferred_radius_miles = 100
    if request.user.role == CustomUser.Role.JOBSEEKER and hasattr(request.user, 'jobseekerprofile'):
        preferred_radius_miles = max(1, min(request.user.jobseekerprofile.preferred_commute_radius_miles, 100))
    return render(
        request,
        "jobboard/JobSeekerMapViewer.html",
        {
            "jobs": jobs,
            "preferred_radius_miles": preferred_radius_miles,
        },
    )


@login_required
@require_http_methods(["POST"])
def update_commute_radius_preference(request):
    if request.user.role != CustomUser.Role.JOBSEEKER:
        return JsonResponse({'error': 'Only job seekers can update commute preferences.'}, status=403)

    profile = getattr(request.user, 'jobseekerprofile', None)
    if not profile:
        return JsonResponse({'error': 'Job seeker profile not found.'}, status=404)

    try:
        radius = int(request.POST.get('radius_miles', ''))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Radius must be a valid integer.'}, status=400)

    if radius < 1 or radius > 100:
        return JsonResponse({'error': 'Radius must be between 1 and 100 miles.'}, status=400)

    profile.preferred_commute_radius_miles = radius
    profile.save(update_fields=['preferred_commute_radius_miles'])
    return JsonResponse({'success': True, 'preferred_radius_miles': radius})

@login_required
def jobseeker_search(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    job_type = request.GET.get('job_type', '')
    work_mode = request.GET.get('work_mode', '')
    min_salary = request.GET.get('min_salary', '')
    max_salary = request.GET.get('max_salary', '')
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
        # Backward compatibility for any legacy short codes in URLs.
        legacy_job_type_map = {
            'FT': 'FULL_TIME',
            'PT': 'PART_TIME',
            'CT': 'CONTRACT',
            'IN': 'INTERNSHIP',
        }
        job_type = legacy_job_type_map.get(job_type, job_type)
        jobs = jobs.filter(job_type=job_type)

    if work_mode:
        jobs = jobs.filter(work_mode=work_mode)
        
    if min_salary:
        try:
            jobs = jobs.filter(salary_max__gte=min_salary)
        except (ValueError, TypeError):
            pass

    if max_salary:
        try:
            jobs = jobs.filter(salary_min__lte=max_salary)
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
        'work_mode': work_mode,
        'min_salary': min_salary,
        'max_salary': max_salary,
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
    todays_interviews = Interview.objects.filter(
        recruiter=request.user, 
        date_time__date=today
    ).order_by('date_time')

    # Story 16: Candidate recommendations for job postings
    top_candidates = []
    recruiter_jobs = Job.objects.filter(recruiter=request.user, is_active=True, is_approved=True)
    if recruiter_jobs.exists():
        # Collect all skills from recruiter's job postings
        all_job_skills = set()
        for job in recruiter_jobs:
            if job.skills:
                for s in job.skills.split(','):
                    s = s.strip().lower()
                    if s:
                        all_job_skills.add(s)
        
        if all_job_skills:
            # Find candidates whose skills match
            q_filter = Q()
            for skill in all_job_skills:
                q_filter |= Q(skills__icontains=skill)
            
            candidate_profiles = JobSeekerProfile.objects.filter(
                q_filter, is_resume_public=True
            ).select_related('user').distinct()[:20]
            
            for profile in candidate_profiles:
                candidate_skills = [s.strip().lower() for s in profile.skills.split(',') if s.strip()] if profile.skills else []
                matching = len(all_job_skills & set(candidate_skills))
                total = max(len(all_job_skills | set(candidate_skills)), 1)
                match_pct = int((matching / total) * 100)
                top_candidates.append({
                    'profile': profile,
                    'match_pct': match_pct,
                    'matching_skills': matching,
                })
            
            top_candidates.sort(key=lambda c: c['match_pct'], reverse=True)
            top_candidates = top_candidates[:6]

    # Unread messages count
    unread_messages = Message.objects.filter(receiver=request.user, is_read=False).count()
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]

    context = {
        'jobs': jobs,
        'total_applicants': total_applicants,
        'interviews_count': interviews_count,
        'pending_applications': pending_applications,
        'todays_interviews': todays_interviews,
        'today': today,
        'top_candidates': top_candidates,
        'unread_messages': unread_messages,
        'unread_notifications': unread_notifications,
        'recent_notifications': recent_notifications,
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
def recruiter_messaging(request, receiver_id=None):
    """Messaging hub - list conversations and show messages (Story 13)"""
    user = request.user

    # Get all users the current user has exchanged messages with
    sent_to = set(Message.objects.filter(sender=user).values_list('receiver_id', flat=True))
    received_from = set(Message.objects.filter(receiver=user).values_list('sender_id', flat=True))
    conversation_user_ids = sent_to | received_from

    conversations = []
    for uid in conversation_user_ids:
        try:
            other_user = CustomUser.objects.get(pk=uid)
        except CustomUser.DoesNotExist:
            continue
        last_msg = Message.objects.filter(
            Q(sender=user, receiver_id=uid) | Q(sender_id=uid, receiver=user)
        ).order_by('-timestamp').first()
        unread_count = Message.objects.filter(sender_id=uid, receiver=user, is_read=False).count()
        conversations.append({
            'user': other_user,
            'last_message': last_msg,
            'unread_count': unread_count,
        })
    conversations.sort(key=lambda c: c['last_message'].timestamp if c['last_message'] else timezone.now(), reverse=True)

    # Get messages for selected conversation
    selected_user = None
    chat_messages = []
    if receiver_id:
        selected_user = get_object_or_404(CustomUser, pk=receiver_id)
        chat_messages = Message.objects.filter(
            Q(sender=user, receiver=selected_user) | Q(sender=selected_user, receiver=user)
        ).order_by('timestamp')
        # Mark received messages as read
        Message.objects.filter(sender=selected_user, receiver=user, is_read=False).update(is_read=True)
        # If not in conversations list, add them
        if selected_user.id not in conversation_user_ids:
            conversations.insert(0, {
                'user': selected_user,
                'last_message': chat_messages.last() if chat_messages.exists() else None,
                'unread_count': 0,
            })

    context = {
        'conversations': conversations,
        'selected_user': selected_user,
        'chat_messages': chat_messages,
    }
    return render(request, "jobboard/RecruiterMessaging.html", context)


@login_required
@require_http_methods(["POST"])
def send_message(request):
    """Send a message to another user (Story 13)"""
    receiver_id = request.POST.get('receiver_id')
    content = request.POST.get('content', '').strip()

    if not receiver_id or not content:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Message and recipient are required.'}, status=400)
        messages.error(request, "Message and recipient are required.")
        return redirect('messaging')

    receiver = get_object_or_404(CustomUser, pk=receiver_id)
    msg = Message.objects.create(sender=request.user, receiver=receiver, content=content)

    # Create notification for receiver
    Notification.objects.create(
        user=receiver,
        notification_message=f"New message from {request.user.get_full_name() or request.user.username}",
        link=f"/jobboard/messaging/{request.user.id}/"
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message_id': msg.id,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%I:%M %p'),
        })
    return redirect('messaging_conversation', receiver_id=receiver.id)


@login_required
@recruiter_required
def email_candidate(request, user_id):
    """Email a candidate through the platform (Story 14)"""
    candidate = get_object_or_404(CustomUser, pk=user_id)

    if request.method == 'POST':
        form = EmailCandidateForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']
            recruiter_name = request.user.get_full_name() or request.user.username
            company = ''
            if hasattr(request.user, 'recruiterprofile'):
                company = request.user.recruiterprofile.company_name

            full_body = (
                f"Hi {candidate.first_name or candidate.username},\n\n"
                f"{body}\n\n"
                f"Best regards,\n"
                f"{recruiter_name}\n"
                f"{company}\n\n"
                f"--- Sent via MintMatch ---"
            )

            try:
                send_mail(
                    subject=subject,
                    message=full_body,
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[candidate.email],
                    fail_silently=False,
                )
                # Create notification for candidate
                Notification.objects.create(
                    user=candidate,
                    notification_message=f"You received an email from {recruiter_name} ({company})",
                    link=""
                )
                messages.success(request, f"Email sent to {candidate.email} successfully!")
                return redirect('recruiter_talent_search')
            except Exception as e:
                messages.error(request, f"Failed to send email: {str(e)}")
    else:
        form = EmailCandidateForm()

    context = {
        'form': form,
        'candidate': candidate,
    }
    return render(request, "jobboard/EmailCandidate.html", context)


@login_required
@recruiter_required
@require_http_methods(["POST"])
def save_search(request):
    """Save a candidate search (Story 15)"""
    query = request.POST.get('query', request.POST.get('q', ''))
    location = request.POST.get('location', '')
    skill = request.POST.get('skill', '')
    project = request.POST.get('project', '')
    name = request.POST.get('name', '') or f"Search: {query or location or skill or project or 'All'}"

    match_qs = JobSeekerProfile.objects.filter(is_resume_public=True)
    if query:
        match_qs = match_qs.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(skills__icontains=query)
        )
    if location:
        match_qs = match_qs.filter(location__icontains=location)
    if skill:
        match_qs = match_qs.filter(skills__icontains=skill)
    if project:
        match_qs = match_qs.filter(projects__icontains=project)
    initial_match_count = match_qs.count()

    SavedSearch.objects.create(
        recruiter=request.user,
        name=name,
        query=query,
        location=location,
        skill=skill,
        project=project,
        last_match_count=initial_match_count,
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Search saved!'})
    messages.success(request, "Search saved successfully!")
    return redirect('recruiter_talent_search')


@login_required
@recruiter_required
def saved_searches(request):
    """List saved searches (Story 15)"""
    searches = SavedSearch.objects.filter(recruiter=request.user)
    return render(request, "jobboard/SavedSearches.html", {'searches': searches, 'saved_searches': searches})


@login_required
@recruiter_required
@require_http_methods(["POST"])
def delete_saved_search(request, pk):
    """Delete a saved search"""
    search = get_object_or_404(SavedSearch, pk=pk, recruiter=request.user)
    search.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, "Saved search deleted.")
    return redirect('saved_searches')


@login_required
@recruiter_required
def recruiter_applicant_map(request):
    """Show clusters of applicants by location on a map (Story 18)"""
    # Get all applicants who applied to this recruiter's jobs
    applicant_ids = Application.objects.filter(
        job__recruiter=request.user
    ).values_list('applicant_id', flat=True).distinct()

    # Get profiles with locations
    applicant_profiles = JobSeekerProfile.objects.filter(
        user_id__in=applicant_ids
    ).exclude(location='').select_related('user')

    # Group by location for clustering
    location_groups = {}
    for profile in applicant_profiles:
        loc = profile.location.strip()
        if loc:
            if loc not in location_groups:
                location_groups[loc] = {
                    'location': loc,
                    'count': 0,
                    'applicants': [],
                    'latitude': float(profile.latitude) if profile.latitude else None,
                    'longitude': float(profile.longitude) if profile.longitude else None,
                }
            location_groups[loc]['count'] += 1
            location_groups[loc]['applicants'].append({
                'name': profile.user.get_full_name() or profile.user.username,
                'headline': profile.headline or profile.major or 'Candidate',
            })

    location_groups_list = list(location_groups.values())
    for group in location_groups_list:
        group['applicant_names'] = [a['name'] for a in group['applicants']]
        group['applicant_summary'] = ", ".join(group['applicant_names'])

    context = {
        'location_groups': location_groups_list,
        'total_applicants': len(applicant_ids),
    }
    return render(request, "jobboard/RecruiterApplicantMap.html", context)

@login_required
@recruiter_required
def recruiter_talent_search(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    skill = request.GET.get('skill', '')
    project = request.GET.get('project', '')
    
    # Only show profiles that are set to public
    profiles = JobSeekerProfile.objects.filter(is_resume_public=True)

    if query:
        profiles = profiles.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(skills__icontains=query) |
            Q(projects__icontains=query) |
            Q(major__icontains=query) |
            Q(headline__icontains=query) |
            Q(work_experience__icontains=query)
        )
    
    if location:
        profiles = profiles.filter(location__icontains=location)
    
    if skill:
        profiles = profiles.filter(skills__icontains=skill)

    if project:
        profiles = profiles.filter(projects__icontains=project)

    # Get all unique skills for the dropdown
    all_skills_raw = JobSeekerProfile.objects.filter(is_resume_public=True).exclude(skills__isnull=True).exclude(skills='').values_list('skills', flat=True)
    all_skills = set()
    for skill_list in all_skills_raw:
        if skill_list:
            skills_split = [s.strip() for s in skill_list.split(',')]
            all_skills.update(skills_split)
    all_skills = sorted(list(all_skills))

    # Get saved searches for this recruiter (Story 15)
    user_saved_searches = SavedSearch.objects.filter(recruiter=request.user)

    # Check if matching new candidates for saved searches and create notifications (Story 15)
    for saved in user_saved_searches:
        sq = JobSeekerProfile.objects.filter(is_resume_public=True)
        if saved.query:
            sq = sq.filter(
                Q(user__first_name__icontains=saved.query) |
                Q(user__last_name__icontains=saved.query) |
                Q(skills__icontains=saved.query)
            )
        if saved.location:
            sq = sq.filter(location__icontains=saved.location)
        if saved.skill:
            sq = sq.filter(skills__icontains=saved.skill)
        if saved.project:
            sq = sq.filter(projects__icontains=saved.project)

        new_count = sq.count()
        saved.current_matches = new_count
        if new_count > saved.last_match_count:
            Notification.objects.create(
                user=request.user,
                notification_message=f"Saved search '{saved.name or 'Untitled Search'}' has {new_count - saved.last_match_count} new candidate match(es).",
                link=f"/jobboard/recruiter/talent-search/?q={saved.query}&location={saved.location}&skill={saved.skill}&project={saved.project}",
            )
        if new_count != saved.last_match_count:
            saved.last_match_count = new_count
            saved.save(update_fields=['last_match_count'])

    context = {
        'profiles': profiles, 
        'query': query,
        'location': location,
        'skill': skill,
        'project': project,
        'all_skills': all_skills,
        'saved_searches': user_saved_searches,
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
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    # Security Check: Ensure the logged-in recruiter owns the job for this application
    if application.job.recruiter != request.user:
        if is_ajax:
            return JsonResponse({'error': 'You do not have permission to modify this application.'}, status=403)
        messages.error(request, "You do not have permission to modify this application.")
        return redirect('recruiter_dashboard')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status in dict(Application.STATUS_CHOICES):
            application.status = new_status
            application.save()
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'status': application.status,
                    'status_display': application.get_status_display(),
                })
            messages.success(request, f"Application status updated to {application.get_status_display()}.")
        else:
            if is_ajax:
                return JsonResponse({'error': 'Invalid status provided.'}, status=400)
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
