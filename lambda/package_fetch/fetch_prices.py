import os
import json
import urllib.request
from datetime import datetime
import boto3
import redis
from decimal import Decimal

# Initialize AWS Resources
dynamodb = boto3.resource('dynamodb')
prices_table = dynamodb.Table(os.getenv('PRICES_TABLE'))
users_table = dynamodb.Table(os.getenv('USERS_TABLE'))
sns = boto3.client('sns')
alerts_topic_arn = os.getenv('ALERTS_TOPIC_ARN')

# Setup Redis Connection
redis_host = os.getenv('REDIS_ENDPOINT')
redis_port = int(os.getenv('REDIS_PORT', 6379)) if os.getenv('REDIS_PORT') else 6379
cache = redis.Redis(host=redis_host, port=redis_port, decode_responses=True) if redis_host else None

def format_retailer(raw_name):
    """Formats the raw retailer name into a clean, UI-friendly string."""
    raw_name = raw_name.lower()
    if raw_name == 'bcp': return 'Bangchak'
    if raw_name in ['ptt', 'irpc', 'pt']: return raw_name.upper()
    return raw_name.title()

def format_oil(raw_name):
    """Formats the raw oil name (e.g., 'gasohol_95' -> 'Gasohol 95')."""
    return raw_name.replace('_', ' ').title()

def lambda_handler(event, context):
    url = "https://api.chnwt.dev/thai-oil-api/latest"
    
    try:
        # 1. Fetch data from the external API
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        stations = data.get('response', {}).get('stations', {})
        today_date = datetime.utcnow().strftime('%Y-%m-%d')
        # Format time to match app.js expectation (YYYY-MM-DD HH:mm)
        graph_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M') 
        
        latest_prices = {}
        
        # 2. Write formatted data to DynamoDB
        with prices_table.batch_writer() as batch:
            for station, oil_data in stations.items():
                retailer_name = format_retailer(station)
                
                for oil_type, oil_info in oil_data.items():
                    price_str = oil_info.get('price')
                    
                    # Skip if the oil type does not have a price (empty string)
                    if not price_str:
                        continue
                        
                    oil_name = format_oil(oil_type)
                    # Create a clean partition key: e.g., "Bangchak#Gasohol 95"
                    partition_key = f"{retailer_name}#{oil_name}"
                    
                    price_decimal = Decimal(str(price_str))
                    latest_prices[partition_key] = price_decimal
                    
                    batch.put_item(
                        Item={
                            'RetailerOilType': partition_key,
                            'Date': today_date,
                            'Time': graph_time,
                            'Price': price_decimal,
                            'NameTH': oil_info.get('name', '')
                        }
                    )
                    
        # 3. Clear Redis Cache so the API serves fresh data immediately
        if cache:
            try:
                cache.flushall()
                print("Redis cache cleared successfully.")
            except Exception as e:
                print(f"Redis Error: {e}")

        # 4. Process User Alerts
        if alerts_topic_arn and os.getenv('USERS_TABLE'):
            users = users_table.scan().get('Items', [])
            for user in users:
                email = user.get('Email')
                config = user.get('AlertConfig', {})
                if not email or not config: continue
                
                # Reconstruct the lookup key based on user config
                lookup_key = f"{config.get('retailer')}#{config.get('oilType')}"
                current_price = latest_prices.get(lookup_key)
                
                if current_price is not None:
                    target_price = Decimal(str(config.get('targetPrice', 0)))
                    condition = config.get('condition', '<=')
                    
                    # Trigger logic
                    if (condition == '<=' and current_price <= target_price) or (condition == '>=' and current_price >= target_price):
                        subject = f"Oil Price Alert: {config.get('retailer')} {config.get('oilType')}"
                        message = f"Hello!\\n\\nYour alert for {config.get('retailer')} {config.get('oilType')} has been triggered.\\nCurrent Price: {current_price} THB/L"
                        sns.publish(TopicArn=alerts_topic_arn, Subject=subject, Message=message)
                        
        return {"statusCode": 200, "body": "Success"}
        
    except Exception as e:
        import traceback
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        }