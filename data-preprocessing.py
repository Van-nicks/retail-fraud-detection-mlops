import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import os


def data_preprocessing():
    df = pd.read_csv('raw/retail_fraud_detection_100k.csv')
    df = df.drop(columns=['transaction_id', 'customer_id', 'transaction_timestamp', 'fraud_risk',
                          'unusual_amount_flag', 'unusual_location_flag', 'velocity_flag',
                          'previous_fraud_flag', 'high_risk_device_flag'])

    categorical_cols = ['payment_method', 'device_type', 'location', 'merchant_category']
    le = LabelEncoder()

    for col in categorical_cols:
        df[col] = le.fit_transform(df[col])

    X = df.drop(columns='fraud_flag')
    y = df['fraud_flag']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    os.makedirs('processed', exist_ok=True)
    X_train.to_csv('processed/X_train.csv', index=False)
    X_test.to_csv('processed/X_test.csv', index=False)
    y_train.to_csv('processed/y_train.csv', index=False)
    y_test.to_csv('processed/y_test.csv', index=False)
    print('Processed data saved successfully')


if __name__ == '__main__':
    data_preprocessing()
