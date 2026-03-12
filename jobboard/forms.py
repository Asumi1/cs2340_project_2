from django import forms
from .models import Job, Application, ScreeningQuestion
from django.forms import inlineformset_factory
import requests
from django.core.exceptions import ValidationError

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cover_letter', 'resume']
        widgets = {
            'cover_letter': forms.Textarea(attrs={'rows': 4, 'class': 'w-full rounded-xl border-slate-200 focus:border-primary focus:ring-primary'}),
            'resume': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary-dark hover:file:bg-primary/20'}),
        }

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'location', 'description', 'job_type', 'work_mode', 'salary_min', 'salary_max', 'skills', 'visa_sponsorship', 'latitude', 'longitude']
        widgets = {
            'job_type': forms.Select(attrs={'class': 'glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100'}),
            'work_mode': forms.Select(attrs={'class': 'glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100'}),
            'skills': forms.TextInput(attrs={'type': 'hidden', 'id': 'skills-hidden-input'}),
            'visa_sponsorship': forms.CheckboxInput(attrs={'class': 'rounded text-primary focus:ring-primary'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['job_type', 'work_mode', 'description', 'skills']: # these are handled in widgets above or hidden
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_classes} glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100 placeholder-gray-400'.strip()

    def save(self, commit=True):
        """Override save to auto-geocode location if coordinates are missing."""
        instance = super().save(commit=False)
        
        # Auto-geocode if location is set but coordinates are missing
        if instance.location and (not instance.latitude or not instance.longitude):
            try:
                response = requests.get(
                    f'https://nominatim.openstreetmap.org/search',
                    params={
                        'q': instance.location,
                        'format': 'json',
                        'limit': 1
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        instance.latitude = float(data[0]['lat'])
                        instance.longitude = float(data[0]['lon'])
            except Exception as e:
                # Silently fail - don't block job creation if geocoding fails
                print(f"Geocoding failed for location '{instance.location}': {e}")
        
        if commit:
            instance.save()
        return instance

class ScreeningQuestionForm(forms.ModelForm):
    class Meta:
        model = ScreeningQuestion
        fields = ['question_text']
        widgets = {
            'question_text': forms.TextInput(attrs={'class': 'w-full bg-white dark:bg-black/20 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary focus:border-transparent', 'placeholder': 'e.g. How many years of experience do you have with Python?'})
        }

ScreeningQuestionFormSet = inlineformset_factory(
    Job, ScreeningQuestion, form=ScreeningQuestionForm,
    extra=1, can_delete=True
)


class EmailCandidateForm(forms.Form):
    subject = forms.CharField(max_length=255, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary focus:border-transparent text-sm',
        'placeholder': 'Email subject...'
    }))
    body = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary focus:border-transparent text-sm',
        'rows': 8,
        'placeholder': 'Write your message...'
    }))


