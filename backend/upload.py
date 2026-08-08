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
    # Ensure you have your AWS credentials configured in ~/.aws/credentials
    # or as environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
)

with open('deployment.zip', 'rb') as f:
    zip_bytes = f.read()

try:
    response = client.update_function_code(
        FunctionName='abtalks-api',
        ZipFile=zip_bytes
    )
    print("SUCCESS", response['CodeSize'])
except Exception as e:
    print("ERROR", str(e))
    sys.exit(1)
