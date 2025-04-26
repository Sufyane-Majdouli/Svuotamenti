#!/bin/bash

# This script is run during Vercel build

# Create necessary directories
mkdir -p Svuotamenti/app/static/css
mkdir -p Svuotamenti/app/static/js
mkdir -p Svuotamenti/app/static/uploads

# Print debugging information
echo "Current directory: $(pwd)"
echo "Directory listing: $(ls -la)"
echo "Python version: $(python --version)"
echo "Installed packages: $(pip list)"

# Exit with success
exit 0 