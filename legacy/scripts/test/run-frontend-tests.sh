#!/bin/bash
# Run frontend unit tests with coverage

set -e

echo "Running frontend unit tests..."

cd frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Run Jest tests
npm run test:coverage

echo ""
echo "Coverage report generated in frontend/coverage/"


