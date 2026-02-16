from django.shortcuts import render, redirect

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect("admin_dashboard")
        elif request.user.role == "RECRUITER":
            return redirect("recruiter_dashboard")
        else:
            return redirect("jobseeker_dashboard")
    return render(request, "core/HomePage.html")
