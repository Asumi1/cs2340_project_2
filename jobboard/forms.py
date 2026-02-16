from django import forms
from .models import Job, Application, ScreeningQuestion
from django.forms import inlineformset_factory

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
        fields = ['title', 'location', 'description', 'job_type', 'salary_min', 'salary_max', 'skills', 'latitude', 'longitude']
        widgets = {
            'job_type': forms.Select(attrs={'class': 'glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100'}),
            'skills': forms.TextInput(attrs={'type': 'hidden', 'id': 'skills-hidden-input'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['job_type', 'description', 'skills']: # these are handled in widgets above or hidden
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_classes} glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100 placeholder-gray-400'.strip()

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

