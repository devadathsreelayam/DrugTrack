from django import forms
from django.contrib.auth import get_user_model
from .models import Pharmacy, PharmacyStock

User = get_user_model()


class PharmacyRegistrationForm(forms.ModelForm):
    """Combined pharmacy registration + user creation form"""
    
    # User fields
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your email address'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a password'}),
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        label='Confirm Password'
    )
    
    # Pharmacy fields
    class Meta:
        model = Pharmacy
        fields = [
            'name', 'phone', 'license_number', 'license_image',
            'address', 'city', 'state', 'pincode',
            'latitude', 'longitude',
            'opens_at', 'closes_at', 'is_open_24x7'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pharmacy name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'License number'}),
            'license_image': forms.FileInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Latitude', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Longitude', 'step': 'any'}),
            'opens_at': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'closes_at': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_open_24x7': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make latitude and longitude optional
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['latitude'].widget = forms.HiddenInput()
        self.fields['longitude'].widget = forms.HiddenInput()
        self.fields['opens_at'].required = False
        self.fields['closes_at'].required = False
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        
        # Check if at least one of opens_at/closes_at is provided or 24x7 is checked
        opens_at = cleaned_data.get('opens_at')
        closes_at = cleaned_data.get('closes_at')
        is_open_24x7 = cleaned_data.get('is_open_24x7')
        
        if not is_open_24x7 and not (opens_at and closes_at):
            self.add_error('opens_at', 'Please provide opening hours or select 24x7.')
        
        return cleaned_data


class PharmacyStockForm(forms.ModelForm):
    """Form for updating pharmacy stock"""
    
    class Meta:
        model = PharmacyStock
        fields = ['drug', 'quantity', 'available_quantity', 'price', 'batch_number', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class PharmacySearchForm(forms.Form):
    """Form for searching pharmacies with drug availability"""
    drug_name = forms.CharField(
        max_length=200, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search for a medicine...'
        })
    )
    city = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City'
        })
    )
