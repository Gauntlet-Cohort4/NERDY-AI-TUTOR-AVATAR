#!/usr/bin/env bash
set -e

echo "=== Python Linting (ruff) ==="
cd "$(dirname "$0")/../agent"
ruff check .
ruff format --check .
echo "✓ Python linting passed"

echo ""
echo "=== TypeScript Type Check ==="
cd "$(dirname "$0")/../frontend"
npx tsc --noEmit
echo "✓ TypeScript type check passed"

echo ""
echo "=== ESLint ==="
npx eslint .
echo "✓ ESLint passed"

echo ""
echo "=== All linting passed ==="
