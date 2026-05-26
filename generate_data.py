import pandas as pd
import random
import json
import os

def generate_messy_data(num_rows=100, output_file="raw_sales_data.csv"):
    dates = ['2023-10-01', 'Oct 2nd 2023', '2023/10/03', '10-04-2023', 'invalid_date', '']
    prices = ['$19.99', '1,000.50', 'USD 20', '25.00', 'FREE', '']
    user_ids = ['U1001', 'user-1002', '1003', 'U-1004', 'N/A', None]
    product_names = ['apple iphone 13', 'Samsung Galaxy S22', 'SONY HEADPHONES', 'unknown', 'ipad pro']
    
    data = []
    for i in range(num_rows):
        # Create a nested JSON string for metadata
        metadata = {
            "category": random.choice(["electronics", "accessories", "unknown"]),
            "warranty_years": random.choice([1, 2, None])
        }
        
        row = {
            "transaction_id": f"TXN-{random.randint(10000, 99999)}",
            "date": random.choice(dates),
            "price_string": random.choice(prices),
            "user_id": random.choice(user_ids),
            "product_name": random.choice(product_names),
            "metadata": json.dumps(metadata) if random.random() > 0.1 else "{invalid_json"
        }
        data.append(row)
        
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    print(f"Messy sales data generated at: {os.path.abspath(output_file)}")

def generate_messy_logs(num_rows=100, output_file="raw_server_logs.csv"):
    ips = ['192.168.1.1', '10.0.0.5', 'invalid-ip', '256.256.256.256', '']
    methods = ['GET', 'post', 'Put', 'DELETE', 'unknown_method']
    endpoints = ['/api/v1/users', '/login', '/api/v2/items?id=123', '']
    statuses = ['200', '404', '500', '200 OK', 'Error 503']
    
    data = []
    for i in range(num_rows):
        # We simulate a single column of raw unstructured log strings
        ip = random.choice(ips)
        method = random.choice(methods)
        endpoint = random.choice(endpoints)
        status = random.choice(statuses)
        date = f"[{random.randint(1,28)}/Oct/2023:{random.randint(0,23)}:{random.randint(10,59)}:{random.randint(10,59)} +0000]"
        
        # Mix formats randomly
        if random.random() > 0.3:
            log_str = f"{ip} - - {date} \"{method} {endpoint} HTTP/1.1\" {status}"
        else:
            log_str = f"ERROR: {date} IP:{ip} Request:'{method} {endpoint}' resulted in {status}"
            
        data.append({"raw_log": log_str})
        
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    print(f"Messy server logs generated at: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    generate_messy_data()
    generate_messy_logs()
