from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib
import os

app = FastAPI(title="Retail Fraud Detection API", version="0.1")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model = joblib.load(os.path.join(BASE_DIR, "models", "rf_model.pkl"))
feature_columns = joblib.load(os.path.join(BASE_DIR, "models", "feature_columns.pkl"))


class TransactionFeatures(BaseModel):
    transaction_amount: float
    payment_method: float
    device_type: float
    location: float
    merchant_category: float
    is_international: float
    transaction_frequency_24h: float
    avg_transaction_amount_7d: float
    failed_transaction_count_24h: float
    account_age_days: float
    multiple_transactions_short_time: float


@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": model is not None}


@app.post("/predict")
def predict(transaction: TransactionFeatures):
    try:
        input_dict = transaction.model_dump()
        input_df = pd.DataFrame([input_dict])[feature_columns]

        pred = model.predict(input_df)[0]
        prob = model.predict_proba(input_df)[0][1]

        return {
            "prediction": int(pred),
            "fraud_probability": round(float(prob), 4),
            "label": "FRAUD" if pred == 1 else "LEGITIMATE",
            "status": "ok",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
