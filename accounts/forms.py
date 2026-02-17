from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    company_name = forms.CharField(required=False, help_text="Required for Recruiters")

    class Meta:
        model = CustomUser
        fields = ("username", "email", "first_name", "last_name", "role")
        widgets = {
            'role': forms.RadioSelect, 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add glass-input styling to all fields except role
        for field_name, field in self.fields.items():
            is_radio = getattr(field.widget, 'input_type', None) == 'radio'
            if field_name != 'role' and not is_radio:
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = (existing_classes + ' glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal placeholder-gray-400').strip()
        
        # Specific hidden logic for company_name is handled in template, but we adding basic style here.

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        company_name = cleaned_data.get("company_name")
        
        if role == CustomUser.Role.RECRUITER and not company_name:
            self.add_error("company_name", "Company name is required for Recruiters.")
        
        return cleaned_data

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("username", "email", "first_name", "last_name")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing_classes + ' glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal').strip()

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing_classes + ' glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal placeholder-gray-400').strip()

from .models import JobSeekerProfile, RecruiterProfile

class JobSeekerProfileForm(forms.ModelForm):
    class Meta:
        model = JobSeekerProfile
        fields = ['headline', 'bio', 'location', 'major', 'skills', 'education', 'work_experience', 'linkedin_url', 'portfolio_url', 'profile_photo', 'resume_file', 'is_resume_public']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'education': forms.Textarea(attrs={'rows': 3}),
            'work_experience': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            is_checkbox = getattr(field.widget, 'input_type', None) == 'checkbox'
            is_file = getattr(field.widget, 'input_type', None) == 'file'
            
            if is_checkbox:
                field.widget.attrs['class'] = 'sr-only peer'
                continue
                
            if is_file:
                field.widget.attrs['class'] = 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-neutral-900 hover:file:bg-primary/20 transition-colors'
                continue

            if field_name == 'headline':
                field.widget.attrs['class'] = 'w-full text-2xl font-bold text-neutral-900 dark:text-white border-0 border-b-2 border-neutral-100 dark:border-neutral-700 bg-transparent px-0 py-2 focus:ring-0 focus:border-primary placeholder-neutral-300 transition-colors'
            elif field_name == 'bio':
                field.widget.attrs['class'] = 'w-full rounded-lg bg-neutral-50 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 focus:border-primary focus:ring-primary/20 text-sm leading-relaxed resize-none p-4'
            else:
                field.widget.attrs['class'] = 'w-full rounded-lg bg-neutral-50 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-700 text-sm focus:border-primary focus:ring-primary/20 transition-colors p-3'

class RecruiterProfileForm(forms.ModelForm):
    class Meta:
        model = RecruiterProfile
        fields = ['company_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'company_name':
                field.widget.attrs['class'] = 'w-full text-2xl font-bold text-neutral-900 dark:text-white border-0 border-b-2 border-neutral-100 dark:border-neutral-700 bg-transparent px-0 py-2 focus:ring-0 focus:border-primary placeholder-neutral-300 transition-colors'
            else:
                field.widget.attrs['class'] = 'w-full rounded-lg bg-neutral-50 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-700 p-3 text-sm focus:border-primary focus:ring-primary/20'
