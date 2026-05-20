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