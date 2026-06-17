from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.pharmacy.models import Pharmacy, PharmacyRating
import random
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate sample pharmacy reviews from patients'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Generating pharmacy reviews...'))
        
        # Get all approved pharmacies
        pharmacies = Pharmacy.objects.filter(status='approved', is_active=True)
        if not pharmacies:
            self.stdout.write(self.style.WARNING('⚠️ No approved pharmacies found.'))
            return
        
        # Get all patients (non-staff users)
        patients = User.objects.filter(is_staff=False)
        if not patients:
            self.stdout.write(self.style.WARNING('⚠️ No patients found. Run generate_patients first.'))
            return
        
        review_templates = [
            "Excellent service! The staff was very helpful.",
            "Great pharmacy with all medicines in stock.",
            "Friendly staff and quick service.",
            "Reasonable prices compared to other pharmacies.",
            "Very helpful pharmacist, explained everything clearly.",
            "Clean and well-organized pharmacy.",
            "Fast delivery service for home delivery.",
            "They had the medicines I needed when others didn't.",
            "The pharmacist took time to explain the dosage.",
            "Good experience overall, would recommend.",
            "Very professional and courteous staff.",
            "Quick and efficient service.",
            "They helped me find alternative medicines when something was out of stock.",
            "Always my go-to pharmacy for all prescriptions.",
            "The staff remembers my name and preferences.",
            "Excellent customer service, highly recommend!",
            "Good stock availability and reasonable prices.",
            "Very clean pharmacy with a good atmosphere.",
            "They accept all major insurance plans.",
            "Knowledgeable pharmacists who answer all questions patiently.",
        ]
        
        created_count = 0
        skipped_count = 0
        
        # For each pharmacy, add 2-8 reviews
        for pharmacy in pharmacies:
            # Skip some pharmacies for variety
            if random.random() < 0.2:
                continue
            
            # Select random patients for reviews
            num_reviews = random.randint(2, 8)
            selected_patients = random.sample(list(patients), min(num_reviews, len(patients)))
            
            for patient in selected_patients:
                # Check if this patient already reviewed this pharmacy
                existing_review = PharmacyRating.objects.filter(
                    pharmacy=pharmacy,
                    user=patient
                ).first()
                
                if existing_review:
                    skipped_count += 1
                    continue
                
                # Create review
                rating = random.randint(3, 5)  # Mostly positive reviews
                if random.random() < 0.15:  # 15% chance of lower rating
                    rating = random.randint(1, 2)
                
                review_text = random.choice(review_templates)
                if rating <= 2:
                    review_text = random.choice([
                        "Poor service, unhelpful staff.",
                        "Very expensive compared to others.",
                        "Didn't have the medicines I needed.",
                        "Bad experience, won't come again.",
                        "The staff was rude and unprofessional.",
                    ])
                
                created_at = timezone.now() - timedelta(days=random.randint(0, 90))
                
                try:
                    PharmacyRating.objects.create(
                        pharmacy=pharmacy,
                        user=patient,
                        rating=rating,
                        review=review_text,
                        service_quality=random.randint(1, 5),
                        drug_availability=random.randint(1, 5),
                        value_for_money=random.randint(1, 5),
                        created_at=created_at,
                        updated_at=created_at,
                    )
                    created_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Error creating review: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('✅ Review Generation Complete!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Created: {created_count} reviews'))
        self.stdout.write(self.style.SUCCESS(f'📊 Skipped: {skipped_count} reviews'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total reviews: {PharmacyRating.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('='*50))
