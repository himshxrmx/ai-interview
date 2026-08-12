"""
DynamoDB helper functions for managing interview sessions.
"""

import os
import json
import boto3
from typing import Optional
from dotenv import load_dotenv

from models import SessionState

load_dotenv()

# ─── DynamoDB Client Setup ──────────────────────────────────────────────────────

TABLE_NAME = "InterviewSessions"


def _get_dynamodb_resource():
    """Create a DynamoDB resource, supporting both local and AWS endpoints."""
    endpoint_url = os.getenv("DYNAMODB_ENDPOINT_URL")
    region = os.getenv("AWS_REGION", "us-east-1")

    if endpoint_url:
        return boto3.resource(
            "dynamodb",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id="local",
            aws_secret_access_key="local"
        )

    return boto3.resource("dynamodb", region_name=region)


def _get_table():
    """Get a reference to the InterviewSessions table."""
    dynamodb = _get_dynamodb_resource()
    return dynamodb.Table(TABLE_NAME)


# ─── CRUD Operations ───────────────────────────────────────────────────────────


def create_session(session: SessionState) -> None:
    """
    Write a new session to DynamoDB.

    Args:
        session: A fully populated SessionState object.
    """
    table = _get_table()
    item = json.loads(session.model_dump_json())
    item = _convert_floats_to_decimal(item)
    table.put_item(Item=item)


def save_candidate_data(candidate_id: str, data: dict) -> None:
    """Save raw extracted text for a candidate to DynamoDB."""
    dynamodb = _get_dynamodb_resource()
    table = dynamodb.Table("CandidateData")
    item = {"candidate_id": candidate_id, **data}
    table.put_item(Item=item)


def get_candidate_data(candidate_id: str) -> Optional[dict]:
    """Retrieve raw candidate data from DynamoDB."""
    dynamodb = _get_dynamodb_resource()
    table = dynamodb.Table("CandidateData")
    response = table.get_item(Key={"candidate_id": candidate_id})
    return response.get("Item")


def get_session(session_id: str) -> Optional[SessionState]:
    """
    Fetch a session from DynamoDB by its session_id.

    Args:
        session_id: The unique session identifier.

    Returns:
        A SessionState object if found, else None.
    """
    table = _get_table()
    response = table.get_item(Key={"session_id": session_id})

    item = response.get("Item")
    if not item:
        return None

    # DynamoDB stores numbers as Decimal; convert for Pydantic
    item = _convert_decimals(item)
    return SessionState(**item)


def update_session(session_id: str, updates: dict) -> None:
    """
    Update arbitrary fields on a session.

    Args:
        session_id: The unique session identifier.
        updates: A dict of field names to new values.
    """
    table = _get_table()

    update_parts = []
    attr_values = {}
    attr_names = {}

    for i, (key, value) in enumerate(updates.items()):
        placeholder_val = f":v{i}"
        placeholder_name = f"#k{i}"
        update_parts.append(f"{placeholder_name} = {placeholder_val}")
        attr_values[placeholder_val] = _convert_floats_to_decimal(value)
        attr_names[placeholder_name] = key

    update_expression = "SET " + ", ".join(update_parts)

    table.update_item(
        Key={"session_id": session_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=attr_values,
        ExpressionAttributeNames=attr_names,
    )


# ─── Utilities ──────────────────────────────────────────────────────────────────


def _convert_decimals(obj):
    """
    Recursively convert DynamoDB Decimal types to int/float for Pydantic compatibility.
    """
    from decimal import Decimal

    if isinstance(obj, list):
        return [_convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def _convert_floats_to_decimal(obj):
    """
    Recursively convert Python float types to Decimal for DynamoDB compatibility.
    DynamoDB does not accept Python floats — they must be Decimal.
    """
    from decimal import Decimal

    if isinstance(obj, list):
        return [_convert_floats_to_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj
