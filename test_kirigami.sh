#!/bin/bash
# Quick test script for Kirigami settings window

cd "$(dirname "$0")"

echo "Testing Kirigami Settings Window..."
echo "Press Ctrl+C to close"
echo

python3 -m blaze.kirigami_integration
