#!/bin/bash

# AccessBrailleRAP build script - No venv activation needed
# Usage: ./build.sh [target] or npm run build[target]
# Targets: debian, ubuntu, rpi, rpm, portable

set -e

TARGET=${1:-debian}

echo "=========================================="
echo "Building AccessBrailleRAP for: $TARGET"
echo "=========================================="

# Ensure Python dependencies are installed
echo "Installing Python dependencies..."
pip install -q -r requirement.txt

# Build based on target
case $TARGET in
  debian)
    echo "Building Debian package..."
    npm run builddebian
    ;;
  ubuntu)
    echo "Building Ubuntu package..."
    npm run buildubuntu
    ;;
  rpi)
    echo "Building Raspberry Pi package..."
    npm run buildrpi
    ;;
  rpm)
    echo "Building RPM package..."
    npm run buildrpm
    ;;
  portable)
    echo "Building portable executable..."
    npm run buildportable
    ;;
  *)
    echo "Unknown target: $TARGET"
    echo "Valid targets: debian, ubuntu, rpi, rpm, portable"
    exit 1
    ;;
esac

echo ""
echo "=========================================="
echo "✓ Build completed successfully!"
echo "=========================================="

if [ "$TARGET" = "rpm" ]; then
  echo "Output: ./dist/*.rpm"
elif [ "$TARGET" = "portable" ]; then
  echo "Output: ./dist/accessbraillerap"
else
  echo "Output: ./dist/*.deb"
fi
