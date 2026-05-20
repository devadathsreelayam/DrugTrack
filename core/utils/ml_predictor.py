import joblib
import numpy as np
import os
from pathlib import Path

# Get the base directory (where manage.py is)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

MODEL_PATH = BASE_DIR / 'drug_decission_tree.pkl'
SCALER_PATH = BASE_DIR / 'drug_scaler.pkl'

DRUG_MAPPING = {
    0: "drugA",
    1: "drugB", 
    2: "drugC",
    3: "drugX",
    4: "drugY"
}

SEX_MAPPING = {"F": 0, "M": 1}
BP_MAPPING = {"HIGH": 0, "LOW": 1, "NORMAL": 2}
CHOL_MAPPING = {"HIGH": 0, "NORMAL": 1}

class DrugPredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.load_model()
    
    def load_model(self):
        try:
            if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
                self.model = joblib.load(MODEL_PATH)
                self.scaler = joblib.load(SCALER_PATH)
                print("Model and scaler loaded successfully")
            else:
                print(f"Model or scaler not found at {MODEL_PATH}")
        except Exception as e:
            print(f"Error loading model: {e}")
    
    def predict(self, age, sex, bp, cholesterol, na_to_k):
        if self.model is None:
            return "drugA", 0.85  # Fallback
        
        try:
            # Preprocess
            sex_encoded = SEX_MAPPING.get(sex.upper())
            bp_encoded = BP_MAPPING.get(bp.upper())
            chol_encoded = CHOL_MAPPING.get(cholesterol.upper())
            
            if None in [sex_encoded, bp_encoded, chol_encoded]:
                return "drugA", 0.70
            
            # Scale Na_to_K
            na_scaled = self.scaler.transform([[na_to_k]])[0][0]
            
            # Prepare features
            features = np.array([[age, sex_encoded, bp_encoded, chol_encoded, na_scaled]])
            
            # Predict
            prediction_idx = int(self.model.predict(features)[0])
            prediction_drug = DRUG_MAPPING.get(prediction_idx, "Unknown")
            
            # Get confidence (for decision tree, use prediction probability if available)
            confidence = 0.85  # Default, can be improved
            try:
                proba = self.model.predict_proba(features)
                confidence = float(np.max(proba[0]))
            except:
                pass
            
            return prediction_drug, confidence
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return "drugA", 0.70

# Singleton instance
predictor = DrugPredictor()