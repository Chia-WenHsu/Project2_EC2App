import boto3
import subprocess
import time
import json
from datetime import datetime
from botocore.exceptions import ClientError

SQS_QUEUE_URL = 'https://sqs.ap-northeast-2.amazonaws.com/530751794867/project2-request-q'
RESPONSE_QUEUE_URL = 'https://sqs.ap-northeast-2.amazonaws.com/530751794867/project2-response-q'
S3_BUCKET_NAME_input = 'nicoproject2input'
S3_BUCKET_NAME_output = 'nicoproject2output'


# 初始化 AWS 客戶端
sqs = boto3.client('sqs', region_name='ap-northeast-2')
s3 = boto3.client('s3', region_name='ap-northeast-2')

print("Worker started, listening to SQS...")

sw = True

while sw:
    # 從 SQS 取得訊息
    response = sqs.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    messages = response.get("Messages", [])
    if not messages:
        continue
    
    
    for message in messages:
        

        try:
            receipt_handle = message["ReceiptHandle"]
        
            body = json.loads(message["Body"])
            image_key = body["s3Key"]
            request_id = body["requestId"]

            print(f" 取得霄錫: {image_key}")

            # 下載圖檔
            s3.download_file(S3_BUCKET_NAME_input, image_key, "input.jpg")
            print(f" 下載 {image_key} to input.jpg")

            result = subprocess.check_output(["/home/ubuntu/Project2_EC2App/venv/bin/python3", "image_classification.py", "input.jpg"] , timeout=60).decode().strip()
            print(f" 結果: {result}")

            image_basename = image_key.rsplit(".", 1)[0]
            label = result.split(",")[-1].strip()

            # 將結果存回 S3（以 test_0 -> test_0: bathtub 形式）

            today_str = datetime.now().strftime('%Y%m%d')
            daily_key = f"{today_str}_results.txt"

            try:
                existing_obj = s3.get_object(Bucket=S3_BUCKET_NAME_output, Key=daily_key)
                existing_content = existing_obj["Body"].read().decode()
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    existing_content = ""
                else:
                    raise

            new_line = f"{image_basename},{label}\n"
            updated_content = existing_content + new_line

            s3.put_object(
                Bucket=S3_BUCKET_NAME_output,
                Key=daily_key,
                Body=updated_content
            )

            print(f"存取結果到 S3: ({image_basename}, {label})")

            # 發送結果到回應佇列
            response_message = f"{image_basename},{result}"
            sqs.send_message(
                QueueUrl=RESPONSE_QUEUE_URL,
                MessageBody=response_message
            )
            print(f"發送結果到 SQS: {response_message}")

            # 刪除已處理訊息
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            print("刪除處理請求\n")
            
        except subprocess.TimeoutExpired:
            print(" Timeout: inference took too long. Skipping this task.")
            sw = False

        except Exception as e:
            print(f" Unexpected error: {str(e)}. Stopping worker.")
            sw = False
            
        
        time.sleep(1)

    

    
