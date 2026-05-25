import boto3
import os

BUCKET_NAME = 'fraud-detection-mlops-aws'
S3_KEY = 'raw/retail_fraud_detection_100k.csv'
LOCAL_PATH = 'raw/retail_fraud_detection_100k.csv'

# Downloading file from AWS S3
def download_file():
    s3 = boto3.client('s3')
    os.makedirs('raw', exist_ok=True)
    print(f'Downloading {S3_KEY} from bucket: {BUCKET_NAME}')
    s3.download_file(BUCKET_NAME, S3_KEY, LOCAL_PATH)
    print(f'File saved to {LOCAL_PATH}')


if __name__ == '__main__':
    download_file()
