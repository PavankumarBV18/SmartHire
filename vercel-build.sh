#!/bin/bash
echo "--- Starting Vercel Build ---"
echo "Current directory: $(pwd)"

# Install dependencies
echo "Installing Node dependencies..."
npm install

# Build CSS
echo "Building Tailwind CSS..."
npm run build

# Check output
if [ -f "static/css/output.css" ]; then
    echo "SUCCESS: static/css/output.css generated."
    ls -l static/css/output.css
else
    echo "ERROR: static/css/output.css not found!"
    exit 1
fi

echo "--- Build Finished ---"
