from decimal import Decimal

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Pharmacy(models.Model):
    """Pharmacy registration and profile"""
    # Basic Info
    name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=200, blank=True, help_text="Full name of the pharmacy owner")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    license_number = models.CharField(max_length=50, unique=True)
    license_image = models.ImageField(upload_to='licenses/', help_text="Upload your pharmacy license")
    certificate_image = models.ImageField(upload_to='certificates/', blank=True, null=True)
    
    # Location
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Timings
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)
    is_open_24x7 = models.BooleanField(default=False)
    
    # Status & Verification
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    verified_badge = models.BooleanField(default=False, help_text="Legally registered pharmacy")
    
    # Owner/Manager (User who registered)
    owner = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='pharmacies'
    )
    
    # Admin approval
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_pharmacies'
    )
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Ratings
    average_rating = models.FloatField(default=0.0)
    total_ratings = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Pharmacies"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.city})"
    
    def is_open_now(self):
        """Check if pharmacy is currently open"""
        if self.is_open_24x7:
            return True
        from datetime import datetime
        now = datetime.now().time()
        if self.opens_at and self.closes_at:
            return self.opens_at <= now <= self.closes_at
        return False
    
    def get_status_display(self):
        """Get human-readable status"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class Drug(models.Model):
    """Drug/Medicine information"""
    name = models.CharField(max_length=200, help_text="Brand name")
    generic_name = models.CharField(max_length=200, blank=True, help_text="Generic name")
    
    DRUG_TYPES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('ointment', 'Ointment'),
        ('drop', 'Drops'),
        ('inhaler', 'Inhaler'),
    ]
    drug_type = models.CharField(max_length=20, choices=DRUG_TYPES, default='tablet')
    
    manufacturer = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    dosage_form = models.CharField(max_length=100, blank=True, help_text="e.g., 500mg, 10mg/ml")
    
    # For search and categorization
    categories = models.CharField(max_length=255, blank=True, help_text="Comma-separated categories")
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags for search")
    
    # For drug interactions (self-referential many-to-many)
    interactions = models.ManyToManyField(
        'self', 
        symmetrical=True, 
        blank=True,
        help_text="Drugs that interact with this drug"
    )
    
    # Prescription required flag
    requires_prescription = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ('name', 'generic_name')
    
    def __str__(self):
        return f"{self.name} ({self.generic_name or self.dosage_form})"
    
    @property
    def display_name(self):
        if self.generic_name:
            return f"{self.name} ({self.generic_name})"
        return self.name


class PharmacyStock(models.Model):
    """Stock management for pharmacies"""
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='stock_items')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='pharmacy_stock')
    
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_available = models.BooleanField(default=True)
    available_quantity = models.IntegerField(default=0, help_text="Quantity available for sale")
    
    # Optional fields
    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    reorder_level = models.IntegerField(default=10, help_text="Notify when stock falls below this")
    
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='stock_updates'
    )
    
    class Meta:
        unique_together = ('pharmacy', 'drug')
        ordering = ['-last_updated']
    
    def __str__(self):
        return f"{self.pharmacy.name} - {self.drug.name} ({self.quantity})"
    
    def is_in_stock(self, quantity=1):
        return self.available_quantity >= quantity
    
    def reduce_stock(self, quantity):
        if self.is_in_stock(quantity):
            self.quantity -= quantity
            self.available_quantity -= quantity
            self.save()
            return True
        return False


class PharmacyRating(models.Model):
    """Ratings and reviews for pharmacies"""
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pharmacy_ratings')
    
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True)
    
    # Services rated
    service_quality = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    drug_availability = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    value_for_money = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('pharmacy', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.pharmacy.name} ({self.rating}★)"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update pharmacy average rating
        ratings = self.pharmacy.ratings.all()
        avg = sum(r.rating for r in ratings) / ratings.count()
        self.pharmacy.average_rating = avg
        self.pharmacy.total_ratings = ratings.count()
        self.pharmacy.save()


class PharmacyOpeningHours(models.Model):
    """Weekly opening hours (optional separate model)"""
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='opening_hours')
    day = models.IntegerField(choices=DAY_CHOICES)
    opens_at = models.TimeField()
    closes_at = models.TimeField()
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('pharmacy', 'day')
    
    def __str__(self):
        return f"{self.pharmacy.name} - {self.get_day_display()}"


class Order(models.Model):
    """Order placed by a user for pharmacy items"""
    
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('mailed', 'Mailed'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    DELIVERY_OPTIONS = [
        ('pickup', 'Pick up from Pharmacy'),
        ('delivery', 'Deliver to Address'),
    ]
    
    # User and Pharmacy
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    pharmacy = models.ForeignKey('Pharmacy', on_delete=models.CASCADE, related_name='orders')
    
    # Order Details
    order_number = models.CharField(max_length=20, unique=True)
    delivery_option = models.CharField(max_length=10, choices=DELIVERY_OPTIONS, default='pickup')
    delivery_address = models.TextField(blank=True, help_text="Delivery address (if delivery option selected)")
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    packaging_charge = models.DecimalField(max_digits=10, decimal_places=2, default=25.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Status
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    status_updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For delivery tracking
    tracking_number = models.CharField(max_length=50, blank=True, help_text="Courier tracking number")
    estimated_delivery = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order_number} - {self.user.username} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: ORD + timestamp + random
            import random
            import time
            timestamp = str(int(time.time()))[-6:]
            random_num = str(random.randint(1000, 9999))
            self.order_number = f"ORD{timestamp}{random_num}"
        super().save(*args, **kwargs)
    
    @staticmethod
    def calculate_delivery_charge(distance_km):
        """Calculate delivery fee using the first 5km free, then ₹25 per 10km block."""
        if distance_km is None:
            return Decimal('0.00')

        try:
            distance = Decimal(str(distance_km))
        except (TypeError, ValueError):
            return Decimal('0.00')

        if distance <= Decimal('5'):
            return Decimal('0.00')

        extra_km = max(distance - Decimal('5'), Decimal('0.00'))
        blocks = int((extra_km / Decimal('10')).to_integral_value(rounding='ROUND_CEILING'))
        return Decimal('25.00') * Decimal(blocks)

    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status not in ['mailed', 'out_for_delivery', 'delivered', 'cancelled']
    
    def can_update_status(self):
        """Check if status can be updated"""
        return self.status != 'cancelled'


class OrderItem(models.Model):
    """Items in an order"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    stock = models.ForeignKey('PharmacyStock', on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Optional fields
    notes = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"{self.order.order_number} - {self.stock.drug.name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)
