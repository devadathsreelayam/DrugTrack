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

class PredictionForm(forms.Form):
    AGE_CHOICES = [(i, i) for i in range(1, 121)]
    SEX_CHOICES = [('M', 'Male'), ('F', 'Female')]
    BP_CHOICES = [('HIGH', 'High'), ('LOW', 'Low'), ('NORMAL', 'Normal')]
    CHOL_CHOICES = [('HIGH', 'High'), ('NORMAL', 'Normal')]
    
    age = forms.ChoiceField(choices=AGE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    sex = forms.ChoiceField(choices=SEX_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    bp = forms.ChoiceField(choices=BP_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    cholesterol = forms.ChoiceField(choices=CHOL_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    na_to_k = forms.FloatField(min_value=5.0, max_value=40.0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ('image', 'notes')
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

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
    """Stage 3: Current health status"""
    bp = forms.ChoiceField(choices=[('', 'Select blood pressure'), ('HIGH', 'High'), ('LOW', 'Low'), ('NORMAL', 'Normal')],
                          widget=forms.Select(attrs={'class': 'form-select'}))
    cholesterol = forms.ChoiceField(choices=[('', 'Select cholesterol level'), ('HIGH', 'High'), ('NORMAL', 'Normal')],
                                   widget=forms.Select(attrs={'class': 'form-select'}))
    na_to_k = forms.FloatField(
        min_value=5.0, max_value=40.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'e.g., 15.5'})
    )


class Stage4MedicationsForm(forms.Form):
    """Stage 4: Existing medications"""
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
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List any other medications you take...'})
    )
