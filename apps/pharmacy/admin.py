from django.contrib import admin
from .models import (
    Pharmacy, Drug, PharmacyStock, 
    PharmacyRating, PharmacyOpeningHours
)

class PharmacyAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'status', 'is_active', 'verified_badge', 'created_at')
    list_filter = ('status', 'is_active', 'verified_badge', 'city')
    search_fields = ('name', 'email', 'license_number', 'address', 'city')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'phone', 'license_number', 'license_image', 'certificate_image')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'pincode', 'latitude', 'longitude')
        }),
        ('Timings', {
            'fields': ('opens_at', 'closes_at', 'is_open_24x7')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'verified_badge', 'owner', 
                       'approved_at', 'approved_by', 'rejection_reason')
        }),
        ('Ratings', {
            'fields': ('average_rating', 'total_ratings'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_pharmacies', 'reject_pharmacies', 'suspend_pharmacies']
    
    def approve_pharmacies(self, request, queryset):
        queryset.update(status='approved', approved_at=request.now, approved_by=request.user)
        self.message_user(request, f"{queryset.count()} pharmacies approved.")
    approve_pharmacies.short_description = "Approve selected pharmacies"
    
    def reject_pharmacies(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} pharmacies rejected.")
    reject_pharmacies.short_description = "Reject selected pharmacies"
    
    def suspend_pharmacies(self, request, queryset):
        queryset.update(status='suspended', is_active=False)
        self.message_user(request, f"{queryset.count()} pharmacies suspended.")
    suspend_pharmacies.short_description = "Suspend selected pharmacies"


class DrugAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'drug_type', 'requires_prescription', 'created_at')
    list_filter = ('drug_type', 'requires_prescription', 'categories')
    search_fields = ('name', 'generic_name', 'manufacturer')
    filter_horizontal = ('interactions',)


class PharmacyStockAdmin(admin.ModelAdmin):
    list_display = ('pharmacy', 'drug', 'quantity', 'price', 'is_available', 'last_updated')
    list_filter = ('is_available', 'pharmacy', 'drug')
    search_fields = ('pharmacy__name', 'drug__name')
    readonly_fields = ('last_updated',)


class PharmacyRatingAdmin(admin.ModelAdmin):
    list_display = ('pharmacy', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'pharmacy')
    search_fields = ('pharmacy__name', 'user__username')


admin.site.register(Pharmacy, PharmacyAdmin)
admin.site.register(Drug, DrugAdmin)
admin.site.register(PharmacyStock, PharmacyStockAdmin)
admin.site.register(PharmacyRating, PharmacyRatingAdmin)
admin.site.register(PharmacyOpeningHours)