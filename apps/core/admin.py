from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Prescription, Medicine, SymptomPrediction

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone_number', 'gender', 'age', 'is_staff', 'date_joined')
    list_filter = ('gender', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone_number', 'gender', 'age', 'address', 'latitude', 'longitude')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'gender', 'age', 'address')
        }),
    )

class SymptomPredictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'predicted_disease', 'severity', 'confidence_score', 'created_at')
    list_filter = ('severity', 'created_at')
    search_fields = ('user__username', 'predicted_disease', 'symptoms')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'diagnosed_disease', 'doctor_name', 'prescribed_date', 'created_at')
    list_filter = ('prescribed_date', 'created_at')
    search_fields = ('user__username', 'diagnosed_disease', 'doctor_name', 'hospital')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Patient', {
            'fields': ('user',)
        }),
        ('Prescription Details', {
            'fields': ('diagnosed_disease', 'doctor_name', 'hospital', 'medicines', 'notes')
        }),
        ('Upload', {
            'fields': ('image',)
        }),
        ('Metadata', {
            'fields': ('prescribed_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_medicine_count(self, obj):
        return len(obj.medicines) if obj.medicines else 0
    get_medicine_count.short_description = 'Medicines'


class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'uses_summary')
    search_fields = ('name',)
    
    def uses_summary(self, obj):
        return obj.uses[:50] + '...' if len(obj.uses) > 50 else obj.uses
    uses_summary.short_description = 'Uses'

admin.site.register(User, CustomUserAdmin)
admin.site.register(SymptomPrediction, SymptomPredictionAdmin)
admin.site.register(Prescription, PrescriptionAdmin)
admin.site.register(Medicine, MedicineAdmin)
