# Content Moderation Pipeline with Amazon Bedrock

A serverless content moderation system built on AWS managed services. Content uploaded to S3 is automatically processed through an event-driven pipeline and moderated using Amazon Bedrock's generative AI capabilities.

## Architecture Overview

<img width="577" height="698" alt="image" src="https://github.com/user-attachments/assets/a17a3f94-481a-4ef6-b3c6-101f3567eaee" />

### Components

| Service | Role |
|---------|------|
| Amazon S3 | Ingestion point — content enters the system here |
| Amazon EventBridge | Detects S3 upload events and fires notifications |
| Amazon SNS | Publishes messages to subscribed consumers |
| Amazon SQS | Buffers messages and triggers downstream processing |
| AWS Lambda | Processes messages and calls Bedrock for moderation |
| Amazon Bedrock | Performs AI-powered content moderation |
| Amazon DynamoDB | Stores moderated content for downstream applications |

## How It Works

1. An object is uploaded to the S3 bucket
2. EventBridge detects the upload and publishes a message to the SNS topic
3. The SQS queue (subscribed to the SNS topic) receives the message
4. Lambda is triggered by the SQS queue
5. Lambda calls Amazon Bedrock to moderate the content
6. Moderated content is stored in the DynamoDB table

## Design Patterns

### SNS + SQS (Fan-Out)

Using SNS and SQS together is a common AWS pattern for building scalable, decoupled systems. Benefits include:

- **Asynchronous processing** — tasks are decoupled from the ingestion path
- **Fan-out architecture** — multiple consumers can independently process the same message concurrently
- **Scalability** — each component scales independently

### Serverless

This architecture uses fully managed services, eliminating the need to provision, operate, or scale infrastructure manually.

## Extensions

While this implementation focuses on text moderation, the architecture can be extended to:

- **Audio/video moderation** using multi-modal generative AI models
- **Transcription** via Amazon Transcribe
- **Translation** via Amazon Translate
- **Image/video analysis** via Amazon Rekognition
- **Any processing task** triggered by data ingestion

## Production Considerations

In a production environment, this architecture would sit behind a front-end (mobile or web) application that accepts user-generated content and uploads it to the S3 bucket.

## Objectives

- Configure Amazon SNS and Amazon SQS to work together (subscribe SQS queue to SNS topic)
- Configure the SQS queue to trigger an AWS Lambda function
- Implement a Lambda function that moderates content using Amazon Bedrock
- Test the end-to-end architecture

## Implementing the Lambda Function

### Existing Code Structure

The Lambda function comes partially implemented with:

| Section | Purpose |
|---------|---------|
| Imports & clients | boto3 clients for S3, Bedrock, DynamoDB; constants for bucket name, model ID, table name |
| `parse_event` / `parse_messages` / `fetch_content` | Parse the S3 event (wrapped in SNS → SQS message), fetch content from S3 |
| `invoke_bedrock` | **You implement this** |
| `classify_content` | **You implement this** |
| `upload_to_dynamodb` | **You implement this** |

### Step 1: Implement `invoke_bedrock`

```python
payload = {
    "messages": [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ],
    "inferenceConfig": {
        "max_new_tokens": 3,
    }
}

body = json.dumps(payload)
response = bedrock_client.invoke_model(body=body, modelId=MODEL_ID)
return json.loads(response.get("body").read())
```

**What this does:**

- Builds a payload with the prompt and limits response to 3 tokens (encourages short true/false answers)
- Invokes the Amazon Nova model
- Returns the parsed response as a Python dictionary

> **Note:** `max_new_tokens` is model-specific. Setting it low encourages concise responses like "true" or "false".

### Step 2: Implement `classify_content`

```python
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
```

**What this does:**

- For each message, calls Bedrock twice:
  1. Checks if message is **spam**
  2. Checks if message contains **PII** (personally identifiable information)
- Sets boolean flags on each message dictionary

### Step 3: Implement `upload_to_dynamodb`

```python
serializer = TypeSerializer()
for message in messages:
    item = {key: serializer.serialize(value) for key, value in message.items()}
    dynamodb_client.put_item(Item=item, TableName=DYNAMODB_TABLE_NAME)
```

**What this does:**

- Serializes each message dictionary into DynamoDB item format
- Uploads each item to the DynamoDB table

### Deploy

Click **Deploy** in the Lambda code editor to save and deploy your changes.

---

## Lab: Testing the Pipeline

### Configure AWS CLI

```bash
aws configure set region us-west-2
aws configure set aws_access_key_id "YOUR_ACCESS_KEY"
aws configure set aws_secret_access_key "YOUR_SECRET_KEY"
```

### Create and Upload Test Content

```bash
# Create a test file with spam-like content
echo "Win a free iPhone! Click here to claim your prize." > $(uuidgen).txt

# Upload to S3
aws s3 sync --exclude "*" --include "*.txt" . s3://content-BUCKET-ID
```

### View Lambda Logs

```bash
aws logs filter-log-events --log-group-name /aws/lambda/content
```

> **Note:** The Lambda function is typically triggered within a couple of seconds. If you don't see log entries, wait a moment and re-run.

### View DynamoDB Results

```bash
aws dynamodb scan --table-name content
```

Output shows the content with moderation flags (`spam: true/false`, `pii: true/false`).

### Additional Test Examples

```bash
echo "Buy cheap sunglasses now at [link]. Limited offer!" > $(uuidgen).txt
echo "My phone number is (555) 123-4567, text me anytime!" > $(uuidgen).txt
aws s3 sync --exclude "*" --include "*.txt" . s3://content-BUCKET-ID

# Check results
aws dynamodb scan --table-name content
```

### View SNS Metrics

```bash
END_TIME=$(date '+%Y-%m-%dT%H:%M:%SZ')
START_TIME=$(date '+%Y-%m-%dT%H:%M:%SZ' -d '1 hour ago')
DIMENSIONS="Name=TopicName,Value=content"

aws cloudwatch get-metric-statistics \
  --namespace 'AWS/SNS' \
  --metric-name NumberOfMessagesPublished \
  --statistics Maximum \
  --period 3600 \
  --end-time $END_TIME \
  --start-time $START_TIME \
  --dimensions $DIMENSIONS \
  --region us-west-2
```

---

## Design Notes

### Content Identification

The S3 object key is used as a content identifier. Alternatives for production:

- Metadata lookup (e.g., author)
- Hash-based ID (SHA256)
- UUID

### Configuration Management

This lab uses constants for simplicity. In production, consider:

- Environment variables
- AWS Systems Manager Parameter Store

### Libraries

For production workloads processing SNS/SQS events frequently, consider [Powertools for AWS Lambda](https://docs.powertools.aws.dev/lambda/python/latest/) for event parsing, logging, and error handling.

### Model Accuracy

Responses from Bedrock have an element of randomness. To improve accuracy in production:

- Use a more capable model
- Use a fine-tuned model
- Combine multiple models

### Production Usage

The moderation status stored in DynamoDB can be consumed by front-end applications to:

- Hide spam or inappropriate content
- Flag content for human review
- Route content to moderation queues
