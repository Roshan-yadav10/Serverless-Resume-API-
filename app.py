"""Lambda handler for the Resume API.

DynamoDB layout: partition key `section`, sort key `sortKey`.
One handler serves every route; the API Gateway resource path selects the section.
"""
import json
import logging
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

SECTIONS = ("profile", "experience", "education", "skills")
NEWEST_FIRST = {"experience", "education"}  # sort keys start with a date/year
KEY_ATTRIBUTES = {"section", "sortKey"}


def _json_default(value):
    """DynamoDB returns numbers as Decimal, which json cannot serialize."""
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Unserializable type: {type(value)}")


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_json_default),
    }


def _query_section(section):
    """Return every item of a section, following pagination."""
    items, start_key = [], None
    while True:
        kwargs = {
            "KeyConditionExpression": Key("section").eq(section),
            "ScanIndexForward": section not in NEWEST_FIRST,
        }
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key
        page = TABLE.query(**kwargs)
        items.extend(page["Items"])
        start_key = page.get("LastEvaluatedKey")
        if not start_key:
            return [{k: v for k, v in item.items() if k not in KEY_ATTRIBUTES} for item in items]


def get_section(section):
    items = _query_section(section)
    if section == "profile":
        return items[0] if items else None
    return items


def lambda_handler(event, context):
    route = event.get("resource", "")
    logger.info("Request: %s %s", event.get("httpMethod"), route)
    try:
        if route == "/resume":
            body = {name: get_section(name) for name in SECTIONS}
            if body["profile"] is None:
                return _response(404, {"message": "Resume data not found. Run seed.py first."})
            return _response(200, body)

        section = route.lstrip("/")
        if section not in SECTIONS:
            return _response(404, {"message": f"Unknown route: {route}"})

        data = get_section(section)
        if data is None or data == []:
            return _response(404, {"message": f"No data for '{section}'. Run seed.py first."})
        return _response(200, data)
    except Exception:  # log details server-side, return a generic message
        logger.exception("Unhandled error")
        return _response(500, {"message": "Internal server error"})
