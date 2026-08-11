import os
import shutil
import boto3
import sys

print("Zipping package...")
if os.path.exists("deployment.zip"):
    os.remove("deployment.zip")

shutil.make_archive("deployment", "zip", "package")
print("Zip created successfully.")

print("Uploading to Lambda...")
client = boto3.client(
    'lambda', 
    region_name='us-east-1',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
)

with open('deployment.zip', 'rb') as f:
    zip_bytes = f.read()

try:
    response = client.update_function_code(
        FunctionName='abtalks-api',
        ZipFile=zip_bytes
    )
    print("Code uploaded.", response['CodeSize'])
    
    # Increase timeout and memory for slower fallback LLMs
    client.update_function_configuration(
        FunctionName='abtalks-api',
        Timeout=180,
        MemorySize=512
    )
    print("SUCCESS: Timeout increased to 180s")
except Exception as e:
    print("ERROR", str(e))
    sys.exit(1)
