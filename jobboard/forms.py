from django import forms
from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'location', 'description', 'job_type', 'salary_min', 'salary_max']
        widgets = {
            'job_type': forms.Select(attrs={'class': 'glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['job_type', 'description']: # these are handled in widgets above
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_classes} glass-input w-full px-4 py-3 rounded-xl outline-none transition-all text-sm font-medium text-charcoal bg-white/50 backdrop-blur-sm focus:bg-white/80 border border-gray-100 placeholder-gray-400'.strip()
