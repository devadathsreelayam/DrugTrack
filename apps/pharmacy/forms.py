from django import forms
from django.contrib.auth import get_user_model
from .models import Pharmacy, PharmacyStock, PharmacyOpeningHours

User = get_user_model()


class PharmacyRegistrationForm(forms.ModelForm):
    """Form for pharmacy registration"""
    
    class Meta:
        model = Pharmacy
        fields = [
            'name', 'email', 'phone', 'license_number', 'license_image',
            'address', 'city', 'state', 'pincode',
            'opens_at', 'closes_at', 'is_open_24x7'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'opens_at': forms.TimeInput(attrs={'type': 'time'}),
            'closes_at': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ['license_image']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})


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
    radius = forms.IntegerField(
        initial=10, 
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 100
        })
    )
