# Serverless Resume API (AWS SAM)

```
Client --x-api-key--> API Gateway (usage plan: throttle + quota) --> Lambda (Python 3.12) --> DynamoDB
```

| Endpoint | Returns |
|---|---|
| `GET /resume` | all sections |
| `GET /profile` | personal information (object) |
| `GET /experience` | jobs, newest first |
| `GET /education` | degrees, newest first |
| `GET /skills` | skill groups by category |

## Files
| File | Purpose |
|---|---|
| `template.yaml` | SAM template: table, API with API key and usage plan, Lambda, least-privilege IAM |
| `src/app.py` | Lambda handler |
| `data/resume.json` | Your resume data (the source of truth; replace the sample) |
| `seed.py` | Loads `resume.json` into DynamoDB |

## Deploy
Prerequisites: AWS CLI configured, AWS SAM CLI, Python 3.12, `pip install boto3`.

```bash
sam build
sam deploy --guided            # accept defaults; note the stack outputs
```

Load the data (the table name is the `TableName` output):
```bash
python seed.py --table <TableName>
```

Get the API key and call the API:
```bash
KEY=$(aws apigateway get-api-key --api-key <ApiKeyId> --include-value --query value --output text)
URL=<ApiUrl>

curl -H "x-api-key: $KEY" $URL/resume
curl -H "x-api-key: $KEY" $URL/experience
curl $URL/profile                      # no key -> 403 Forbidden
```

## Verify throttling
With the defaults (5 req/s, burst 10, 1000 per day):
```bash
for i in $(seq 1 40); do curl -s -o /dev/null -w "%{http_code}\n" -H "x-api-key: $KEY" $URL/skills & done; wait
```
Some responses should be `429 Too Many Requests`.

## Design notes
- **Keys:** partition key `section`, sort key `sortKey`. All items of a section are fetched with one efficient `Query`. Sort keys start with a date (`2023-06#Company`) or year, so `ScanIndexForward=false` returns newest first.
- **Data source:** `resume.json` is loaded into DynamoDB by `seed.py`; the Lambda reads the table. Edit the JSON and re-run `seed.py` to update (removed entries are not deleted; delete them in the console or re-create the table).
- **Security:** API key required on every method; Lambda has read-only access to its own table only; errors return generic messages while details go to CloudWatch Logs.
- **Cost:** on-demand DynamoDB, 128 MB arm64 Lambda; effectively free at low traffic.
- **Limitations:** an API key identifies a client and enables throttling, but is not strong authentication. For production add AWS WAF, a Cognito or IAM authorizer, CORS settings if called from a browser, and DynamoDB point-in-time recovery.

## Clean up
```bash
sam delete
```
