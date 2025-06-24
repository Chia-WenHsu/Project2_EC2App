## 此程式為 項目2 APP 層程式

1. git clone 
2. pip install requirements


SQS_QUEUE_URL = 'https://sqs.ap-northeast-2.amazonaws.com/530751794867/project2-request-q'
RESPONSE_QUEUE_URL = 'https://sqs.ap-northeast-2.amazonaws.com/530751794867/project2-response-q'
S3_BUCKET_NAME_input = 'nicoproject2input'
S3_BUCKET_NAME_output = 'nicoproject2output'
REGION = "ap-northeast-2"
AMI_ID = "ami-011dae5f0fc7d1a64"
INSTANCE_TYPE = "t2.micro"
KEY_NAME = "nico_projectKey"
SECURITY_GROUP_IDS = ["sg-06130228d6c599dd4"]


3. SERVICE SETTING

```
[Unit]
Description=Image Classification Worker
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Project2_EC2App
ExecStart=/home/ubuntu/Project2_EC2App/venv/bin/python3 /home/ubuntu/Project2_EC2App/worker2.py
Restart=no

[Install]
WantedBy=multi-user.target

```