import json
import re
from datetime import datetime
from groq import Groq
import os
from dotenv import load_dotenv
from django.contrib.auth import get_user_model

User = get_user_model()
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class SymptomAnalyzer:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"
    
    def predict_disease(self, symptoms_text, user=None):
        """
        Predict disease from symptoms with full user context
        """
        
        # Build comprehensive user context
        user_context = self._build_full_context(user)
        
        system_prompt = """You are an advanced medical AI assistant specialized in symptom analysis and drug recommendations.
        
        Your task is to analyze symptoms with the user's complete medical context and provide:
        1. Most likely disease/condition
        2. Confidence score
        3. Reasoning based on symptoms and context
        4. Severity assessment
        5. Drug recommendations with dosage
        6. Drug interaction warnings
        7. Safety precautions
        
        IMPORTANT RULES:
        - Be conservative with confidence scores
        - Always consider drug interactions with existing medications
        - Suggest dosages based on age, weight, and health conditions
        - Provide alternative drugs if common ones interact with existing meds
        - Always include a medical disclaimer
        - Respond ONLY with valid JSON
        """
        
        user_prompt = f"""
        Analyze these symptoms and provide a comprehensive medical assessment.
        
        Symptoms: {symptoms_text}
        
        Complete User Context:
        {user_context}
        
        Respond with EXACTLY this JSON structure (no other text):
        
        {{
            "predicted_disease": "name of the disease",
            "confidence_score": 75,
            "reasoning": "detailed explanation considering symptoms and user context",
            "severity": "Mild/Moderate/Severe",
            "common_symptoms_matched": ["symptom1", "symptom2", "symptom3"],
            "suggested_drugs": [
                {{
                    "name": "Primary drug",
                    "dosage": "Recommended dosage",
                    "frequency": "How often to take",
                    "duration": "How long to take",
                    "is_alternative": false,
                    "reason": "Why this drug is recommended"
                }},
                {{
                    "name": "Alternative drug",
                    "dosage": "Recommended dosage",
                    "frequency": "How often to take",
                    "duration": "How long to take",
                    "is_alternative": true,
                    "reason": "Alternative because primary may interact with existing meds"
                }}
            ],
            "drug_interactions": [
                {{
                    "drug1": "Existing medication",
                    "drug2": "Suggested drug",
                    "severity": "High/Moderate/Low",
                    "description": "Description of interaction"
                }}
            ],
            "safety_precautions": [
                "Precaution 1",
                "Precaution 2"
            ],
            "when_to_see_doctor": "Clear guidance on when to seek medical help",
            "disclaimer": "This is not a medical diagnosis. Please consult a doctor."
        }}
        
        Rules:
        - confidence_score: 0-100 (be conservative)
        - severity: Mild, Moderate, or Severe
        - If drug interactions exist, suggest alternatives
        - Consider age, weight, chronic conditions for dosage
        - List at least 2 safety precautions
        - Include 2-4 common symptoms matched
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=900
            )
            
            response_text = chat_completion.choices[0].message.content
            json_text = self._extract_json(response_text)
            result = json.loads(json_text)
            
            # Add metadata
            result['original_symptoms'] = symptoms_text
            result['timestamp'] = datetime.now().isoformat()
            result['model_used'] = self.model
            result['user_context_used'] = True
            
            return result
            
        except json.JSONDecodeError as e:
            return self._get_fallback_response(symptoms_text, f"JSON parsing error: {str(e)}")
        except Exception as e:
            return self._get_fallback_response(symptoms_text, str(e))
    
    def _build_full_context(self, user):
        """Build comprehensive user context from all available data"""
        if not user or not user.is_authenticated:
            return "No user context available. New user."
        
        context_parts = []
        
        # 1. Demographics
        context_parts.append("=" * 40)
        context_parts.append("PATIENT DEMOGRAPHICS")
        context_parts.append("=" * 40)
        context_parts.append(f"Age: {user.age if user.age else 'Not provided'}")
        context_parts.append(f"Gender: {user.gender if user.gender else 'Not provided'}")
        context_parts.append(f"Username: {user.username}")
        
        # 2. Health Profile
        health_profile = getattr(user, 'health_profile', None)
        if health_profile:
            context_parts.append("\n" + "=" * 40)
            context_parts.append("HEALTH PROFILE")
            context_parts.append("=" * 40)
            if health_profile.bp:
                context_parts.append(f"• Blood Pressure: {health_profile.bp}")
            if health_profile.cholesterol:
                context_parts.append(f"• Cholesterol: {health_profile.cholesterol}")
            if health_profile.blood_sugar:
                context_parts.append(f"• Blood Sugar: {health_profile.blood_sugar}")
            if health_profile.weight:
                context_parts.append(f"• Weight: {health_profile.weight} kg")
            if health_profile.height:
                context_parts.append(f"• Height: {health_profile.height} m")
            if health_profile.bmi:
                context_parts.append(f"• BMI: {health_profile.bmi} ({health_profile.bmi_category})")
            if health_profile.allergies:
                context_parts.append(f"• Allergies: {health_profile.allergies}")
            if health_profile.chronic_conditions:
                context_parts.append(f"• Chronic Conditions: {health_profile.chronic_conditions}")
        else:
            context_parts.append("\n• No health profile data available")
        
        # 3. Current Medications
        medications = user.medications.all()
        if medications:
            context_parts.append("\n" + "=" * 40)
            context_parts.append("CURRENT MEDICATIONS")
            context_parts.append("=" * 40)
            for med in medications:
                context_parts.append(f"• {med.medication_name}")
        else:
            context_parts.append("\n• No current medications recorded")
        
        # 4. Recent Prescriptions (last 5)
        recent_prescriptions = user.prescriptions.all().order_by('-created_at')[:5]
        if recent_prescriptions:
            context_parts.append("\n" + "=" * 40)
            context_parts.append("RECENT PRESCRIPTIONS (Last 5)")
            context_parts.append("=" * 40)
            for pres in recent_prescriptions:
                meds = pres.get_medicine_list()
                context_parts.append(f"• {pres.prescribed_date}: {pres.diagnosed_disease}")
                if meds:
                    context_parts.append(f"  Prescribed: {', '.join(meds)}")
                if pres.doctor_name:
                    context_parts.append(f"  Doctor: {pres.doctor_name}")
        else:
            context_parts.append("\n• No recent prescriptions")
        
        # 5. Recent Symptom History (last 5 predictions)
        recent_predictions = user.symptom_predictions.all().order_by('-created_at')[:5]
        if recent_predictions:
            context_parts.append("\n" + "=" * 40)
            context_parts.append("RECENT SYMPTOM HISTORY")
            context_parts.append("=" * 40)
            for pred in recent_predictions:
                context_parts.append(f"• {pred.created_at.strftime('%Y-%m-%d')}: {pred.predicted_disease}")
                context_parts.append(f"  Confidence: {pred.confidence_score}%, Severity: {pred.severity}")
                context_parts.append(f"  Symptoms: {pred.symptoms[:100]}...")
        else:
            context_parts.append("\n• No previous symptom analyses")
        
        # 6. Health Summary
        context_parts.append("\n" + "=" * 40)
        context_parts.append("HEALTH SUMMARY")
        context_parts.append("=" * 40)
        context_parts.append(f"Total Prescriptions: {user.prescriptions.count()}")
        context_parts.append(f"Total Symptom Analyses: {user.symptom_predictions.count()}")
        context_parts.append(f"Total Medications: {user.medications.count()}")
        
        return "\n".join(context_parts)
    
    def _extract_json(self, text):
        code_block_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1)
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group()
        
        return text
    
    def _get_fallback_response(self, symptoms_text, error_message):
        return {
            "predicted_disease": "Unable to determine",
            "confidence_score": 0,
            "reasoning": f"Analysis encountered an error: {error_message}",
            "severity": "Unknown",
            "common_symptoms_matched": [],
            "suggested_drugs": [],
            "drug_interactions": [],
            "safety_precautions": ["Please consult a healthcare professional"],
            "when_to_see_doctor": "Please consult a doctor immediately",
            "disclaimer": "Please consult a healthcare professional for proper diagnosis",
            "original_symptoms": symptoms_text,
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "model_used": self.model
        }


# Singleton instance
symptom_analyzer = SymptomAnalyzer()
