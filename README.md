# Lambda Billing Slack Bot

This project integrates AWS Lambda with Slack to send daily AWS cost reports and respond to user requests. The bot provides AWS billing details in Slack channels when mentioned and sends daily reports via AWS EventBridge.

## Prerequisites

Before starting, ensure you have the following:

- **AWS Account** with access to AWS Cost Explorer and Lambda.
- **Slack workspace** and a **Slack app**.
- **Alpha Vantage API key** for currency conversion.
- **API Gateway** for triggering Lambda from Slack.

## Step 1: Create and Configure a Slack App

### 1.1. Create a Slack App

1. Go to the [Slack API](https://api.slack.com/apps) and create a new app.
2. Select "From scratch" and give your app a name (e.g., "AWS Billing Bot") and choose your workspace.
3. Click **Create App**.

### 1.2. Set Permissions (OAuth Scopes)

1. In the Slack app settings, go to **OAuth & Permissions**.
2. Under **Bot Token Scopes**, add the following permissions:
   - `app_mentions:read` – To read messages where the bot is mentioned.
   - `channels:history` – To read messages in public channels.
   - `channels:read` – To view basic information about public channels.
   - `chat:write` – To send messages as the bot.
   - `commands` – To allow the bot to accept slash commands.
   - `im:read` – To read direct messages.
   - `users:write` – To set presence for the bot.
   
3. Click **Save Changes**.

### 1.3. Install the App to Your Workspace

1. Go to **Install App** in the sidebar.
2. Click **Install App to Workspace**.
3. Authorize the app and get your **SLACK_BOT_TOKEN** and **SLACK_SIGNING_SECRET**.

## Step 2: Set Up AWS Lambda

### 2.1. Create an AWS Lambda Function

1. Go to the [AWS Lambda Console](https://console.aws.amazon.com/lambda/).
2. Click **Create function** and choose **Author from scratch**.
3. Name your function (e.g., `LambdaBillingSlackBot`).
4. Choose **Python 3.x** as the runtime.
5. Set the **Execution role** to a role that has permissions to access AWS Cost Explorer (you can create a new role with the `AWSCostExplorerReadOnlyAccess` policy).

### 2.2. Install Dependencies

1. In your local environment, create a `requirements.txt` file with the following dependencies:

2. Install the dependencies locally:
```bash
pip install -r requirements.txt
```
3. Create a ZIP file containing your Python code and all dependencies:

```bash
zip -r lambda_function.zip .
```

4. Upload the ZIP file to AWS Lambda.


### 2.3. Set Environment Variables

1. In the AWS Lambda console, go to your function.
2. Under the **Configuration** tab, add the following environment variables:
   - `SLACK_BOT_TOKEN`: Your Slack bot token.
   - `SLACK_CHANNEL_ID`: The Slack channel ID where reports will be sent.
   - `SLACK_SIGNING_SECRET`: Your Slack signing secret.
   - `ALPHA_VANTAGE_API_KEY`: Your Alpha Vantage API key for currency conversion.

### 2.4. Set Lambda Handler

1. Set the Lambda handler to `lambda_function.lambda_handler`.

## Step 3: Set Up API Gateway

### 3.1. Create an API Gateway REST API

1. Go to the [API Gateway Console](https://console.aws.amazon.com/apigateway/).
2. Click **Create API** and choose **REST API**.
3. Set up a new API and create a resource (e.g., `/slack-events`).
4. Create a new **POST** method for this resource and integrate it with your Lambda function.

### 3.2. Deploy the API

1. Create a new deployment stage (e.g., `prod`).
2. Deploy your API.

## Step 4: Set Up EventBridge for Scheduled Reports

### 4.1. Create a Rule in EventBridge

1. Go to the [EventBridge Console](https://console.aws.amazon.com/events/).
2. Click **Create Rule** and select **Schedule**.
3. Set the schedule for your daily reports (e.g., `cron(0 9 * * ? *)` for 9 AM UTC).
4. Set the target to your Lambda function.

## Step 5: Lambda Function Code

The Lambda function code is located in the `trimmed.py` file in the repository. This code handles:

- Fetching AWS billing data using AWS Cost Explorer.
- Converting USD to INR using the Alpha Vantage API.
- Sending AWS cost reports to Slack when mentioned.
- Scheduling daily reports using AWS EventBridge.

## Step 6: Test the Setup

### Slack Mention

In your Slack channel, mention the bot and type "bills":

```text
@aws-bills bills