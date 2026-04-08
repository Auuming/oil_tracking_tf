import os
import json
import boto3
import redis
from boto3.dynamodb.conditions import Key
from decimal import Decimal

# Helper to convert DynamoDB Decimals to standard floats for JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
prices_table = dynamodb.Table(os.getenv('PRICES_TABLE'))
users_table = dynamodb.Table(os.getenv('USERS_TABLE'))

# Setup SNS Client
sns = boto3.client('sns')
alerts_topic_arn = os.getenv('ALERTS_TOPIC_ARN')

# Setup Redis connection (initialized outside the handler for warm starts)
redis_host = os.getenv('REDIS_ENDPOINT')
redis_port = int(os.getenv('REDIS_PORT', 6379))
cache = redis.Redis(host=redis_host, port=redis_port, decode_responses=True) if redis_host else None

def lambda_handler(event, context):
    route_key = event.get('routeKey', '')
    
    # Required headers for CORS so your S3 frontend can talk to API Gateway
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    }
    
    if route_key == "GET /prices":
        # 1. Get raw inputs from frontend (e.g., "PTT" and "Gasohol 95")
        query_params = event.get('queryStringParameters', {})
        retailer = query_params.get('retailer', 'PTT')
        oil_type = query_params.get('oilType', 'Gasohol 95')
        
        # 2. Normalize to match DB Partition Key (e.g., "ptt#gasohol_95")
        norm_retailer = retailer.lower()
        norm_oil = oil_type.lower().replace(" ", "_")
        partition_key = f"{norm_retailer}#{norm_oil}"
        
        # 3. CHECK REDIS CACHE FIRST
        if cache:
            try:
                cached_data = cache.get(partition_key)
                if cached_data:
                    print("Cache Hit!")
                    return {
                        "statusCode": 200,
                        "headers": headers,
                        "body": cached_data # Already a JSON string
                    }
            except Exception as e:
                print(f"Redis cache error: {e}")

        # 4. CACHE MISS: Query DynamoDB
        print("Cache Miss! Fetching from DynamoDB...")
        response = prices_table.query(
            KeyConditionExpression=Key('RetailerOilType').eq(partition_key)
        )
        
        # 5. Format the data to exactly what app.js expects: [{ time: "...", price: ... }]
        items = response.get('Items', [])
        formatted_data = [
            {"time": item.get('Time', item['Date']), "price": float(item['Price'])} 
            for item in items
        ]
        
        json_response = json.dumps(formatted_data, cls=DecimalEncoder)
        
        # 6. Save back to Redis (Cache for 1 hour / 3600 seconds)
        if cache:
            try:
                cache.setex(partition_key, 3600, json_response)
            except Exception as e:
                print(f"Redis save error: {e}")
                
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json_response
        }
        
    # Note: app.js sends POST to /alerts, so we match that route here
    elif route_key == "POST /alerts": 
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        
        if email:
            # 1. Store the whole alert payload inside DynamoDB
            users_table.put_item(Item={'Email': email, 'AlertConfig': body})
            
            # 2. Automatically subscribe the user to the SNS Topic
            if alerts_topic_arn:
                sns.subscribe(
                    TopicArn=alerts_topic_arn,
                    Protocol='email',
                    Endpoint=email
                )
                
            return {
                "statusCode": 200, 
                "headers": headers, 
                "body": json.dumps({"message": f"Alert set! Please check {email} to confirm your subscription."})
            }
            
    return {"statusCode": 404, "headers": headers, "body": json.dumps({"message": "Not Found"})}