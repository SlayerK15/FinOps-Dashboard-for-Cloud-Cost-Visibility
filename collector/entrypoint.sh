#!/bin/bash

# Wait for SQLite database directory to be ready
while [ ! -d "/app/data" ]; do
    echo "Waiting for data directory to be ready..."
    sleep 2
done

# Start the collector
python collector.py 