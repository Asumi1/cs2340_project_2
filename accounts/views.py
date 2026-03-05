from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm, JobSeekerProfileForm, RecruiterProfileForm
from .models import JobSeekerProfile, RecruiterProfile, CustomUser

def signup_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create the corresponding profile based on role
            if user.role == CustomUser.Role.JOBSEEKER:
                JobSeekerProfile.objects.create(user=user)
            elif user.role == CustomUser.Role.RECRUITER:
                company = form.cleaned_data.get("company_name", "Pending Company Name")
                RecruiterProfile.objects.create(user=user, company_name=company)
            
            login(request, user)
            
            # Redirect based on role
            if user.role == CustomUser.Role.RECRUITER:
                return redirect("recruiter_dashboard")
            elif user.role == CustomUser.Role.JOBSEEKER:
                return redirect("jobseeker_dashboard")
            return redirect("home")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if "next" in request.POST:
                return redirect(request.POST.get("next"))
            
            # Redirect based on role
            if user.role == CustomUser.Role.RECRUITER:
                return redirect("recruiter_dashboard")
            elif user.role == CustomUser.Role.JOBSEEKER:
                return redirect("jobseeker_dashboard")
            return redirect("home")
    else:
        form = CustomAuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("home")

@login_required
def edit_profile(request):
    user = request.user
    if user.is_staff or user.is_superuser:
        return redirect('admin_dashboard')

    if user.role == CustomUser.Role.JOBSEEKER:
        try:
            profile = user.jobseekerprofile
        except JobSeekerProfile.DoesNotExist:
            profile = JobSeekerProfile.objects.create(user=user)
        
        if request.method == 'POST':
            form = JobSeekerProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('jobseeker_dashboard')
        else:
            form = JobSeekerProfileForm(instance=profile)
            
    elif user.role == CustomUser.Role.RECRUITER:
        try:
            profile = user.recruiterprofile
        except RecruiterProfile.DoesNotExist:
            profile = RecruiterProfile.objects.create(user=user, company_name="Unknown")
            
        if request.method == 'POST':
            form = RecruiterProfileForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('recruiter_dashboard')
        else:
            form = RecruiterProfileForm(instance=profile)
    else:
        return redirect('home')
    
    return render(request, 'accounts/profile_edit.html', {'form': form})
