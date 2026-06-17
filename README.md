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
