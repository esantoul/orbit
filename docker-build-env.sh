#!/bin/bash
# Build the Orbit Docker build environment image
# This only needs to be run once, or when dependencies change

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
IMAGE_NAME="orbit-build-env:latest"

echo "========================================"
echo "Building Orbit Build Environment Image"
echo "========================================"
echo "Image: $IMAGE_NAME"
echo "This may take a few minutes..."
echo "========================================"

# Build the Docker image
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"

echo "========================================"
echo "Build environment image created successfully!"
echo "========================================"
echo "Image: $IMAGE_NAME"
echo ""
echo "Next steps:"
echo "  Run './docker-build.sh' to build Orbit"
echo "  Run './docker-build.sh --help' for usage information"
echo "========================================"

