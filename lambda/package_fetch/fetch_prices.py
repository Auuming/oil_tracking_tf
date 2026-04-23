import os
import json
import urllib.request
from datetime import datetime
import boto3
import redis
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
prices_table = dynamodb.Table(os.getenv('PRICES_TABLE'))
users_table = dynamodb.Table(os.getenv('USERS_TABLE'))
sns = boto3.client('sns')
alerts_topic_arn = os.getenv('ALERTS_TOPIC_ARN')

redis_host = os.getenv('REDIS_ENDPOINT')
redis_port = int(os.getenv('REDIS_PORT', 6379)) if os.getenv('REDIS_PORT') else 6379
cache = redis.Redis(host=redis_host, port=redis_port, decode_responses=True) if redis_host else None


def format_retailer(raw_name):
    raw_name = raw_name.lower()
    if raw_name == 'bcp':
        return 'Bangchak'
    if raw_name in ['ptt', 'irpc', 'pt']:
        return raw_name.upper()
    return raw_name.title()


def lambda_handler(event, context):
    url = os.getenv("SCRAPER_API_URL")

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

        stations = data.get('response', {}).get('stations', {})

        today_date = datetime.utcnow().strftime('%Y-%m-%d')
        graph_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

        latest_prices = {}

        with prices_table.batch_writer() as batch:
            for station, oil_data in stations.items():
                retailer_name = format_retailer(station)

                for oil_key_th, oil_info in oil_data.items():
                    price_str = oil_info.get('price')

                    if not price_str:
                        continue

                    # keep Thai key exactly as JSON key
                    oil_name = oil_key_th

                    partition_key = f"{retailer_name}#{oil_name}"
                    price_decimal = Decimal(str(price_str))

                    latest_prices[partition_key] = price_decimal

                    batch.put_item(
                        Item={
                            'RetailerOilType': partition_key,
                            'Date': today_date,
                            'Time': graph_time,
                            'Price': price_decimal,
                            'NameTH': oil_key_th.replace('_', ' ')
                        }
                    )

        if cache:
            try:
                cache.flushall()
                print("Redis cache cleared successfully.")
            except Exception as e:
                print(f"Redis Error: {e}")

        if alerts_topic_arn and os.getenv('USERS_TABLE'):
            users = users_table.scan().get('Items', [])

            for user in users:
                email = user.get('Email')
                configs = user.get('AlertConfig', [])

                if not email or not configs:
                    continue

                if isinstance(configs, dict):
                    configs = [configs]

                triggered_messages = []

                for config in configs:
                    lookup_key = f"{config.get('retailer')}#{config.get('oilType')}"
                    current_price = latest_prices.get(lookup_key)

                    if current_price is not None:
                        target_price = Decimal(str(config.get('targetPrice', 0)))
                        condition = config.get('condition', '<=')

                        if (condition == '<=' and current_price <= target_price) or \
                           (condition == '>=' and current_price >= target_price):
                            triggered_messages.append(
                                f"- {config.get('retailer')} {config.get('oilType')}: {current_price} THB/L (Condition: {condition} {target_price})"
                            )

                if triggered_messages:
                    subject = "Your Daily Oil Price Alerts"
                    combined_alerts_text = "\n".join(triggered_messages)
                    message = (
                        f"Hello!\n\n"
                        f"The following oil prices have reached your target conditions today:\n\n"
                        f"{combined_alerts_text}\n\n"
                        f"Stay safe on the road!"
                    )

                    sns.publish(
                        TopicArn=alerts_topic_arn,
                        Subject=subject,
                        Message=message,
                        MessageAttributes={
                            'target_email': {
                                'DataType': 'String',
                                'StringValue': email
                            }
                        }
                    )

        return {"statusCode": 200, "body": "Success"}

    except Exception as e:
        import traceback
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            }, ensure_ascii=False)
        }