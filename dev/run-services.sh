#!/bin/bash

docker compose -f docker-compose.yaml up -d searxng browserless

echo "SearXNG is running at http://localhost:7002"
echo "Browserless is running at http://localhost:7003"
echo ""
echo "You can now run the FastAPI application locally with:"
echo "uvicorn main:app --host 0.0.0.0 --port 7001 --reload --env-file dev/.env"
