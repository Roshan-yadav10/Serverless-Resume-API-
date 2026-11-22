#!/usr/bin/env python3
"""Load data/resume.json into the DynamoDB table (safe to re-run: items are overwritten).

Usage: python seed.py --table <TableName> [--file data/resume.json] [--region ap-south-1]
"""
import argparse
import json
from decimal import Decimal

import boto3

REQUIRED = ("profile", "experience", "education", "skills")


def build_items(resume):
    """Map the JSON document to DynamoDB items with (section, sortKey) keys."""
    missing = [s for s in REQUIRED if s not in resume]
    if missing:
        raise SystemExit(f"resume.json is missing sections: {', '.join(missing)}")

    yield {"section": "profile", "sortKey": "main", **resume["profile"]}
    for job in resume["experience"]:
        yield {"section": "experience", "sortKey": f"{job['start_date']}#{job['company']}", **job}
    for edu in resume["education"]:
        yield {"section": "education", "sortKey": f"{edu['end_year']}#{edu['institution']}", **edu}
    for group in resume["skills"]:
        yield {"section": "skills", "sortKey": group["category"], **group}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--table", required=True)
    parser.add_argument("--file", default="data/resume.json")
    parser.add_argument("--region")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as fh:
        resume = json.load(fh, parse_float=Decimal)  # DynamoDB rejects float

    table = boto3.resource("dynamodb", region_name=args.region).Table(args.table)
    count = 0
    with table.batch_writer() as batch:
        for item in build_items(resume):
            batch.put_item(Item=item)
            count += 1
    print(f"Loaded {count} items into {args.table}")


if __name__ == "__main__":
    main()
