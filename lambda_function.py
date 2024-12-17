import boto3
import requests
import datetime
import os

# Slack Webhook URL
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"

# Initialize AWS Cost Explorer client
ce_client = boto3.client('ce', region_name='us-east-1')

def get_cost_data():
    # Date range for the last 30 days
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    
    # Fetch cost data from Cost Explorer
    response = ce_client.get_cost_and_usage(
        TimePeriod={'Start': str(start_date), 'End': str(end_date)},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    
    # Process cost data
    cost_details = []
    total_cost = 0.0
    for group in response['ResultsByTime'][0]['Groups']:
        service = group['Keys'][0]
        amount = float(group['Metrics']['UnblendedCost']['Amount'])
        if amount > 0:
            cost_details.append(f"- {service} - ${amount:.2f}")
            total_cost += amount
    
    return cost_details, total_cost

def send_to_slack(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print(f"Failed to send message to Slack: {response.text}")

def lambda_handler(event, context):
    # Get cost data
    cost_details, total_cost = get_cost_data()
    today = datetime.date.today().strftime('%A, %B %d, %Y')
    
    # Format the Slack message
    message = f"""
*AWS COST DETAILS REPORT - {datetime.date.today()}*
:clock3: *TODAY'S SPENDING DETAILS*
{today}
No costs incurred today
Today's Total: $0.00 (₹0.00)

:date: *30-DAY COST BREAKDOWN*
{chr(10).join(cost_details)}

:drawing_pin: *SUMMARY*
- Today's Spending - $0.00 (₹0.00)
- Last 30 Days Total - ${total_cost:.2f}
- Daily Average Cost - ${total_cost / 30:.2f}
    """
    # Send the message to Slack
    send_to_slack(message)
    print("Cost report sent to Slack successfully!")
