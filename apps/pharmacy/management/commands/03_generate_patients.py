from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.core.models import UserHealthProfile, UserMedication, SymptomPrediction
from apps.pharmacy.models import Drug
import random
from datetime import timedelta, datetime

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate sample patient profiles and symptom predictions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Generating patients and predictions...'))
        
        # Sample data for random generation
        first_names = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emma', 'Robert', 'Lisa', 'William', 'Olivia',
                       'James', 'Priya', 'Rajesh', 'Anita', 'Suresh', 'Deepa', 'Vijay', 'Meera', 'Karthik', 'Sneha']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
                      'Kumar', 'Nair', 'Menon', 'Pillai', 'Iyer', 'Rao', 'Sharma', 'Patel', 'Singh', 'Reddy']
        
        bp_options = ['HIGH', 'NORMAL', 'LOW']
        cholesterol_options = ['HIGH', 'NORMAL']
        blood_sugar_options = ['NORMAL', 'PRE_DIABETIC', 'DIABETIC']
        severity_options = ['Mild', 'Moderate', 'Severe']
        
        symptom_templates = [
            "I have a fever of {temp}°F, severe headache, and body aches. This started {days} days ago.",
            "Persistent dry cough for {days} weeks, shortness of breath when walking, chest tightness.",
            "Severe abdominal pain in the lower right side, nausea, vomiting, loss of appetite.",
            "Frequent urination, excessive thirst, blurred vision, feeling tired all the time for {days} months.",
            "I have a runny nose, sneezing, mild headache, and my throat feels scratchy.",
            "Joint pain and swelling in knees and hands, especially in the morning. Lasts for about {hours} hours.",
            "Sharp chest pain when breathing deeply, shortness of breath, cough with yellow mucus.",
            "Dizziness, palpitations, feeling lightheaded when standing up quickly.",
            "Skin rash with intense itching, hives appearing after eating certain foods.",
            "Unexplained weight loss, increased appetite, nervousness, and sweating.",
        ]
        
        disease_templates = [
            'Influenza', 'Pneumonia', 'Appendicitis', 'Type 2 Diabetes', 'Common Cold',
            'Rheumatoid Arthritis', 'Bronchitis', 'Hypotension', 'Allergic Reaction', 'Hyperthyroidism',
            'Gastroenteritis', 'Urinary Tract Infection', 'Sinusitis', 'Migraine', 'Asthma',
            'Hypertension', 'Acid Reflux', 'Anemia', 'Depression', 'Anxiety'
        ]
        
        drug_templates = [
            ['Paracetamol', 'Aspirin'],
            ['Amoxicillin', 'Azithromycin'],
            ['Metformin', 'Glimepiride'],
            ['Atorvastatin', 'Rosuvastatin'],
            ['Lisinopril', 'Amlodipine'],
            ['Omeprazole', 'Pantoprazole'],
            ['Cetirizine', 'Loratadine'],
            ['Doxycycline', 'Ciprofloxacin'],
            ['Ibuprofen', 'Tramadol'],
            ['Sertraline', 'Escitalopram'],
        ]
        
        medications_list = [
            'Paracetamol', 'Metformin', 'Lisinopril', 'Omeprazole', 'Aspirin',
            'Atorvastatin', 'Amlodipine', 'Pantoprazole', 'Cetirizine', 'Ibuprofen',
            'Vitamin D3', 'Calcium', 'Iron Folic Acid', 'Salbutamol', 'Montelukast'
        ]
        
        # Get or create sample patients
        patients = []
        patient_count = 10
        
        for i in range(patient_count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"patient_{i+1}_{first_name.lower()}"
            email = f"{first_name.lower()}.{last_name.lower()}@example.com"
            
            # Create patient
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': f"{random.randint(6000000000, 9999999999)}",
                    'gender': random.choice(['M', 'F']),
                    'age': random.randint(18, 75),
                    'address': f"{random.randint(1, 999)} {random.choice(['Main', 'Park', 'Lake', 'Hill', 'Garden'])} Street",
                    'latitude': random.uniform(8.0, 12.0),
                    'longitude': random.uniform(74.0, 78.0),
                    'is_active': True,
                }
            )
            
            if created:
                user.set_password('patient123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Created patient: {user.username} ({first_name} {last_name})'))
                
                # Create health profile
                health_profile, _ = UserHealthProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'bp': random.choice(bp_options),
                        'cholesterol': random.choice(cholesterol_options),
                        'blood_sugar': random.choice(blood_sugar_options),
                        'weight': round(random.uniform(50.0, 100.0), 1),
                        'height': round(random.uniform(1.50, 2.00), 2),
                        'allergies': random.choice(['None', 'Penicillin', 'Dust', 'Pollen', 'Peanuts', 'None']),
                        'chronic_conditions': random.choice(['None', 'Diabetes', 'Hypertension', 'Asthma', 'None']),
                    }
                )
                
                # Add random medications (1-4)
                num_meds = random.randint(1, 4)
                selected_meds = random.sample(medications_list, min(num_meds, len(medications_list)))
                for med_name in selected_meds:
                    UserMedication.objects.get_or_create(
                        user=user,
                        medication_name=med_name
                    )
                
                # Create 1-5 symptom predictions
                num_predictions = random.randint(1, 5)
                for j in range(num_predictions):
                    symptoms = random.choice(symptom_templates).format(
                        temp=random.randint(99, 104),
                        days=random.randint(1, 7),
                        hours=random.randint(1, 6),
                        weeks=random.randint(1, 4),
                        months=random.randint(1, 6)
                    )
                    
                    disease = random.choice(disease_templates)
                    drugs = random.choice(drug_templates)
                    severity = random.choice(severity_options)
                    confidence = random.randint(60, 95)
                    
                    prediction = SymptomPrediction.objects.create(
                        user=user,
                        symptoms=symptoms,
                        predicted_disease=disease,
                        confidence_score=confidence,
                        severity=severity,
                        reasoning=f"Based on the symptoms presented, {disease} is likely.",
                        suggested_drugs=[
                            {'name': drugs[0], 'dosage': 'Standard dosage', 'is_alternative': False},
                            {'name': drugs[1] if len(drugs) > 1 else drugs[0], 'dosage': 'Standard dosage', 'is_alternative': True}
                        ],
                        common_symptoms_matched=random.sample(['fever', 'headache', 'cough', 'fatigue', 'nausea', 'pain'], 3),
                        full_response={},
                        created_at=timezone.now() - timedelta(days=random.randint(0, 60))
                    )
                    
                    patients.append(user)
            else:
                self.stdout.write(self.style.WARNING(f'• Skipped: {username} (already exists)'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('✅ Patient Generation Complete!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total patients: {User.objects.filter(is_staff=False).count()}'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total predictions: {SymptomPrediction.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('='*50))
