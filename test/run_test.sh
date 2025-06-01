#!/bin/bash

echo "Web2MD Token Usage Test Runner"
echo "=============================="

echo "Checking if web2md is running..."
if curl -s http://localhost:7001 > /dev/null 2>&1; then
    echo "✓ web2md is running at http://localhost:7001"
else
    echo "✗ web2md is not running at http://localhost:7001"
    echo ""
    echo "Please start web2md first:"
    echo "  Option 1 (Development): cd dev && ./run-services.sh && uvicorn main:app --host 0.0.0.0 --port 7001 --reload --env-file dev/.env"
    echo "  Option 2 (Docker): docker compose up -d"
    exit 1
fi

echo ""
echo "Starting token usage test..."
echo "This may take a few minutes depending on the number of queries..."
echo ""

cd "$(dirname "$0")"
python3 token_usage_test.py

echo ""
echo "Test completed! Check token_usage_results.json for detailed results."