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
            if field_name != 'role' and field.widget.input_type != 'radio':
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
 