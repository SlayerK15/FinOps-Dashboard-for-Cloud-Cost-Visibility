import os
import time
import schedule
import boto3
import pandas as pd
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class CloudCostCollector:
    def __init__(self):
        self.data_dir = os.getenv('DATA_DIR', '/app/data')
        self.costs_file = os.path.join(self.data_dir, 'cloud_costs.csv')
        self.budget_file = os.path.join(self.data_dir, 'budget_metrics.csv')
        self.daily_budget = float(os.getenv('DAILY_BUDGET', 0.33))  # Default $10/month = ~$0.33/day
        
        # Initialize AWS clients
        self.ce_client = boto3.client('ce',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Initialize files if they don't exist
        self.initialize_files()

    def initialize_files(self):
        """Create the CSV files with headers if they don't exist"""
        # Cloud costs file
        if not os.path.exists(self.costs_file):
            with open(self.costs_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'service', 'region', 'cost'])
            print(f"Created cloud_costs.csv file at {self.costs_file}")
        
        # Budget metrics file
        if not os.path.exists(self.budget_file):
            with open(self.budget_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['date', 'daily_total', 'daily_budget', 'monthly_budget', 'month_to_date'])
            print(f"Created budget_metrics.csv file at {self.budget_file}")

    def collect_costs(self):
        """Collect cost data from AWS Cost Explorer"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)  # Get a week of data for better visualization

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
            daily_totals = {}
            
            for result in response['ResultsByTime']:
                daily_total = 0
                date = result['TimePeriod']['Start']
                
                for group in result['Groups']:
                    service = group['Keys'][0]
                    region = group['Keys'][1]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    daily_total += cost
                    
                    costs.append({
                        'timestamp': date,
                        'service': service,
                        'region': region,
                        'cost': cost
                    })
                
                daily_totals[date] = daily_total

            # Store cost data in CSV
            if costs:
                # Read existing data
                existing_costs = pd.read_csv(self.costs_file)
                
                # Convert to DataFrame
                new_costs_df = pd.DataFrame(costs)
                
                # Remove dates we're going to replace
                dates_to_update = set(new_costs_df['timestamp'].unique())
                existing_costs = existing_costs[~existing_costs['timestamp'].isin(dates_to_update)]
                
                # Combine and write back
                combined_costs = pd.concat([existing_costs, new_costs_df], ignore_index=True)
                combined_costs.to_csv(self.costs_file, index=False)
                
                # Update budget metrics
                self.update_budget_metrics(daily_totals)
                
                print(f"Stored {len(costs)} cost records for {len(daily_totals)} days")
        except Exception as e:
            print(f"Error collecting costs: {e}")

    def update_budget_metrics(self, daily_totals):
        """Update the budget metrics CSV with daily totals and budget info"""
        try:
            monthly_budget = self.daily_budget * 30  # Approximate monthly budget
            
            # Calculate month to date total
            current_month = datetime.now().strftime('%Y-%m')
            costs_df = pd.read_csv(self.costs_file)
            month_costs = costs_df[costs_df['timestamp'].str.startswith(current_month)]
            month_to_date = month_costs['cost'].sum() if not month_costs.empty else 0
            
            # Read existing budget metrics
            if os.path.exists(self.budget_file):
                budget_df = pd.read_csv(self.budget_file)
            else:
                budget_df = pd.DataFrame(columns=['date', 'daily_total', 'daily_budget', 'monthly_budget', 'month_to_date'])
            
            # Create new budget data
            budget_data = []
            for date, total in daily_totals.items():
                budget_data.append({
                    'date': date,
                    'daily_total': total,
                    'daily_budget': self.daily_budget,
                    'monthly_budget': monthly_budget,
                    'month_to_date': month_to_date
                })
            
            # Create new DataFrame
            new_budget_df = pd.DataFrame(budget_data)
            
            # Remove dates we're going to replace
            dates_to_update = set(new_budget_df['date'].unique())
            budget_df = budget_df[~budget_df['date'].isin(dates_to_update)]
            
            # Combine and write back
            combined_budget = pd.concat([budget_df, new_budget_df], ignore_index=True)
            combined_budget.to_csv(self.budget_file, index=False)
        except Exception as e:
            print(f"Error updating budget metrics: {e}")

    def run(self):
        """Run the collector on a schedule"""
        interval = int(os.getenv('COLLECTOR_INTERVAL', 3600))  # Default to hourly
        schedule.every(interval).seconds.do(self.collect_costs)
        
        # Run immediately on startup
        print(f"Starting first collection...")
        self.collect_costs()
        
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == '__main__':
    collector = CloudCostCollector()
    collector.run()