import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
import mlflow
import mlflow.sklearn
import os
import joblib


def train():
    X_train = pd.read_csv('processed/X_train.csv')
    X_test = pd.read_csv('processed/X_test.csv')
    y_train = pd.read_csv('processed/y_train.csv').squeeze()
    y_test = pd.read_csv('processed/y_test.csv').squeeze()

    print('Data loaded successfully')
    print(f'Training size: {X_train.shape}')
    print(f'Test size: {X_test.shape}')

    rf_model = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
    rf_model.fit(X_train, y_train)
    print('Random Forest Model Trained Successfully')

    y_pred = rf_model.predict(X_test)
    y_prob = rf_model.predict_proba(X_test)[:, 1]

    print(classification_report(y_test, y_pred))
    print(f"AUC Score: {roc_auc_score(y_test, y_prob)}")

    with mlflow.start_run():
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("class_weight", "balanced")
        mlflow.log_metric("auc", roc_auc_score(y_test, y_prob))
        mlflow.sklearn.log_model(rf_model, name="model")
        print("MLflow logging complete")

    os.makedirs('models', exist_ok=True)
    joblib.dump(rf_model, 'models/rf_model.pkl')
    joblib.dump(list(X_train.columns), 'models/feature_columns.pkl')
    print("Model exported to models/rf_model.pkl")
    print("Feature columns exported to models/feature_columns.pkl")

if __name__ == '__main__':
    train()
