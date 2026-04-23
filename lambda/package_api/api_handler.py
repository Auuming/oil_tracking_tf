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

def ensure_email_subscription(topic_arn, email):
    email = (email or "").strip().lower()
    if not topic_arn or not email:
        return {
            "ok": False,
            "reason": "missing_input",
            "already_confirmed": False,
            "resent_confirmation": False,
            "confirmed_count": 0,
            "pending_count": 0,
            "deleted_stale_count": 0,
        }

    paginator = sns.get_paginator("list_subscriptions_by_topic")

    confirmed_subscriptions = []
    pending_subscriptions = []
    other_unconfirmed_subscriptions = []

    for page in paginator.paginate(TopicArn=topic_arn):
        for sub in page.get("Subscriptions", []):
            protocol = (sub.get("Protocol") or "").lower()
            endpoint = (sub.get("Endpoint") or "").strip().lower()
            sub_arn = sub.get("SubscriptionArn")

            if protocol != "email" or endpoint != email:
                continue

            if sub_arn == "PendingConfirmation":
                pending_subscriptions.append(sub)
            elif sub_arn:
                confirmed_subscriptions.append(sub)
            else:
                other_unconfirmed_subscriptions.append(sub)

    deleted_stale_count = 0

    # If there is already a confirmed subscription, stop here
    if confirmed_subscriptions:
        # best effort cleanup for odd stale non-pending ARN entries
        for sub in other_unconfirmed_subscriptions:
            sub_arn = sub.get("SubscriptionArn")
            if sub_arn and sub_arn != "PendingConfirmation":
                try:
                    sns.unsubscribe(SubscriptionArn=sub_arn)
                    deleted_stale_count += 1
                except Exception:
                    pass

        return {
            "ok": True,
            "reason": "already_confirmed",
            "already_confirmed": True,
            "resent_confirmation": False,
            "confirmed_count": len(confirmed_subscriptions),
            "pending_count": len(pending_subscriptions),
            "deleted_stale_count": deleted_stale_count,
            "subscription_arn": confirmed_subscriptions[0].get("SubscriptionArn"),
        }

    # No confirmed subscription yet -> resend confirmation
    response = sns.subscribe(
        TopicArn=topic_arn,
        Protocol="email",
        Endpoint=email,
        Attributes={
            "FilterPolicy": json.dumps({"target_email": [email]})
        }
    )

    return {
        "ok": True,
        "reason": "confirmation_resent",
        "already_confirmed": False,
        "resent_confirmation": True,
        "confirmed_count": 0,
        "pending_count": len(pending_subscriptions) + 1,
        "deleted_stale_count": deleted_stale_count,
        "subscription_arn": response.get("SubscriptionArn"),
    }

def lambda_handler(event, context):
    route_key = event.get('routeKey', '')
    headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
    
    if route_key == "GET /prices":
        # Check Redis Cache
        if cache:
            try:
                cached_data = cache.get("all_prices_grouped")
                if cached_data and cached_data != '[]':
                    return {"statusCode": 200, "headers": headers, "body": cached_data}
            except: pass
                
        # Fetch all data from DynamoDB if not in cache
        try:
            response = prices_table.scan()
            db_items = response.get('Items', [])
            
            # Group the data to match app.js structure exactly
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
                
            # Convert dictionary to a flat list and sort points by time
            final_list = []
            for rot, group in grouped_data.items():
                group["points"] = sorted(group["points"], key=lambda x: x["time"])
                final_list.append(group)
                
            # Wrap it in the "items" dictionary for app.js
            final_response = {"items": final_list}
            json_response = json.dumps(final_response, cls=DecimalEncoder)
            
            # Save back to Redis cache for 1 hour
            if cache:
                try: cache.setex("all_prices_grouped", 3600, json_response)
                except: pass
                    
            return {"statusCode": 200, "headers": headers, "body": json_response}
            
        except Exception as e:
            return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}
            
    # Handle the Alerts POST endpoint
    elif route_key == "POST /alerts": 
        try:
            body_str = event.get('body', '{}') or '{}'
            body = json.loads(body_str, parse_float=Decimal)
            email = body.get('email')
            
            if email:
                # Fetch the existing user data
                response = users_table.get_item(Key={'Email': email})
                existing_user = response.get('Item', {})
                
                # Get existing configs, default to empty list. 
                alert_configs = existing_user.get('AlertConfig', [])
                if isinstance(alert_configs, dict):
                    alert_configs = [alert_configs]
                    
                # Check for duplicates based on retailer and oilType
                new_retailer = body.get('retailer')
                new_oil_type = body.get('oilType')
                is_updated = False
                
                for i, config in enumerate(alert_configs):
                    if config.get('retailer') == new_retailer and config.get('oilType') == new_oil_type:
                        alert_configs[i] = body
                        is_updated = True
                        break
                
                if not is_updated:
                    alert_configs.append(body)

                # Save the updated array back to DynamoDB
                users_table.put_item(Item={'Email': email, 'AlertConfig': alert_configs})
                
                # Process SNS Subscription
                subscription_result = None
                if alerts_topic_arn:
                    subscription_result = ensure_email_subscription(alerts_topic_arn, email)
                    
                message = f"Alert saved for {email}!"

                if alerts_topic_arn:
                    if not subscription_result or not subscription_result.get("ok"):
                        message += " Could not verify email notification subscription status."
                    elif subscription_result.get("already_confirmed"):
                        message += " Email notifications are already enabled for this address."
                    elif subscription_result.get("resent_confirmation"):
                        pending_count = subscription_result.get("pending_count", 1)
                        message += " A confirmation email was sent. Please confirm it to enable notifications."
                        if pending_count > 1:
                            message += " (There are older unconfirmed requests for this email. Only one confirmed subscription is needed.)"
                
                return {
                    "statusCode": 200,
                    "headers": headers,
                    "body": json.dumps({"message": message})
                }
            else:
                return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Missing email in request body."})}

        except Exception as e:
            import traceback
            return {
                "statusCode": 500, 
                "headers": headers, 
                "body": json.dumps({
                    "error": str(e), 
                    "traceback": traceback.format_exc()
                })
            }
            
    return {"statusCode": 404, "headers": headers, "body": json.dumps({"message": "Not Found"})}