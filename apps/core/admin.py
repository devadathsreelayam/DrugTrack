from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Prediction, Prescription, Medicine

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone_number', 'gender', 'age', 'is_staff', 'date_joined')
    list_filter = ('gender', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'gender', 'age', 'address', 'latitude', 'longitude')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'gender', 'age', 'address')
        }),
    )

class PredictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'predicted_drug', 'age', 'sex', 'bp', 'cholesterol', 'created_at')
    list_filter = ('predicted_drug', 'bp', 'cholesterol', 'created_at')
    search_fields = ('user__username', 'predicted_drug')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'uploaded_at', 'image_tag')
    list_filter = ('uploaded_at',)
    search_fields = ('user__username',)
    readonly_fields = ('uploaded_at',)
    
    def image_tag(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" />'
        return '-'
    image_tag.allow_tags = True
    image_tag.short_description = 'Preview'

class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'uses_summary')
    search_fields = ('name',)
    
    def uses_summary(self, obj):
        return obj.uses[:50] + '...' if len(obj.uses) > 50 else obj.uses
    uses_summary.short_description = 'Uses'

admin.site.register(User, CustomUserAdmin)
admin.site.register(Prediction, PredictionAdmin)
admin.site.register(Prescription, PrescriptionAdmin)
admin.site.register(Medicine, MedicineAdmin)
