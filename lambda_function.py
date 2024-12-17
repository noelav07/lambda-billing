import boto3
import json
import requests
from datetime import datetime, timedelta

# Slack Webhook URL
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"

# Function to fetch costs using AWS Cost Explorer
def get_cost_data():
    client = boto3.client('ce', region_name='us-east-1')

    # Define the date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)

    # Convert dates to strings
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Call AWS Cost Explorer API
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date_str,
            'End': end_date_str
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )

    # Parse the response
    costs = []
    for result in response['ResultsByTime']:
        for group in result['Groups']:
            service_name = group['Keys'][0]
            amount = float(group['Metrics']['UnblendedCost']['Amount'])
            costs.append((service_name, amount))

    return costs, start_date_str, end_date_str

# Function to format the Slack message
def format_slack_message(costs, start_date, end_date):
    today = datetime.utcnow().strftime('%A, %B %d, %Y')
    total_cost = sum(amount for _, amount in costs)
    daily_avg = total_cost / 30 if total_cost > 0 else 0.0

    # Build the message
    message = f"""📊 *AWS COST DETAILS REPORT - {datetime.utcnow().strftime('%B %d, %Y')}*
⏰ *TODAY'S SPENDING DETAILS*
{today}
No costs incurred today
Today's Total: $0.00 (₹0.00)

📅 *30-DAY COST BREAKDOWN*
{start_date} - {end_date}
"""
    for service, amount in costs:
        message += f"- {service} - ${amount:.2f} (₹{amount * 85:.2f})\n"

    message += f"""💡 *SUMMARY*
- Today's Spending - $0.00 (₹0.00)
- Last 30 Days Total - ${total_cost:.2f} (₹{total_cost * 85:.2f})
- Daily Average Cost - ${daily_avg:.2f} (₹{daily_avg * 85:.2f})
"""
    return message

# Function to send the message to Slack
def send_to_slack(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    
    if response.status_code != 200:
        raise Exception(f"Request to Slack returned an error {response.status_code}, the response is:\n{response.text}")

# Lambda handler
def lambda_handler(event, context):
    try:
        # Fetch cost data
        costs, start_date, end_date = get_cost_data()

        # Format the Slack message
        slack_message = format_slack_message(costs, start_date, end_date)

        # Send the message to Slack
        send_to_slack(slack_message)

        return {"statusCode": 200, "body": "Message sent to Slack successfully!"}

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": f"Error: {str(e)}"}
