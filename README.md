# Retail Fraud Detection — MLOps Pipeline

An end-to-end MLOps pipeline for real-time fraud detection in retail transactions. 
A Random Forest classifier is trained, tracked, containerised and deployed as a 
REST API on AWS with full CI/CD automation and live monitoring.

---

## Architecture

<img width="1853" height="2745" alt="mermaid-diagram-2026-05-27-215315" src="https://github.com/user-attachments/assets/45211f55-0023-43d3-af1f-2253bd08e04c" />

---

## Tech Stack

| Category | Tools |
|---|---|
| Data & Storage | AWS S3, boto3 |
| Modelling | scikit-learn (Random Forest) |
| Experiment Tracking | MLflow |
| API Serving | FastAPI, Uvicorn |
| Containerisation | Docker |
| Container Registry | AWS ECR |
| Cloud Infrastructure | AWS EC2 (t3.micro), Amazon Linux 2023 |
| CI/CD | GitHub Actions |
| Monitoring & Alerting | AWS CloudWatch, AWS SNS |
| Language | Python 3.13 |
| Region | eu-west-2 (London) |

---

## Project Structure

```
retail-fraud-detection-mlops/
├── .github/
│   └── workflows/
│       └── deploy.yml         # GitHub Actions CI/CD pipeline
├── raw/                       # gitignored — raw data
├── processed/                 # gitignored — train/test splits
├── mlruns/                    # gitignored — MLflow experiment tracking
├── models/                    # gitignored — local model artefacts
├── data-ingestion.py          # pulls raw CSV from S3
├── data-preprocessing.py      # cleans, encodes and splits data
├── data-training.py           # trains Random Forest, logs to MLflow
├── app.py                     # FastAPI serving app
├── requirements.txt           # serving dependencies
├── Dockerfile                 # container build instructions
├── .dockerignore              # excludes unnecessary files from image
├── .gitignore                 # excludes data, models, secrets
├── commands.md                # full deployment runbook
└── README.md
```

---

## Pipeline Overview

### 1. Data Ingestion
Raw retail transaction data (100k rows) is stored in S3 and pulled 
locally using boto3 for preprocessing and training.

### 2. Preprocessing
Categorical encoding, feature scaling and train/test splitting. 
Five leaking flag columns were identified and dropped:
```
unusual_amount_flag
unusual_location_flag
velocity_flag
previous_fraud_flag
high_risk_device_flag
```
These columns were derived directly from the fraud label, meaning 
including them would give the model information it would never have 
at prediction time in production.

### 3. Experiment Tracking
Random Forest trained and evaluated with MLflow tracking:

| Metric | Score |
|---|---|
| AUC | 0.90 |
| Accuracy | 0.79 |
| F1 (fraud class) | 0.78 |
| F1 (legitimate class) | 0.80 |

### 4. Containerisation
Model exported as `rf_model.pkl` and `feature_columns.pkl` to S3. 
FastAPI app loads the model from S3 at container startup. 
Docker image built for linux/amd64 to match EC2 architecture.

### 5. Deployment
Docker image pushed to AWS ECR. EC2 instance pulls the image and 
runs the container on port 8000. IAM role attached to EC2 for 
secure access to ECR and S3 — no credentials stored on the server.

### 6. CI/CD
Every push to main triggers GitHub Actions to automatically:
- Build a fresh linux/amd64 Docker image
- Push to ECR
- SSH into EC2 and redeploy the container

### 7. Monitoring
CloudWatch agent ships container logs to a CloudWatch log group 
with 30 day retention. Two alarms configured:
- Health check alarm — fires if EC2 instance fails status checks
- Memory alarm — fires if memory usage exceeds 80%

Both alarms send email notifications via SNS.

---

## API Documentation

### Base URL
```
http://<ec2-public-ip>:8000
```

### Endpoints

#### GET /health
Returns API and model status.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

#### POST /predict
Accepts transaction features and returns a fraud prediction.

**Request body:**
```json
{
  "transaction_amount": 250.00,
  "customer_age": 34,
  "account_age_days": 120,
  "transaction_hour": 14,
  "is_weekend": 0,
  "transaction_count_1h": 3,
  "unique_merchants_1d": 2,
  "avg_transaction_amount_7d": 180.00,
  "transaction_amount_zscore": 1.2,
  "is_international": 0,
  "payment_method_encoded": 1
}
```

**Response:**
```json
{
  "prediction": 0,
  "fraud_probability": 0.1823,
  "label": "LEGITIMATE",
  "status": "ok"
}
```

#### Interactive Docs
```
http://<ec2-public-ip>:8000/docs
```

---

## Design Decisions and Alternatives Considered

### EC2 + ECR over AWS SageMaker
SageMaker provides a fully managed ML deployment platform but has 
no free tier for endpoints (~$50-80/month minimum). EC2 with Docker 
provides more transparent infrastructure, transferable skills across 
cloud providers, and runs within free tier limits. SageMaker would 
be evaluated for a production system requiring managed autoscaling 
and built-in A/B testing.

### MLflow over SageMaker Experiment Tracking
MLflow is cloud agnostic and integrates with any deployment target. 
SageMaker experiment tracking creates vendor lock-in and adds cost. 
For a single-model pipeline MLflow provides all required functionality.

### Model in S3 over Baking into Docker Image
Initially the model was baked into the Docker image via COPY in the 
Dockerfile. This was changed so the container downloads the model 
from S3 at startup. This means retraining only requires uploading 
a new pkl file to S3 — no Docker rebuild or redeployment needed.

### IAM Role over AWS Credentials on EC2
EC2 is granted permissions via an attached IAM role rather than 
storing AWS credentials on the server. Credentials on a server 
are a common cause of AWS account breaches. IAM roles issue 
temporary tokens automatically with no credentials ever touching 
the instance.

### Joblib over Pickle
Joblib is scikit-learn's recommended serialisation library, 
optimised for numpy arrays inside model objects. The scikit-learn 
version is pinned in requirements.txt to prevent deserialisation 
errors from version mismatches between training and serving 
environments.

---

## Known Limitations and Future Improvements

### Current Limitations
```
Memory pressure      t3.micro has 1GB RAM — memory alarm fires 
                     at 80% under normal load. A t3.small (2GB) 
                     would resolve this in production.

Manual retraining    New model versions require manually uploading 
                     pkl files to S3. This is a human step in an 
                     otherwise automated pipeline.

No HTTPS             API runs on HTTP port 8000. Production would 
                     require a load balancer with SSL termination.

No authentication    The /predict endpoint is publicly accessible 
                     with no API key or auth layer.
```

### Future Improvements
```
Airflow pipeline     Scheduled retraining DAG that automatically 
                     trains on new data, evaluates performance and 
                     uploads the new model to S3 if AUC improves.

SageMaker            Evaluate managed endpoints for production 
                     traffic with autoscaling requirements.

Terraform            Replace manual CLI deployment with 
                     Infrastructure as Code for fully reproducible 
                     environment setup.

CI testing           Add pytest step to GitHub Actions before 
                     deployment — failed tests block deployment 
                     rather than relying on post-deploy health checks.
```

---

## Deployment Runbook

See [commands.md](commands.md) for the complete step-by-step 
deployment commands including teardown instructions.

---

## Teardown

When finished, run the teardown commands in commands.md to 
terminate all AWS resources and avoid ongoing charges. 
Particularly important — release the Elastic IP address 
which incurs charges even when not attached to a running instance.
