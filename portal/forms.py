from django import forms
from academics.models import StudentResult
from students.models import Student


class StudentResultForm(forms.ModelForm):
    """Form for entering student results"""
    class Meta:
        model = StudentResult
        fields = ['test1', 'test2', 'exam']
        widgets = {
            'test1': forms.NumberInput(attrs={
                'class': 'form-control score-input',
                'min': '0',
                'max': '20',
                'placeholder': 'Test 1 (0-20)'
            }),
            'test2': forms.NumberInput(attrs={
                'class': 'form-control score-input',
                'min': '0',
                'max': '20',
                'placeholder': 'Test 2 (0-20)'
            }),
            'exam': forms.NumberInput(attrs={
                'class': 'form-control score-input',
                'min': '0',
                'max': '60',
                'placeholder': 'Exam (0-60)'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        test1 = cleaned_data.get('test1', 0)
        test2 = cleaned_data.get('test2', 0)
        exam = cleaned_data.get('exam', 0)
        
        total = test1 + test2 + exam
        if total > 100:
            raise forms.ValidationError(
                f"Total score ({total}) cannot exceed 100."
            )
        
        return cleaned_data


class BulkResultImportForm(forms.Form):
    """Form for bulk importing student results"""
    csv_file = forms.FileField(
        label='Upload CSV file',
        help_text='CSV format: admission_number, test1, test2, exam'
    )


class StudentQuickAddForm(forms.ModelForm):
    """Form for teachers to quickly add students to a class"""
    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'admission_number', 'gender', 'date_of_birth']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'admission_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Admission Number'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
