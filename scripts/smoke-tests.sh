#!/bin/bash
# Smoke tests for API endpoints

set -e

API_URL=${1:-http://localhost:5000}
API_KEY=${API_KEY:-dev-api-key}

echo "Running smoke tests against: $API_URL"

# Health check
echo "✓ Testing /health..."
curl -f "$API_URL/health" || { echo "✗ Health check failed"; exit 1; }

# API docs
echo "✓ Testing /api/v1/docs..."
curl -f "$API_URL/api/v1/docs" || { echo "✗ API docs failed"; exit 1; }

# Initialize system
echo "✓ Testing /api/v1/anc/initialize..."
curl -f -X POST "$API_URL/api/v1/anc/initialize" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sample_rate": 44100, "algorithm": "nlms"}' || { echo "✗ Initialize failed"; exit 1; }

# Get status
echo "✓ Testing /api/v1/anc/status..."
curl -f "$API_URL/api/v1/anc/status" \
  -H "X-API-Key: $API_KEY" || { echo "✗ Status check failed"; exit 1; }

echo ""
echo "✓ All smoke tests passed!"
