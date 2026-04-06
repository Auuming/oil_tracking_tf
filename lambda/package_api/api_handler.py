import json
import os
import redis
from influxdb_client import InfluxDBClient

def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(payload)
    }

def lambda_handler(event, context):
    endpoint = os.getenv('INFLUXDB_ENDPOINT')
    bucket = os.getenv('INFLUXDB_BUCKET')
    
    # Retrieve Redis Environment Variables
    redis_endpoint = os.getenv('REDIS_ENDPOINT')
    redis_port = int(os.getenv('REDIS_PORT', 6379))

    query_params = event.get("queryStringParameters") or {}
    retailer = query_params.get("retailer", "PTT")
    oil_type = query_params.get("type", "Diesel")

    # 1. Define a unique Cache Key
    cache_key = f"prices:{retailer}:{oil_type}"
    r = None
    
    # 2. Try to fetch from Redis Cache FIRST
    try:
        r = redis.Redis(
            host=redis_endpoint, 
            port=redis_port, 
            decode_responses=True,
            socket_timeout=2,          
            socket_connect_timeout=2   
        )
        cached_data = r.get(cache_key)
        
        if cached_data:
            # Cache HIT: Return immediately without touching InfluxDB
            return _response(200, {
                "data": json.loads(cached_data),
                "count": len(json.loads(cached_data)),
                "info": "Data retrieved from Redis Cache"
            })
    except Exception as e:
        print(f"Redis cache error: {e}") # Log error but continue to fallback to database

    # 3. Cache MISS: Fetch from InfluxDB (Timestream)
    try:
        client = InfluxDBClient(
            url=f"https://{endpoint}:8086",
            token=os.getenv('INFLUXDB_TOKEN'),
            org=os.getenv('INFLUXDB_ORG'),
            timeout=10000
        )
        query_api = client.query_api()

        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "oil_prices")
          |> filter(fn: (r) => r["retailer"] == "{retailer}")
          |> filter(fn: (r) => r["type"] == "{oil_type}")
        '''

        tables = query_api.query(query)
        results = []

        for table in tables:
            for record in table.records:
                results.append({
                    "timestamp": record.get_time().isoformat(),
                    "price": record.get_value()
                })

        # 4. Save the results back into Redis Cache for future requests
        # We set an expiration of 300 seconds (5 minutes) so the cache eventually refreshes
        if r and results:
            try:
                r.setex(cache_key, 300, json.dumps(results))
            except Exception as e:
                print(f"Failed to write to Redis: {e}")

        return _response(200, {
            "data": results,
            "count": len(results),
            "info": "Query successful, fetched from InfluxDB"
        })

    except Exception as e:
        return _response(500, {
            "error": str(e),
            "debug_endpoint": endpoint
        })
    finally:
        if 'client' in locals():
            client.close()