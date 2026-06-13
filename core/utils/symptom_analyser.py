import json
import re
from datetime import datetime
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class SymptomAnalyzer:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"
    
    def predict_disease(self, symptoms_text):
        """
        Predict disease from symptoms text and return structured JSON
        """
        
        system_prompt = """You are a medical symptom analysis AI. Your job is to analyze symptoms and provide structured, JSON-only responses. 
        You must always respond with valid JSON only, no other text. Be conservative with confidence scores. 
        Always include a medical disclaimer."""
        
        user_prompt = f"""
        Analyze these symptoms and predict the most likely disease.
        
        Symptoms: {symptoms_text}
        
        Respond with EXACTLY this JSON structure (no other text):
        
        {{
            "predicted_disease": "name of the disease",
            "confidence_score": 85,
            "reasoning": "brief explanation of why you think this",
            "severity": "Mild/Moderate/Severe",
            "common_symptoms_matched": ["symptom1", "symptom2", "symptom3"],
            "suggested_drugs": ["drug1", "drug2"],
            "disclaimer": "This is not a medical diagnosis. Please consult a doctor."
        }}
        
        Rules:
        - confidence_score: integer between 0-100 (be conservative)
        - severity: one of Mild, Moderate, or Severe
        - common_symptoms_matched: list of 2-4 symptoms from the input
        - suggested_drugs: list of 2 common medications for this condition
        - Keep reasoning concise (1-2 sentences)
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=500
            )
            
            response_text = chat_completion.choices[0].message.content
            json_text = self._extract_json(response_text)
            result = json.loads(json_text)
            
            result['original_symptoms'] = symptoms_text
            result['timestamp'] = datetime.now().isoformat()
            result['model_used'] = self.model
            
            return result
            
        except json.JSONDecodeError as e:
            return self._get_fallback_response(symptoms_text, f"JSON parsing error: {str(e)}")
        except Exception as e:
            return self._get_fallback_response(symptoms_text, str(e))
    
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
            "disclaimer": "Please consult a healthcare professional for proper diagnosis",
            "original_symptoms": symptoms_text,
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "model_used": self.model
        }


# Singleton instance
symptom_analyzer = SymptomAnalyzer()
