import boto3
import requests
import os
from datetime import datetime, timedelta

# Function to get the USD to INR exchange rate dynamically
def get_exchange_rate():
    url = "https://v6.exchangerate-api.com/v6/54c6243ebcfc045f40ea797b/latest/USD"  # Replace with your API key
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200 and data.get("conversion_rates"):
        return data["conversion_rates"]["INR"]
    else:
        print("Error fetching exchange rate.")
        return 82.5  # Default fallback rate

# Lambda handler function
def lambda_handler(event, context):
    # Initialize the Cost Explorer client
    client = boto3.client('ce', region_name='us-east-1')

    # Get today's date and the date 30 days ago
    today = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

    # Fetch the cost and usage data for the last 30 days
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': today
        },
        Granularity='DAILY',
        Metrics=['AmortizedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )

    # Initialize variables
    total_cost_today = 0.00
    total_cost_last_30_days = 0.00
    services_cost = {}

    # Fetch the dynamic exchange rate (USD to INR)
    exchange_rate = get_exchange_rate()

    # Parse the response and calculate totals
    for result in response['ResultsByTime']:
        # Get the date for the current result
        date = result['TimePeriod']['Start']
        
        # If it's today's date, capture the cost for today
        if date == today:
            total_cost_today = float(result['Total']['AmortizedCost']['Amount'])
        
        # Accumulate the cost for the last 30 days
        for group in result.get('Groups', []):
            service_name = group['Keys'][0]
            service_cost = float(group['Metrics']['AmortizedCost']['Amount'])
            
            if service_name not in services_cost:
                services_cost[service_name] = 0.0
            services_cost[service_name] += service_cost

    # Calculate the total cost for the last 30 days
    total_cost_last_30_days = sum(services_cost.values())

    # Prepare the message for Slack
    slack_message = {
        "text": ":bar_chart: AWS COST DETAILS REPORT - " + today,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":clock3: *TODAY'S SPENDING DETAILS*\n{today}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"\n- *Today's Total*: ${total_cost_today:.2f} (₹{total_cost_today * exchange_rate:.2f})"
                    if total_cost_today > 0 else "No costs incurred today"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":date: *30-DAY COST BREAKDOWN*\n{start_date} - {today}\n" +
                            "\n".join([f"📌 {service} - ${cost:.2f} (₹{cost * exchange_rate:.2f})" for service, cost in services_cost.items()]) +
                            f"\n*Monthly Total*: ${total_cost_last_30_days:.2f} (₹{total_cost_last_30_days * exchange_rate:.2f})"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📌 *SUMMARY*\n" +
                            f"📅 *Today's Spending* - ${total_cost_today:.2f} (₹{total_cost_today * exchange_rate:.2f})\n" +
                            f"📊 *Last 30 Days Total* - ${total_cost_last_30_days:.2f} (₹{total_cost_last_30_days * exchange_rate:.2f})\n" +
                            f"📉 *Daily Average Cost* - ${total_cost_last_30_days / 30:.2f} (₹{(total_cost_last_30_days / 30) * exchange_rate:.2f})"
                }
            }
        ]
    }

    # Slack webhook URL from environment variable
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')

    if not slack_webhook_url:
        print("Slack webhook URL not set in environment variables.")
        return

    # Send the message to Slack
    response = requests.post(slack_webhook_url, json=slack_message)

    if response.status_code != 200:
        print(f"Error sending message to Slack: {response.status_code}, {response.text}")
    else:
        print("Message sent to Slack successfully!")
