from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.pharmacy.models import Pharmacy, Drug, PharmacyStock
import random
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate sample pharmacies with different statuses'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Generating pharmacies...'))
        
        # Get or create a pharmacy owner
        owner, _ = User.objects.get_or_create(
            username='pharmacy_admin',
            defaults={
                'email': 'pharmacy_admin@example.com',
                'first_name': 'Pharmacy',
                'last_name': 'Admin',
                'is_staff': True,
            }
        )
        if not owner.password:
            owner.set_password('admin123')
            owner.save()
        
        # Get some drugs to associate with pharmacies
        drugs = list(Drug.objects.all())
        if not drugs:
            self.stdout.write(self.style.WARNING('⚠️ No drugs found. Run seed_medicines first.'))
            return
        
        pharmacies_data = [
            {
                'name': 'City Medical Store',
                'email': 'citymedicals@example.com',
                'phone': '9876543210',
                'license_number': 'LIC001',
                'address': '123 MG Road, Kochi',
                'city': 'Kochi',
                'state': 'Kerala',
                'pincode': '682001',
                'latitude': 9.9312,
                'longitude': 76.2673,
                'opens_at': '08:00:00',
                'closes_at': '22:00:00',
                'is_open_24x7': False,
                'status': 'approved',
                'is_active': True,
                'verified_badge': True,
                'owner': owner,
            },
            {
                'name': 'HealthPlus Pharmacy',
                'email': 'healthplus@example.com',
                'phone': '9876543211',
                'license_number': 'LIC002',
                'address': '45 Park Street, Thrissur',
                'city': 'Thrissur',
                'state': 'Kerala',
                'pincode': '680001',
                'latitude': 10.5276,
                'longitude': 76.2144,
                'opens_at': '09:00:00',
                'closes_at': '21:00:00',
                'is_open_24x7': False,
                'status': 'approved',
                'is_active': True,
                'verified_badge': True,
                'owner': owner,
            },
            {
                'name': 'MediCare Pharmacy',
                'email': 'medicare@example.com',
                'phone': '9876543212',
                'license_number': 'LIC003',
                'address': '78 Temple Road, Kottayam',
                'city': 'Kottayam',
                'state': 'Kerala',
                'pincode': '686001',
                'latitude': 9.5916,
                'longitude': 76.5222,
                'opens_at': '07:00:00',
                'closes_at': '23:00:00',
                'is_open_24x7': False,
                'status': 'approved',
                'is_active': True,
                'verified_badge': True,
                'owner': owner,
            },
            {
                'name': 'Apollo Pharmacy',
                'email': 'apollo@example.com',
                'phone': '9876543213',
                'license_number': 'LIC004',
                'address': '123 Hospital Road, Trivandrum',
                'city': 'Trivandrum',
                'state': 'Kerala',
                'pincode': '695001',
                'latitude': 8.5241,
                'longitude': 76.9366,
                'opens_at': '06:00:00',
                'closes_at': '00:00:00',
                'is_open_24x7': True,
                'status': 'approved',
                'is_active': True,
                'verified_badge': True,
                'owner': owner,
            },
            {
                'name': 'Wellness Pharmacy',
                'email': 'wellness@example.com',
                'phone': '9876543214',
                'license_number': 'LIC005',
                'address': '56 Lake View, Alappuzha',
                'city': 'Alappuzha',
                'state': 'Kerala',
                'pincode': '688001',
                'latitude': 9.4981,
                'longitude': 76.3388,
                'opens_at': '08:30:00',
                'closes_at': '20:30:00',
                'is_open_24x7': False,
                'status': 'pending',
                'is_active': True,
                'verified_badge': False,
                'owner': owner,
            },
            {
                'name': 'Carewell Pharmacy',
                'email': 'carewell@example.com',
                'phone': '9876543215',
                'license_number': 'LIC006',
                'address': '89 Church Street, Kozhikode',
                'city': 'Kozhikode',
                'state': 'Kerala',
                'pincode': '673001',
                'latitude': 11.2588,
                'longitude': 75.7804,
                'opens_at': '09:00:00',
                'closes_at': '19:00:00',
                'is_open_24x7': False,
                'status': 'pending',
                'is_active': True,
                'verified_badge': False,
                'owner': owner,
            },
            {
                'name': 'Green Pharmacy',
                'email': 'green@example.com',
                'phone': '9876543216',
                'license_number': 'LIC007',
                'address': '12 Garden Road, Palakkad',
                'city': 'Palakkad',
                'state': 'Kerala',
                'pincode': '678001',
                'latitude': 10.7867,
                'longitude': 76.6548,
                'opens_at': '08:00:00',
                'closes_at': '20:00:00',
                'is_open_24x7': False,
                'status': 'suspended',
                'is_active': False,
                'verified_badge': False,
                'owner': owner,
            },
            {
                'name': 'Dhanvanthri Pharmacy',
                'email': 'dhanvanthri@example.com',
                'phone': '9876543217',
                'license_number': 'LIC008',
                'address': '34 Temple Street, Kannur',
                'city': 'Kannur',
                'state': 'Kerala',
                'pincode': '670001',
                'latitude': 11.8745,
                'longitude': 75.3704,
                'opens_at': '07:30:00',
                'closes_at': '21:30:00',
                'is_open_24x7': False,
                'status': 'approved',
                'is_active': True,
                'verified_badge': True,
                'owner': owner,
            },
            {
                'name': 'Sree Pharmacy',
                'email': 'sree@example.com',
                'phone': '9876543218',
                'license_number': 'LIC009',
                'address': '67 Temple Road, Kasaragod',
                'city': 'Kasaragod',
                'state': 'Kerala',
                'pincode': '671001',
                'latitude': 12.4984,
                'longitude': 74.9866,
                'opens_at': '08:00:00',
                'closes_at': '22:00:00',
                'is_open_24x7': False,
                'status': 'pending',
                'is_active': True,
                'verified_badge': False,
                'owner': owner,
            },
            {
                'name': 'Goodwill Pharmacy',
                'email': 'goodwill@example.com',
                'phone': '9876543219',
                'license_number': 'LIC010',
                'address': '90 Main Road, Pathanamthitta',
                'city': 'Pathanamthitta',
                'state': 'Kerala',
                'pincode': '689001',
                'latitude': 9.2648,
                'longitude': 76.7870,
                'opens_at': '08:30:00',
                'closes_at': '19:30:00',
                'is_open_24x7': False,
                'status': 'approved',
                'is_active': True,
                'verified_badge': False,
                'owner': owner,
            },
        ]

        created_count = 0
        skipped_count = 0

        for data in pharmacies_data:
            try:
                pharmacy, created = Pharmacy.objects.get_or_create(
                    license_number=data['license_number'],
                    defaults=data
                )
                
                if created:
                    created_count += 1
                    # Add random stock for approved pharmacies
                    if pharmacy.status == 'approved':
                        # Add 5-10 random drugs to stock
                        num_drugs = random.randint(5, 10)
                        selected_drugs = random.sample(drugs, min(num_drugs, len(drugs)))
                        for drug in selected_drugs:
                            PharmacyStock.objects.get_or_create(
                                pharmacy=pharmacy,
                                drug=drug,
                                defaults={
                                    'quantity': random.randint(20, 100),
                                    'available_quantity': random.randint(10, 50),
                                    'price': round(random.uniform(10.0, 500.0), 2),
                                    'is_available': True,
                                    'reorder_level': random.randint(5, 20),
                                }
                            )
                    self.stdout.write(self.style.SUCCESS(f'✓ Created: {pharmacy.name} ({pharmacy.get_status_display()})'))
                else:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f'• Skipped: {pharmacy.name} (already exists)'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error creating {data["name"]}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'✅ Pharmacy Generation Complete!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Created: {created_count} pharmacies'))
        self.stdout.write(self.style.SUCCESS(f'📊 Skipped: {skipped_count} pharmacies'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total: {created_count + skipped_count} pharmacies'))
        self.stdout.write(self.style.SUCCESS('='*50))
