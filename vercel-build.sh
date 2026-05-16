#!/bin/bash
# Install Node dependencies
npm install

# Build Tailwind CSS
npm run build

# Verify build output
if [ -f "static/css/output.css" ]; then
    echo "Tailwind build successful: static/css/output.css generated."
else
    echo "ERROR: Tailwind build failed. static/css/output.css not found."
    exit 1
fi
