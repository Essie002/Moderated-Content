import json
import boto3
from boto3.dynamodb.types import TypeSerializer

s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime", "us-east-1")
dynamodb_client = boto3.client("dynamodb")

DYNAMODB_TABLE_NAME = "content"

MODEL_ID = "us.amazon.nova-micro-v1:0"

SPAM_PROMPT_TEMPLATE = """
You are a content moderation bot that classifies textual messages posted by users. Is the following message likely to be spam?

MESSAGE

Respond with either True or False.
"""

PII_PROMPT_TEMPLATE = """
You are a content moderation bot that classifies textual messages posted by users. Does the following message contain sensitive or private information? 

MESSAGE

Respond with either True or False.
"""

def parse_event(event):
    messages = []
    for record in event.get("Records", []):
        body = json.loads(record.get("body", "{}"))
        message = json.loads(body.get("Message", {}))
        messages.append(message)
    return messages


def parse_messages(messages):
    objects = []
    for message in messages:
        if message.get("detail-type", "") != "Object Created":
            continue

        detail = message.get("detail", {})
        bucket = detail.get("bucket", {}).get("name")
        message_id = detail.get("object", {}).get("key")

        if bucket and message_id:
            objects.append({"bucket": bucket, "id": message_id})
    return objects


def fetch_content(objects):
    for s3_object in objects:
        body = s3_client.get_object(
            Bucket=s3_object["bucket"], Key=s3_object["id"]
        ).get("Body", "")
        body = body.read().decode("utf-8")
        s3_object["message"] = body
    return objects


def invoke_bedrock(prompt):
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 3,
        }
    }
    body = json.dumps(payload)
    response = bedrock_client.invoke_model(body=body, modelId=MODEL_ID)
    return json.loads(response.get("body").read())


def classify_content(messages):
    for message in messages:
        message['spam'] = False
        prompt = SPAM_PROMPT_TEMPLATE.replace("MESSAGE", message["message"])
        response = invoke_bedrock(prompt)
        for result in response.get("results", []):
            if "true" in result['output']['message']['content'][0]['text'].lower():
                message["spam"] = True

        message['pii'] = False
        prompt = PII_PROMPT_TEMPLATE.replace("MESSAGE", message["message"])
        response = invoke_bedrock(prompt)
        for result in response.get("results", []):
            if "true" in result['output']['message']['content'][0]['text'].lower():
                message["pii"] = True

    return messages


def upload_to_dynamodb(messages):
    serializer = TypeSerializer()
    for message in messages:
        item = {key: serializer.serialize(value) for key, value in message.items()}
        dynamodb_client.put_item(Item=item, TableName=DYNAMODB_TABLE_NAME)


def handler(event, context):
    messages = parse_event(event)

    messages = parse_messages(messages)

    messages = fetch_content(messages)

    messages = classify_content(messages)

    upload_to_dynamodb(messages)

    return {"statusCode": 200, "body": json.dumps(f"{len(messages)} processed")}
