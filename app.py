from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib
import boto3
import tempfile

app = FastAPI(title="Retail Fraud Detection API", version="0.1")


def load_model_from_s3():
    s3 = boto3.client("s3", region_name="eu-west-2")
    bucket = "fraud-detection-mlops-aws"

    with tempfile.NamedTemporaryFile() as model_file:
        s3.download_fileobj(bucket, "models/rf_model.pkl", model_file)
        model_file.seek(0)
        loaded_model = joblib.load(model_file.name)

    with tempfile.NamedTemporaryFile() as cols_file:
        s3.download_fileobj(bucket, "models/feature_columns.pkl", cols_file)
        cols_file.seek(0)
        loaded_columns = joblib.load(cols_file.name)

    return loaded_model, loaded_columns


model, feature_columns = load_model_from_s3()


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
