import os
import json
import urllib.request
from datetime import datetime
import boto3

dynamodb = boto3.resource('dynamodb')
prices_table = dynamodb.Table(os.getenv('PRICES_TABLE'))

def lambda_handler(event, context):
    url = "https://api.chnwt.dev/thai-oil-api/latest"
    
    try:
        # 1. Fetch JSON data from the API
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        stations = data.get('response', {}).get('stations', {})
        
        # We need a sort key (Date) and a timestamp for the frontend graph
        today_date = datetime.utcnow().strftime('%Y-%m-%d')
        graph_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M') 
        
        # 2. Write to DynamoDB using batch writing for speed
        with prices_table.batch_writer() as batch:
            for station, oil_data in stations.items():
                for oil_type, oil_info in oil_data.items():
                    price_str = oil_info.get('price')
                    
                    # Skip if price is empty string
                    if not price_str:
                        continue
                        
                    # Partition Key: e.g., "ptt#gasohol_95"
                    partition_key = f"{station.lower()}#{oil_type.lower()}"
                    
                    batch.put_item(
                        Item={
                            'RetailerOilType': partition_key,
                            'Date': today_date,
                            'Time': graph_time, # Storing this so frontend gets the exact point in time
                            'Price': float(price_str),
                            'NameTH': oil_info.get('name', '')
                        }
                    )
                    
        return {"statusCode": 200, "body": "Successfully updated DynamoDB"}
        
    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": "Failed to fetch data"}