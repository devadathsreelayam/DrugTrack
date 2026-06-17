from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Prescription

class SignupForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=True)
    age = forms.IntegerField(min_value=1, max_value=120, required=True)
    address = forms.CharField(widget=forms.Textarea, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'gender', 'age', 'address', 'password1', 'password2')

class PrescriptionForm(forms.ModelForm):
    """Form for creating structured prescriptions"""
    
    class Meta:
        model = Prescription
        fields = ['diagnosed_disease', 'doctor_name', 'hospital', 'image', 'medicines', 'notes']
        widgets = {
            'diagnosed_disease': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Upper Respiratory Infection'}),
            'doctor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dr. Name'}),
            'hospital': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hospital/Clinic name'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'medicines': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5,
                'placeholder': 'Enter each medicine on a new line with format:\nAmoxicillin 500mg - Twice daily - 7 days\nParacetamol 650mg - Three times daily - 5 days'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional instructions...'}),
        }
        help_texts = {
            'medicines': 'Format: Medicine Name Dosage - Frequency - Duration (one per line)',
        }
    
    def clean_medicines(self):
        """Parse medicines from textarea into structured data"""
        medicines_text = self.cleaned_data.get('medicines', '')
        if isinstance(medicines_text, str):
            structured_medicines = []
            for line in medicines_text.strip().split('\n'):
                line = line.strip()
                if line:
                    # Try to parse the line
                    parts = [p.strip() for p in line.split('-')]
                    if len(parts) >= 1:
                        med_entry = {
                            'name': parts[0],
                            'dosage': parts[1] if len(parts) > 1 else '',
                            'frequency': parts[2] if len(parts) > 2 else '',
                            'duration': parts[3] if len(parts) > 3 else '',
                        }
                        structured_medicines.append(med_entry)
            return structured_medicines
        return medicines_text


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'gender', 'age', 'address')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class Stage1SignupForm(UserCreationForm):
    """Stage 1: Basic account creation"""
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your email address'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class Stage2ProfileForm(forms.ModelForm):
    """Stage 2: Personal details"""
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}))
    gender = forms.ChoiceField(choices=[('', 'Select gender'), ('M', 'Male'), ('F', 'Female'), ('O', 'Other')], 
                               widget=forms.Select(attrs={'class': 'form-select'}))
    age = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age'}))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Your address (optional)'}))
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'gender', 'age', 'address')


class Stage3HealthForm(forms.Form):
    """Stage 3: Health status"""
    
    BP_CHOICES = [
        ('', 'Select blood pressure'),
        ('HIGH', 'High'),
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
    ]
    
    CHOLESTEROL_CHOICES = [
        ('', 'Select cholesterol level'),
        ('HIGH', 'High'),
        ('NORMAL', 'Normal'),
    ]
    
    BLOOD_SUGAR_CHOICES = [
        ('', 'Select blood sugar level'),
        ('NORMAL', 'Normal (70-100 mg/dL)'),
        ('PRE_DIABETIC', 'Pre-diabetic (100-125 mg/dL)'),
        ('DIABETIC', 'Diabetic (126+ mg/dL)'),
        ('UNKNOWN', 'Not sure / Not tested'),
    ]
    
    bp = forms.ChoiceField(
        choices=BP_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    cholesterol = forms.ChoiceField(
        choices=CHOLESTEROL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    blood_sugar = forms.ChoiceField(
        choices=BLOOD_SUGAR_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    weight = forms.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        min_value=20,
        max_value=300,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 70.5',
            'step': '0.1'
        }),
        label='Weight (kg)'
    )
    
    height = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        min_value=0.50,
        max_value=2.50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 1.75',
            'step': '0.01'
        }),
        label='Height (meters)'
    )
    
    allergies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'e.g., Penicillin, Dust, Pollen'
        }),
        label='Known Allergies (optional)'
    )
    
    chronic_conditions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'e.g., Diabetes, Hypertension, Asthma'
        }),
        label='Chronic Conditions (optional)'
    )
    
    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is not None and weight <= 0:
            raise forms.ValidationError('Weight must be greater than 0.')
        return weight
    
    def clean_height(self):
        height = self.cleaned_data.get('height')
        if height is not None and height <= 0:
            raise forms.ValidationError('Height must be greater than 0.')
        return height


class Stage4MedicationsForm(forms.Form):
    """Stage 4: Optional medications."""
    medications = forms.MultipleChoiceField(
        required=False,
        choices=[
            ('aspirin', 'Aspirin'),
            ('warfarin', 'Warfarin'),
            ('metformin', 'Metformin'),
            ('lisinopril', 'Lisinopril'),
            ('atorvastatin', 'Atorvastatin'),
            ('amlodipine', 'Amlodipine'),
            ('levothyroxine', 'Levothyroxine'),
            ('omeprazole', 'Omeprazole'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    other_medications = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional - list any other medications you take...'})
    )
