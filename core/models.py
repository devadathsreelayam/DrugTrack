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
    

class Pharmacy(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Pharmacies"