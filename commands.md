# Deployment Commands

## Docker

### Build image

````bash
docker buildx build \
  --platform linux/amd64 \
  -t fraud-detection-api:latest \
  --load \
  .
````

### Run locally

````bash
docker run -p 8000:8000 fraud-detection-api
````

---

## AWS Deployment

### Create ECR repository

````bash
aws ecr create-repository \
  --repository-name fraud-detection-api \
  --region eu-west-2
````

### Authenticate Docker to ECR

````bash
aws ecr get-login-password --region eu-west-2 | docker login \
  --username AWS \
  --password-stdin \
  <account-id>.dkr.ecr.eu-west-2.amazonaws.com
````

### Tag and push image to ECR

````bash
docker tag fraud-detection-api:latest \
  <account-id>.dkr.ecr.eu-west-2.amazonaws.com/fraud-detection-api:latest

docker push \
  <account-id>.dkr.ecr.eu-west-2.amazonaws.com/fraud-detection-api:latest
````

### Create key pair

````bash
aws ec2 create-key-pair \
  --key-name fraud-detection-key \
  --region eu-west-2 \
  --query 'KeyMaterial' \
  --output text > fraud-detection-key.pem

chmod 400 fraud-detection-key.pem
````

### Create security group

````bash
aws ec2 create-security-group \
  --group-name fraud-detection-sg \
  --description "Security group for fraud detection API" \
  --region eu-west-2

aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region eu-west-2

aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0 \
  --region eu-west-2
````

### Get latest Amazon Linux 2023 AMI

````bash
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" \
  "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text \
  --region eu-west-2
````

### Launch EC2 instance

````bash
aws ec2 run-instances \
  --image-id <ami-id> \
  --instance-type t3.micro \
  --key-name fraud-detection-key \
  --security-group-ids <sg-id> \
  --region eu-west-2 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=fraud-detection-api}]'
````

### Create and attach IAM role

````bash
aws iam create-role \
  --role-name fraud-detection-ec2-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name fraud-detection-ec2-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam create-instance-profile \
  --instance-profile-name fraud-detection-ec2-profile

aws iam add-role-to-instance-profile \
  --instance-profile-name fraud-detection-ec2-profile \
  --role-name fraud-detection-ec2-role

aws ec2 associate-iam-instance-profile \
  --instance-id <instance-id> \
  --iam-instance-profile Name=fraud-detection-ec2-profile \
  --region eu-west-2
````

### SSH into EC2

````bash
ssh -i fraud-detection-key.pem ec2-user@<public-ip>
````

### On EC2 — install Docker

````bash
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user
newgrp docker
````

### On EC2 — authenticate, pull and run

````bash
aws ecr get-login-password --region eu-west-2 | docker login \
  --username AWS \
  --password-stdin \
  <account-id>.dkr.ecr.eu-west-2.amazonaws.com

docker pull <account-id>.dkr.ecr.eu-west-2.amazonaws.com/fraud-detection-api:latest

docker run -d \
  -p 8000:8000 \
  --name fraud-api \
  --restart unless-stopped \
  <account-id>.dkr.ecr.eu-west-2.amazonaws.com/fraud-detection-api:latest
````

### Verify

````bash
docker ps
curl http://localhost:8000/health
````

---

## Model Management

### Upload model files to S3

```bash
aws s3 cp models/rf_model.pkl \
  s3://<bucket-name>/models/rf_model.pkl

aws s3 cp models/feature_columns.pkl \
  s3://<bucket-name>/models/feature_columns.pkl
```

### Verify S3 upload

```bash
aws s3 ls s3://<bucket-name>/models/
```

---

## Instance Management

### Stop instance

```bash
aws ec2 stop-instances \
  --instance-ids <instance-id> \
  --region eu-west-2
```

### Start instance

```bash
aws ec2 start-instances \
  --instance-ids <instance-id> \
  --region eu-west-2
```

### Get current public IP

```bash
aws ec2 describe-instances \
  --instance-ids <instance-id> \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text \
  --region eu-west-2
```

---

## CloudWatch Monitoring

### Create SNS topic for alerts

```bash
aws sns create-topic \
  --name fraud-detection-alerts \
  --region eu-west-2
```

### Subscribe email to SNS topic

```bash
aws sns subscribe \
  --topic-arn <topic-arn> \
  --protocol email \
  --notification-endpoint <your-email> \
  --region eu-west-2
```

### Create CloudWatch log group

```bash
aws logs create-log-group \
  --log-group-name /fraud-detection/api \
  --region eu-west-2
```

### Set log retention policy

```bash
aws logs put-retention-policy \
  --log-group-name /fraud-detection/api \
  --retention-in-days 30
```

### On EC2 — install and configure CloudWatch agent

```bash
sudo yum install -y amazon-cloudwatch-agent

sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s
```

### Verify CloudWatch agent status

```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a status
```

### Create health check alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fraud-api-health-check \
  --alarm-description "Alerts when fraud detection API is down" \
  --metric-name StatusCheckFailed \
  --namespace AWS/EC2 \
  --statistic Maximum \
  --dimensions Name=InstanceId,Value=<instance-id> \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions <topic-arn> \
  --ok-actions <topic-arn> \
  --region eu-west-2
```

### Create memory alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fraud-api-memory-high \
  --alarm-description "Alerts when memory usage exceeds 80 percent" \
  --metric-name mem_used_percent \
  --namespace CWAgent \
  --statistic Average \
  --dimensions Name=InstanceId,Value=<instance-id> \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions <topic-arn> \
  --region eu-west-2
```

---

## Teardown — Run When Project Is Complete

```bash
aws ec2 terminate-instances \
  --instance-ids <instance-id> \
  --region eu-west-2

aws ec2 release-address \
  --allocation-id <allocation-id> \
  --region eu-west-2

aws ecr delete-repository \
  --repository-name fraud-detection-api \
  --force \
  --region eu-west-2

aws logs delete-log-group \
  --log-group-name /fraud-detection/api \
  --region eu-west-2

aws sns delete-topic \
  --topic-arn <topic-arn> \
  --region eu-west-2
```