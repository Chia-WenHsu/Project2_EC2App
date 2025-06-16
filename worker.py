# stable_worker_image_classifier

import boto3
import time
import os
import subprocess
import json
import platform

SQS_QUEUE_URL = 'https://sqs.ap-northeast-2.amazonaws.com/530751794867/project2-request-q'
RESPONSE_QUEUE_URL = 'https://sqs.ap-northeast-2.amazonaws.com/530751794867/project2-response-q'
S3_BUCKET_NAME_input = 'nicoproject2input'
S3_BUCKET_NAME_output = 'nicoproject2output'

LOCAL_IMAGE_PATH = 'input.jpg'
RESULTS_FOLDER = 'results/'
MODEL_PATH = '/home/ubuntu/resnet18-f37072fd.pth'

if platform.system() == "Windows":
    MODEL_PATH = "C:\\Users\\a0925\\OneDrive\\桌面\\ASU\\Course\\2025Summer\\CSE546_CloudComputing\\Project\\Project2\\resnet18-f37072fd.pth"
else:
    MODEL_PATH = "/home/ubuntu/resnet18-f37072fd.pth"

# Use credentials only if not on IAM-role EC2
sqs = boto3.client('sqs', region_name='ap-northeast-2')

s3 = boto3.client('s3', region_name='ap-northeast-2')

def ensure_model_cached():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Upload it before running.")

def classify_image(image_path):
    try:
        process = subprocess.run(
            ['python', 'image_classification.py', image_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
        print(" Subprocess finished")
        stdout_output = process.stdout.decode(errors='ignore').strip()
        stderr_output = process.stderr.decode(errors='ignore').strip()

        print(" STDOUT:", stdout_output)
        print(" STDERR:", stderr_output)

        if stdout_output:
            parts = stdout_output.split(',')
            label = parts[1] if len(parts) == 2 else 'unknown'
        else:
            label = 'no_output'

    except subprocess.TimeoutExpired:
        print(" Subprocess timeout after 60 seconds")
        label = "timeout"
    except Exception as e:
        print(f" Subprocess failed: {e}")
        label = "error"
    return label

def excute():
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    ensure_model_cached()
    sw =True
    while sw:
        try:
            response = sqs.receive_message(QueueUrl=SQS_QUEUE_URL,
                                            MaxNumberOfMessages=1,
                                            WaitTimeSeconds=10)

            messages = response.get('Messages', [])
            if not messages:
                continue

            for msg in messages:
                receipt_handle = msg['ReceiptHandle']
                image_key = json.loads(msg['Body'])['s3Key'].strip()
                print(f" Received task: {image_key}")

                s3.download_file(S3_BUCKET_NAME_input, image_key, LOCAL_IMAGE_PATH)
                print(f" Downloaded {image_key} to {LOCAL_IMAGE_PATH}")

                label = classify_image(LOCAL_IMAGE_PATH)

                print(f"Result label: {label}")

                result_key = RESULTS_FOLDER + os.path.splitext(image_key)[0] + '.txt'
                s3.put_object(
                    Bucket=S3_BUCKET_NAME_output,
                    Key=result_key,
                    Body=label.encode('utf-8')
                )

                response_msg = {
                    "image": image_key,
                    "label": label
                }
                sqs.send_message(
                    QueueUrl=RESPONSE_QUEUE_URL,
                    MessageBody=json.dumps(response_msg)
                )

                sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
                print(f" Cleaned up task: {image_key}\n")
                time.sleep(1)
                sw = False
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            sw = False
            time.sleep(5)


if __name__ == '__main__':
    excute()
