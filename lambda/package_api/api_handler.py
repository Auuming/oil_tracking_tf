import os
import json
import boto3
import redis
from decimal import Decimal

# Helper class to allow json.dumps to process Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

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

def lambda_handler(event, context):
    route_key = event.get('routeKey', '')
    headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
    
    if route_key == "GET /prices":
        # 1. Check Redis Cache first
        if cache:
            try:
                cached_data = cache.get("all_prices_grouped")
                if cached_data and cached_data != '[]':
                    return {"statusCode": 200, "headers": headers, "body": cached_data}
            except: pass
                
        # 2. Fetch all data from DynamoDB if not in cache
        try:
            response = prices_table.scan()
            db_items = response.get('Items', [])
            
            # 3. Group the data to match app.js structure exactly
            grouped_data = {}
            for item in db_items:
                rot = item.get('RetailerOilType', '')
                if '#' not in rot: continue
                    
                # Split the key (e.g., "Bangchak#Gasohol 95" -> "Bangchak", "Gasohol 95")
                retailer_name, oil_name = rot.split('#', 1)
                
                # Initialize the group if it doesn't exist
                if rot not in grouped_data:
                    grouped_data[rot] = {
                        "retailer": retailer_name,
                        "oilType": oil_name,
                        "points": []
                    }
                    
                # Append the price point
                grouped_data[rot]["points"].append({
                    "time": item.get('Time', item.get('Date', '')),
                    "price": float(item['Price'])
                })
                
            # 4. Convert dictionary to a flat list and sort points by time
            final_list = []
            for rot, group in grouped_data.items():
                group["points"] = sorted(group["points"], key=lambda x: x["time"])
                final_list.append(group)
                
            # 5. Wrap it in the "items" dictionary for app.js
            final_response = {"items": final_list}
            json_response = json.dumps(final_response, cls=DecimalEncoder)
            
            # 6. Save back to Redis cache for 1 hour
            if cache:
                try: cache.setex("all_prices_grouped", 3600, json_response)
                except: pass
                    
            return {"statusCode": 200, "headers": headers, "body": json_response}
            
        except Exception as e:
            return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}
            
    # Handle the Alerts POST endpoint
    elif route_key == "POST /alerts": 
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        
        if email:
            users_table.put_item(Item={'Email': email, 'AlertConfig': body})
            if alerts_topic_arn:
                sns.subscribe(TopicArn=alerts_topic_arn, Protocol='email', Endpoint=email)
            return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": f"Confirmation sent to {email}! Please click the link in the email to start receiving your price alerts."})}
            
    return {"statusCode": 404, "headers": headers, "body": json.dumps({"message": "Not Found"})}