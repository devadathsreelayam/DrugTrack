from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPES = [
        ('admin', 'Admin'),
        ('patient', 'Patient'),
        ('pharmacy_owner', 'Pharmacy Owner'),
        ('both', 'Both'),
    ]
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='patient')
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
    def pharmacy(self):
        from apps.pharmacy.models import Pharmacy
        return Pharmacy.objects.filter(owner=self).first()

    @property
    def pharmacy_status(self):
        pharmacy = self.pharmacy
        return pharmacy.status if pharmacy else 'none'
    
    @property
    def is_pharmacy_owner(self):
        from apps.pharmacy.models import Pharmacy
        return Pharmacy.objects.filter(owner=self).exists()
    
    @property
    def has_pharmacy_license(self):
        from apps.pharmacy.models import Pharmacy
        return Pharmacy.objects.filter(owner=self, status='approved').exists()
    
    @property
    def is_patient(self):
        return self.user_type in ['patient', 'both']
    

class Prescription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    
    # Prescription Details
    diagnosed_disease = models.CharField(max_length=200, help_text="What was diagnosed?")
    doctor_name = models.CharField(max_length=200, blank=True, help_text="Doctor's name")
    hospital = models.CharField(max_length=200, blank=True, help_text="Hospital/Clinic name")
    
    # Uploaded image
    image = models.ImageField(upload_to='prescriptions/', blank=True, null=True, help_text="Upload prescription image (optional)")
    
    # Structured Medicines (JSON field)
    medicines = models.JSONField(default=list, help_text="List of prescribed medicines with details")
    
    # Additional Notes
    notes = models.TextField(blank=True, help_text="Additional instructions or notes")
    
    # Metadata
    prescribed_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.diagnosed_disease} - {self.prescribed_date}"
    
    def get_medicine_list(self):
        """Return list of medicine names"""
        return [med.get('name', '') for med in self.medicines if med.get('name')]
    
    def get_medicine_names_string(self):
        """Return comma-separated medicine names"""
        return ', '.join(self.get_medicine_list())

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
    
    # Blood Pressure
    bp = models.CharField(max_length=10, blank=True, null=True)  # HIGH, LOW, NORMAL
    
    # Cholesterol
    cholesterol = models.CharField(max_length=10, blank=True, null=True)  # HIGH, NORMAL
    
    # Blood Sugar / Diabetes
    blood_sugar = models.CharField(max_length=20, blank=True, null=True, 
                                   help_text="Fasting blood sugar level")
    
    # Weight and Height (for BMI)
    weight = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True,
                                 help_text="Weight in kg")
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True,
                                 help_text="Height in meters")
    
    # Additional health metrics
    allergies = models.TextField(blank=True, null=True, 
                                 help_text="Any known allergies")
    chronic_conditions = models.TextField(blank=True, null=True,
                                          help_text="Chronic conditions like diabetes, hypertension, etc.")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Health Profile"
    
    @property
    def bmi(self):
        """Calculate BMI if weight and height are available"""
        if self.weight and self.height and self.height > 0:
            bmi = self.weight / (self.height ** 2)
            return round(bmi, 1)
        return None
    
    @property
    def bmi_category(self):
        """Get BMI category"""
        bmi = self.bmi
        if bmi is None:
            return "Unknown"
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"


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
