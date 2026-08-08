"""
Standalone script to initialize the DynamoDB InterviewSessions table.

Usage:
    python init_db.py

Supports both local DynamoDB (via DYNAMODB_ENDPOINT_URL) and AWS-hosted DynamoDB.
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

TABLE_NAME = "InterviewSessions"
CANDIDATE_TABLE = "CandidateData"


def get_dynamodb_client():
    """Create a DynamoDB client from environment configuration."""
    endpoint_url = os.getenv("DYNAMODB_ENDPOINT_URL")
    region = os.getenv("AWS_REGION", "us-east-1")

    kwargs = {
        "region_name": region,
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "local"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
    }

    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    return boto3.client("dynamodb", **kwargs)


def create_table(client):
    """
    Create the InterviewSessions DynamoDB table.

    Schema:
        - Partition Key: session_id (String)
    """
    try:
        response = client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "session_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"✅ Table '{TABLE_NAME}' created successfully.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"ℹ️  Table '{TABLE_NAME}' already exists. Skipping creation.")
        else:
            print(f"❌ Error creating table: {e.response['Error']['Message']}")
            return False

    try:
        response2 = client.create_table(
            TableName=CANDIDATE_TABLE,
            KeySchema=[{"AttributeName": "candidate_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "candidate_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"✅ Table '{CANDIDATE_TABLE}' created successfully.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"ℹ️  Table '{CANDIDATE_TABLE}' already exists. Skipping creation.")
        else:
            print(f"❌ Error creating table {CANDIDATE_TABLE}: {e.response['Error']['Message']}")
            return False

    return True


def verify_table(client):
    """Verify the table exists and is active."""
    try:
        response = client.describe_table(TableName=TABLE_NAME)
        status = response["Table"]["TableStatus"]
        item_count = response["Table"]["ItemCount"]
        print(f"\n📋 Table Verification:")
        print(f"   Name:       {TABLE_NAME}")
        print(f"   Status:     {status}")
        print(f"   Item Count: {item_count}")
        print(f"   Key Schema: session_id (HASH/String)")
        return status == "ACTIVE"
    except ClientError as e:
        print(f"❌ Could not verify table: {e.response['Error']['Message']}")
        return False


def main():
    print("=" * 50)
    print("  DynamoDB Table Initializer")
    print("=" * 50)

    endpoint = os.getenv("DYNAMODB_ENDPOINT_URL", "AWS Cloud")
    print(f"\n🔗 Endpoint: {endpoint}")
    print(f"🌍 Region:   {os.getenv('AWS_REGION', 'us-east-1')}\n")

    client = get_dynamodb_client()

    if create_table(client):
        verify_table(client)
    else:
        sys.exit(1)

    print("\n✅ Database initialization complete.")


if __name__ == "__main__":
    main()
