# FinOps Dashboard

A Docker-based FinOps dashboard that collects and visualizes cloud costs using Grafana and a Python collector.

## Prerequisites

- Docker
- Docker Compose
- AWS credentials with Cost Explorer access

## Setup

1. Clone this repository
2. Copy the `.env.example` file to `.env` and fill in your AWS credentials:
   ```bash
   cp .env.example .env
   ```
3. Edit the `.env` file and add your AWS credentials:
   ```
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=your_region
   ```

## Running the Dashboard

1. Start the services:
   ```bash
   docker-compose up -d
   ```

2. Access the dashboard:
   - Grafana: http://localhost:3000
   - Default credentials: admin/admin

## Components

### Collector Service
- Python-based service that collects cost data from AWS Cost Explorer
- Stores data in SQLite database
- Runs on a configurable interval (default: 5 minutes)

### Grafana
- Visualizes the collected cost data
- Pre-configured dashboard with:
  - Cloud costs by service
  - Cloud costs by region
- Auto-provisioned datasource and dashboard

## Data Storage

- SQLite database: `./data/sqlite/cloud_costs.db`
- Grafana data: `./data/grafana/`

## Configuration

- Edit `.env` file to modify:
  - AWS credentials
  - Collection interval
  - Grafana credentials
  - Database paths

## Troubleshooting

1. Check container logs:
   ```bash
   docker-compose logs -f
   ```

2. Verify AWS credentials in `.env` file

3. Ensure Cost Explorer API is enabled in your AWS account

## License

MIT 