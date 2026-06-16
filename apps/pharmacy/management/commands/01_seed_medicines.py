from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.pharmacy.models import Drug


class Command(BaseCommand):
    help = 'Seed the database with sample medicines/drugs'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting medicine seeding...'))
        
        medicines = [
            # Common Medicines
            {
                'name': 'Paracetamol',
                'generic_name': 'Acetaminophen',
                'drug_type': 'tablet',
                'manufacturer': 'GSK',
                'description': 'Used for fever and mild to moderate pain relief.',
                'dosage_form': '500mg',
                'categories': 'pain, fever, headache',
                'tags': 'pain, fever, OTC',
                'requires_prescription': False,
            },
            {
                'name': 'Amoxicillin',
                'generic_name': 'Amoxicillin',
                'drug_type': 'capsule',
                'manufacturer': 'Cipla',
                'description': 'Antibiotic used to treat bacterial infections.',
                'dosage_form': '500mg',
                'categories': 'antibiotic, infection',
                'tags': 'antibiotic, bacterial',
                'requires_prescription': True,
            },
            {
                'name': 'Metformin',
                'generic_name': 'Metformin Hydrochloride',
                'drug_type': 'tablet',
                'manufacturer': 'Sun Pharma',
                'description': 'Used to control blood sugar in type 2 diabetes.',
                'dosage_form': '500mg',
                'categories': 'diabetes, blood sugar',
                'tags': 'diabetes, sugar',
                'requires_prescription': True,
            },
            {
                'name': 'Atorvastatin',
                'generic_name': 'Atorvastatin Calcium',
                'drug_type': 'tablet',
                'manufacturer': 'Pfizer',
                'description': 'Used to lower cholesterol and reduce cardiovascular risk.',
                'dosage_form': '10mg',
                'categories': 'cholesterol, heart',
                'tags': 'cholesterol, statin',
                'requires_prescription': True,
            },
            {
                'name': 'Lisinopril',
                'generic_name': 'Lisinopril',
                'drug_type': 'tablet',
                'manufacturer': 'AstraZeneca',
                'description': 'Used to treat high blood pressure and heart failure.',
                'dosage_form': '10mg',
                'categories': 'blood pressure, hypertension',
                'tags': 'bp, hypertension',
                'requires_prescription': True,
            },
            {
                'name': 'Omeprazole',
                'generic_name': 'Omeprazole',
                'drug_type': 'capsule',
                'manufacturer': 'Dr. Reddy\'s',
                'description': 'Used to treat acid reflux and stomach ulcers.',
                'dosage_form': '20mg',
                'categories': 'acid reflux, stomach',
                'tags': 'reflux, acidity',
                'requires_prescription': False,
            },
            {
                'name': 'Aspirin',
                'generic_name': 'Acetylsalicylic Acid',
                'drug_type': 'tablet',
                'manufacturer': 'Bayer',
                'description': 'Used for pain relief, fever, and as a blood thinner.',
                'dosage_form': '75mg',
                'categories': 'pain, blood thinner, heart',
                'tags': 'pain, heart',
                'requires_prescription': False,
            },
            {
                'name': 'Dolo 650',
                'generic_name': 'Paracetamol',
                'drug_type': 'tablet',
                'manufacturer': 'Micro Labs',
                'description': 'Used for fever and mild to moderate pain relief.',
                'dosage_form': '650mg',
                'categories': 'pain, fever, headache',
                'tags': 'pain, fever',
                'requires_prescription': False,
            },
            {
                'name': 'Ciplox',
                'generic_name': 'Ciprofloxacin',
                'drug_type': 'tablet',
                'manufacturer': 'Cipla',
                'description': 'Antibiotic used to treat bacterial infections.',
                'dosage_form': '500mg',
                'categories': 'antibiotic, infection',
                'tags': 'antibiotic, bacterial',
                'requires_prescription': True,
            },
            {
                'name': 'Azithromycin',
                'generic_name': 'Azithromycin',
                'drug_type': 'tablet',
                'manufacturer': 'Sun Pharma',
                'description': 'Antibiotic used for respiratory and skin infections.',
                'dosage_form': '500mg',
                'categories': 'antibiotic, respiratory',
                'tags': 'antibiotic, infection',
                'requires_prescription': True,
            },
            {
                'name': 'Crocin',
                'generic_name': 'Paracetamol',
                'drug_type': 'tablet',
                'manufacturer': 'GSK',
                'description': 'Used for fever and mild to moderate pain relief.',
                'dosage_form': '500mg',
                'categories': 'pain, fever',
                'tags': 'pain, fever',
                'requires_prescription': False,
            },
            {
                'name': 'Ecosprin',
                'generic_name': 'Aspirin',
                'drug_type': 'tablet',
                'manufacturer': 'USV',
                'description': 'Used as a blood thinner and for pain relief.',
                'dosage_form': '75mg',
                'categories': 'heart, blood thinner',
                'tags': 'heart, aspirin',
                'requires_prescription': False,
            },
            {
                'name': 'Levothyroxine',
                'generic_name': 'Levothyroxine Sodium',
                'drug_type': 'tablet',
                'manufacturer': 'Abbott',
                'description': 'Used to treat hypothyroidism (underactive thyroid).',
                'dosage_form': '50mcg',
                'categories': 'thyroid, hormone',
                'tags': 'thyroid',
                'requires_prescription': True,
            },
            {
                'name': 'Amlodipine',
                'generic_name': 'Amlodipine Besylate',
                'drug_type': 'tablet',
                'manufacturer': 'Pfizer',
                'description': 'Used to treat high blood pressure and chest pain.',
                'dosage_form': '5mg',
                'categories': 'blood pressure, heart',
                'tags': 'bp, hypertension',
                'requires_prescription': True,
            },
            {
                'name': 'Pantoprazole',
                'generic_name': 'Pantoprazole',
                'drug_type': 'tablet',
                'manufacturer': 'Dr. Reddy\'s',
                'description': 'Used to treat GERD and stomach ulcers.',
                'dosage_form': '40mg',
                'categories': 'acid reflux, stomach',
                'tags': 'reflux, acidity',
                'requires_prescription': False,
            },
            {
                'name': 'Montair LC',
                'generic_name': 'Montelukast + Levocetirizine',
                'drug_type': 'tablet',
                'manufacturer': 'Cipla',
                'description': 'Used for allergy and asthma symptoms.',
                'dosage_form': '10mg + 5mg',
                'categories': 'allergy, asthma',
                'tags': 'allergy, asthma',
                'requires_prescription': True,
            },
            {
                'name': 'Dexona',
                'generic_name': 'Dexamethasone',
                'drug_type': 'tablet',
                'manufacturer': 'Zydus',
                'description': 'Corticosteroid used for inflammation and allergies.',
                'dosage_form': '0.5mg',
                'categories': 'steroid, inflammation',
                'tags': 'steroid, allergy',
                'requires_prescription': True,
            },
            {
                'name': 'Glucomet',
                'generic_name': 'Metformin',
                'drug_type': 'tablet',
                'manufacturer': 'USV',
                'description': 'Used to control blood sugar in type 2 diabetes.',
                'dosage_form': '500mg SR',
                'categories': 'diabetes, blood sugar',
                'tags': 'diabetes, sugar',
                'requires_prescription': True,
            },
            {
                'name': 'Zincovit',
                'generic_name': 'Zinc + Vitamin C + Vitamin D',
                'drug_type': 'tablet',
                'manufacturer': 'Cipla',
                'description': 'Multivitamin supplement for immunity.',
                'dosage_form': 'Tablet',
                'categories': 'vitamins, immunity',
                'tags': 'vitamins, supplement',
                'requires_prescription': False,
            },
            {
                'name': 'Pudin Hara',
                'generic_name': 'Menthol + Peppermint Oil',
                'drug_type': 'syrup',
                'manufacturer': 'Dabur',
                'description': 'Ayurvedic medicine for stomach pain and digestion.',
                'dosage_form': '15ml',
                'categories': 'digestion, stomach',
                'tags': 'ayurvedic, digestion',
                'requires_prescription': False,
            },
        ]

        created_count = 0
        updated_count = 0

        for medicine_data in medicines:
            try:
                # Check if medicine already exists
                drug, created = Drug.objects.get_or_create(
                    name=medicine_data['name'],
                    defaults={
                        'generic_name': medicine_data['generic_name'],
                        'drug_type': medicine_data['drug_type'],
                        'manufacturer': medicine_data['manufacturer'],
                        'description': medicine_data['description'],
                        'dosage_form': medicine_data['dosage_form'],
                        'categories': medicine_data['categories'],
                        'tags': medicine_data['tags'],
                        'requires_prescription': medicine_data['requires_prescription'],
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Created: {medicine_data["name"]}'))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'• Skipped: {medicine_data["name"]} (already exists)'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error creating {medicine_data["name"]}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'✅ Seeding Complete!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Created: {created_count} medicines'))
        self.stdout.write(self.style.SUCCESS(f'📊 Existing: {updated_count} medicines'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total: {created_count + updated_count} medicines in database'))
        self.stdout.write(self.style.SUCCESS('='*50))
