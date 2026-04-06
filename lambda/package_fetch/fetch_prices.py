import json
import os
import requests
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

def lambda_handler(event, context):
    api_url = "https://api.chnwt.dev/thai-oil-api/latest"
    response = requests.get(api_url)
    data = response.json()
    
    # Extract the data and the current Thai date string from the API
    response_data = data.get("response", {})
    stations = response_data.get("stations", {})
    api_date = response_data.get("date", "")  # e.g., "6 เมษายน 2569"
    
    bucket = os.getenv("INFLUXDB_BUCKET")
    
    # Setup InfluxDB Connection
    client = InfluxDBClient(
        url=f"https://{os.getenv('INFLUXDB_ENDPOINT')}:8086",
        token=os.getenv('INFLUXDB_TOKEN'),
        org=os.getenv("INFLUXDB_ORG")
    )
    
    # ==========================================
    # NEW LOGIC: Check if we already saved today's data
    # ==========================================
    query_api = client.query_api()
    
    # Query the last 24h to see if a record with today's api_date exists
    check_query = f'''
    from(bucket: "{bucket}")
      |> range(start: -24h)
      |> filter(fn: (r) => r["_measurement"] == "oil_prices")
      |> filter(fn: (r) => r["api_date"] == "{api_date}")
      |> limit(n: 1)
    '''
    
    tables = query_api.query(check_query)
    
    if len(tables) > 0:
        # We already have data for this API date! Skip writing.
        client.close()
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "skipped", "info": f"Data for '{api_date}' already exists in database."})
        }
    # ==========================================

    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # Map API keys to the names used in your Frontend UI
    retailers = {"ptt": "PTT", "bcp": "Bangchak", "shell": "Shell"}
    fuel_types = {
        "premium_diesel": "Diesel",
        "gasohol_95": "Gasohol 95",
        "gasohol_91": "Gasohol 91",
        "gasohol_e20": "Gasohol E20"
    }

    points = []
    
    # Loop through requested stations and fuels
    for r_key, r_name in retailers.items():
        station_data = stations.get(r_key, {})
        for f_key, f_name in fuel_types.items():
            fuel_info = station_data.get(f_key, {})
            price_str = fuel_info.get("price", "")
            
            # Only save if there is a valid price
            if price_str:
                try:
                    price_val = float(price_str)
                    point = Point("oil_prices") \
                        .tag("retailer", r_name) \
                        .tag("type", f_name) \
                        .tag("api_date", api_date) \
                        .field("price", price_val) \
                        .time(datetime.now(timezone.utc))
                    points.append(point)
                except ValueError:
                    continue

    # Write all points at once
    if points:
        write_api.write(bucket=bucket, record=points)
    
    if 'client' in locals():
        client.close()

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "success", "points_saved": len(points)})
    }