"""
Package the Lambda bundle and push it to AWS.

Credentials come from the standard AWS chain (env vars, ~/.aws/credentials, or
an instance role) — run `aws configure` if this can't find them. Nothing secret
belongs in this file.
"""

import os
import shutil
import sys

import boto3
from dotenv import load_dotenv

FUNCTION_NAME = "abtalks-api"
REGION = "us-east-1"

load_dotenv()

print("Zipping package...")
if os.path.exists("deployment.zip"):
    os.remove("deployment.zip")

shutil.make_archive("deployment", "zip", "package")
print("Zip created successfully.")

print("Uploading to Lambda...")
client = boto3.client("lambda", region_name=REGION)

with open("deployment.zip", "rb") as f:
    zip_bytes = f.read()

try:
    response = client.update_function_code(
        FunctionName=FUNCTION_NAME,
        ZipFile=zip_bytes,
    )
    print("Code uploaded.", response["CodeSize"])

    waiter = client.get_waiter("function_updated_v2")
    waiter.wait(FunctionName=FUNCTION_NAME)

    # Secrets live on the function's configuration, not inside the bundle.
    env_vars = {}
    for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        value = os.getenv(key)
        if value:
            env_vars[key] = value

    if not env_vars.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY is not set locally — refusing to deploy "
              "a function that has no key to call.")
        sys.exit(1)

    # Increase timeout and memory for slower fallback LLMs
    client.update_function_configuration(
        FunctionName=FUNCTION_NAME,
        Timeout=180,
        MemorySize=512,
        Environment={"Variables": env_vars},
    )
    print(f"SUCCESS: Timeout 180s, env vars set ({', '.join(sorted(env_vars))})")
except Exception as e:
    print("ERROR", str(e))
    sys.exit(1)
