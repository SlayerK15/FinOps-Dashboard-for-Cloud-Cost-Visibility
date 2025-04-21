import os
import time
import schedule
import boto3
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class CloudCostCollector:
    def __init__(self):
        self.db_path = os.getenv('SQLITE_DB_PATH', '/app/data/cloud_costs.db')
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        self.setup_database()
        
        # Initialize AWS clients
        self.ce_client = boto3.client('ce',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )

    def setup_database(self):
        """Create necessary tables if they don't exist"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cloud_costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT,
                    cost REAL,
                    timestamp DATETIME,
                    region TEXT
                )
            """))
            conn.commit()

    def collect_costs(self):
        """Collect cost data from AWS Cost Explorer"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        response = self.ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'REGION'}
            ]
        )

        costs = []
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                region = group['Keys'][1]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                
                costs.append({
                    'service': service,
                    'cost': cost,
                    'timestamp': result['TimePeriod']['Start'],
                    'region': region
                })

        # Store in SQLite
        if costs:
            df = pd.DataFrame(costs)
            df.to_sql('cloud_costs', self.engine, if_exists='append', index=False)
            print(f"Stored {len(costs)} cost records")

    def run(self):
        """Run the collector on a schedule"""
        schedule.every(int(os.getenv('COLLECTOR_INTERVAL', 300))).seconds.do(self.collect_costs)
        
        # Run immediately on startup
        self.collect_costs()
        
        while True:
            schedule.run_pending()
            time.sleep(1)

    print("AWS_ACCESS_KEY_ID:", os.getenv("AWS_ACCESS_KEY_ID"))
    print("AWS_SECRET_ACCESS_KEY:", os.getenv("AWS_SECRET_ACCESS_KEY"))
    print("AWS_REGION:", os.getenv("AWS_REGION"))


if __name__ == '__main__':
    collector = CloudCostCollector()
    collector.run() 