from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Extend default User model
    phone_number = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=10, choices=[
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    ], blank=True)
    age = models.IntegerField(null=True, blank=True)
    address = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return self.username
    
    @property
    def is_pharmacy_owner(self):
        """Check if user owns a pharmacy"""
        from apps.pharmacy.models import Pharmacy
        return Pharmacy.objects.filter(owner=self, status='approved').exists()
    
    @property
    def pharmacy(self):
        """Get user's pharmacy"""
        from apps.pharmacy.models import Pharmacy
        return Pharmacy.objects.filter(owner=self).first()
    
    @property
    def has_pharmacy_license(self):
        """Check if user has an approved pharmacy"""
        from apps.pharmacy.models import Pharmacy
        return Pharmacy.objects.filter(owner=self, status='approved').exists()

class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    age = models.IntegerField()
    sex = models.CharField(max_length=1)  # M or F
    bp = models.CharField(max_length=10)  # HIGH, LOW, NORMAL
    cholesterol = models.CharField(max_length=10)  # HIGH, NORMAL
    na_to_k = models.FloatField()
    predicted_drug = models.CharField(max_length=50)
    confidence_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.predicted_drug} - {self.created_at}"

class Prescription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    image = models.ImageField(upload_to='prescriptions/')
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.uploaded_at}"

class Medicine(models.Model):
    name = models.CharField(max_length=100)
    uses = models.TextField()
    dosage = models.TextField()
    side_effects = models.TextField()
    precautions = models.TextField()
    storage = models.TextField()
    
    def __str__(self):
        return self.name


class UserHealthProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='health_profile')
    bp = models.CharField(max_length=10)  # HIGH, LOW, NORMAL
    cholesterol = models.CharField(max_length=10)  # HIGH, NORMAL
    na_to_k = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Health Profile"


class UserMedication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medications')
    medication_name = models.CharField(max_length=100)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'medication_name')
    
    def __str__(self):
        return f"{self.user.username} - {self.medication_name}"


class SymptomPrediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='symptom_predictions')
    symptoms = models.TextField()
    predicted_disease = models.CharField(max_length=200)
    confidence_score = models.IntegerField()
    severity = models.CharField(max_length=20)
    reasoning = models.TextField()
    suggested_drugs = models.JSONField(default=list)
    common_symptoms_matched = models.JSONField(default=list)
    full_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.predicted_disease} - {self.created_at}"
