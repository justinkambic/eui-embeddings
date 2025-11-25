#!/bin/bash
# Run Python unit tests with coverage

set -e

echo "Running Python unit tests..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run pytest with coverage
pytest tests/unit/python/ \
    -v \
    --cov=. \
    --cov-report=html:htmlcov/python \
    --cov-report=term-missing \
    --cov-exclude=tests/* \
    --cov-exclude=venv/* \
    --cov-exclude=*/__pycache__/* \
    --tb=short

echo ""
echo "Coverage report generated in htmlcov/python/index.html"


