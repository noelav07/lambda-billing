import json  # Import the json module
import logging
import boto3
from botocore.exceptions import ClientError
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from dotenv import load_dotenv
import os
import requests
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

load_dotenv()

# Slack configurations
bot_token = os.environ.get("SLACK_BOT_TOKEN")
CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")

# Initialize AWS Cost Explorer client
ce_client = boto3.client('ce')

# Initialize the Slack app
app = App(
    token=bot_token,
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
)

handler = SlackRequestHandler(app)

def get_usd_to_inr_rate():
    try:
        API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")
        url = f'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=INR&apikey={API_KEY}'
        response = requests.get(url)
        data = response.json()
        rate = float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
        logger.info(f"Successfully fetched USD to INR rate: {rate}")
        return rate
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {str(e)}", exc_info=True)
        return 83.34  # Fallback rate if API fails

def get_aws_costs():
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        logger.info(f"Fetching AWS costs for period: {start_date} to {end_date}")
        
        usd_to_inr = get_usd_to_inr_rate()
        logger.info(f"Using USD to INR rate: {usd_to_inr}")
        
        logger.info("Fetching today's costs from AWS Cost Explorer")
        today_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': end_date.strftime('%Y-%m-%d'),
                'End': (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )
        
        # Get monthly costs
        logger.info("Fetching monthly costs from AWS Cost Explorer")
        monthly_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )
        
        # Format the header with larger text
        day_name = end_date.strftime('%A')
        message = f"📊 *{end_date.strftime('%B')}* Month Bill Cycle\n\n"

        # Monthly costs section
        monthly_total = 0
        monthly_services = []
        
        for result in monthly_response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                if cost > 0:
                    monthly_total += cost
                    monthly_services.append((service, cost))
        
        # Sort and display monthly services
        if monthly_services:
            monthly_services.sort(key=lambda x: x[1], reverse=True)
            message += "*📅 Services utilised*\n"
            for service, cost in monthly_services:
                inr_cost = cost * usd_to_inr
                logger.debug(f"Monthly cost for {service}: USD {cost:.2f}, INR {inr_cost:.2f}")
                message += f"▹ {service} - 💵${cost:,.2f} (₹{inr_cost:,.2f})\n"
        else:
            message += "*📅 Monthly Service Breakdown*\nNo costs incurred in this period 📉\n"
        
        monthly_total_inr = monthly_total * usd_to_inr
        logger.info(f"Monthly total cost: USD {monthly_total:.2f}, INR {monthly_total_inr:.2f}")
        # message += f"\n*Service Total:* 💵${monthly_total:,.2f} (₹{monthly_total_inr:,.2f})\n\n"
        
        # Tax section (assuming tax is calculated as a fixed amount or a percentage)
        tax_amount = 1.39  # Example tax amount in USD
        tax_inr = tax_amount * usd_to_inr
        # message += f"▹ Tax - 💵${tax_amount:,.2f} (₹{tax_inr:,.2f})\n"
        
        # Total with tax
        total_with_tax = monthly_total + tax_amount
        total_with_tax_inr = total_with_tax * usd_to_inr
        # message += f"\n*Total with Tax:* 💵${total_with_tax:,.2f} (₹{total_with_tax_inr:,.2f})\n\n"
        
        # Summary section
        message += "\n*📌 SUMMARY*\n"
        message += f"\n*Service Total:* 💵${monthly_total:,.2f} (₹{monthly_total_inr:,.2f})"
        message += f"\n▹ Tax - 💵${tax_amount:,.2f} (₹{tax_inr:,.2f})\n"
        message += f"▹ *Total Cost incurred till last bill cycle* - 💵${total_with_tax:,.2f} (₹{total_with_tax_inr:,.2f})\n"
        
        return message
        
    except ClientError as e:
        logger.error(f"AWS Cost Explorer API error: {str(e)}", exc_info=True)
        return f"❌ *Error fetching AWS costs:* {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_aws_costs: {str(e)}", exc_info=True)
        return f"❌ *An unexpected error occurred:* {str(e)}"


@app.event("app_mention")
def handle_mention(event, say):
    logger.info(f"Received app mention event from user: {event['user']}")
    if "bills" in event['text'].lower():
        logger.info("Cost report requested via mention")
        cost_message = get_aws_costs()
        say(cost_message)
    else:
        logger.info("Generic greeting requested via mention")
        say(f"Hey <@{event['user']}>!")

def lambda_handler(event, context):
    """
    AWS Lambda handler function
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Handle Slack URL verification challenge
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            if isinstance(body, dict) and body.get('type') == 'url_verification':
                logger.info("Handling Slack URL verification challenge")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'challenge': body['challenge']})
                }

        # Handle scheduled event from EventBridge
        if (
            isinstance(event, dict) and 
            (('source' in event and event['source'] == 'aws.events') or
             ('detail-type' in event and event['detail-type'] == 'Scheduled Event'))
        ):
            logger.info("Processing scheduled event for daily cost report")
            cost_message = get_aws_costs()
            app.client.chat_postMessage(
                channel=CHANNEL_ID,
                text=cost_message
            )
            logger.info("Daily cost report sent successfully")
            return {
                'statusCode': 200,
                'body': json.dumps('Daily cost report sent successfully')
            }

        # Handle manual trigger via /scheduled-report endpoint
        elif (
            isinstance(event, dict) and
            'path' in event and 
            event['path'] == '/slack-events'
        ):
            logger.info("Processing manual trigger for cost report")
            cost_message = get_aws_costs()
            app.client.chat_postMessage(
                channel=CHANNEL_ID,
                text=cost_message
            )
            return {
                'statusCode': 200,
                'body': json.dumps('Cost report sent successfully')
            }

        # Handle Slack events (these come through API Gateway)
        elif 'body' in event and 'headers' in event:
            logger.info("Processing Slack event via API Gateway")
            return handler.handle(event, context)
            
        logger.warning(f"Received unsupported event type: {event}")
        return {
            'statusCode': 400,
            'body': json.dumps('Unsupported event type')
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps(f'Internal server error: {str(e)}')
        }
