#!/bin/bash
# Build Orbit using Docker
# This script mounts the source code and runs the build in a container

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
IMAGE_NAME="orbit-build-env:latest"

# Default values
BUILD_TYPE="relwithdebinfo"
STATIC_QT="false"
BUILD_JOBS=""  # Empty means use default (all cores)

# Function to display usage
show_usage() {
    cat <<EOF
Usage: $0 [BUILD_TYPE] [OPTIONS]

Build Orbit in a Docker container.

BUILD_TYPE:
  debug              Build in debug mode
  release            Build in release mode
  relwithdebinfo     Build with release optimizations and debug info (default)

OPTIONS:
  --static-qt        Build with static Qt (portable binary, takes 2-4 hours)
  --jobs N           Limit parallel build jobs to N (default: use all cores)
  --help             Show this help message

EXAMPLES:
  $0                           # Build relwithdebinfo with dynamic Qt
  $0 release                   # Build release with dynamic Qt
  $0 --static-qt               # Build relwithdebinfo with static Qt
  $0 release --static-qt       # Build release with static Qt
  $0 --jobs 4                  # Build with 4 parallel jobs (reduces RAM usage)
  $0 release --jobs 8          # Build release with 8 parallel jobs

NOTES:
  - First run: ./docker-build-env.sh to create the build environment image
  - Source code is mounted read-only from the current directory
  - Build output appears in build_default_<buildtype>/ directory
  - Static Qt builds take 2-4 hours on first build, ~30-60 min subsequently

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        debug|release|relwithdebinfo)
            BUILD_TYPE="$1"
            shift
            ;;
        --static-qt)
            STATIC_QT="true"
            shift
            ;;
        --jobs)
            if [[ -z "$2" ]] || [[ "$2" =~ ^- ]]; then
                echo "Error: --jobs requires a numeric argument"
                exit 1
            fi
            BUILD_JOBS="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            ;;
        *)
            echo "Error: Unknown argument '$1'"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# Check if the build environment image exists
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Error: Build environment image '$IMAGE_NAME' not found!"
    echo ""
    echo "Please run './docker-build-env.sh' first to create the build environment."
    exit 1
fi

BUILD_DIR="build_${BUILD_TYPE}"
if [ "$STATIC_QT" = "true" ]; then
    BUILD_DIR="${BUILD_DIR}_static_qt"
fi

echo "========================================"
echo "Orbit Docker Build (Conan 2.x)"
echo "========================================"
echo "Build Type: $BUILD_TYPE"
echo "Static Qt: $STATIC_QT"
echo "Build Directory: $BUILD_DIR"
if [ -n "$BUILD_JOBS" ]; then
    echo "Parallel Jobs: $BUILD_JOBS"
fi
echo "========================================"

# Create build directory on host if it doesn't exist
mkdir -p "$SCRIPT_DIR/$BUILD_DIR"

# Create a persistent conan 2.x cache directory
# This speeds up rebuilds by caching downloaded dependencies
CONAN_CACHE_DIR="$SCRIPT_DIR/.docker-conan2-cache"
mkdir -p "$CONAN_CACHE_DIR"

echo "Starting Docker container..."
echo ""

# Run the Docker container with mounted volumes (Conan 2.x uses .conan2)
# Note: workspace is mounted as rw to allow CMakeUserPresets.json generation
docker run --rm \
    -v "$SCRIPT_DIR:/workspace:rw" \
    -v "$CONAN_CACHE_DIR:/root/.conan2:rw" \
    -e BUILD_TYPE="$BUILD_TYPE" \
    -e STATIC_QT="$STATIC_QT" \
    -e BUILD_JOBS="$BUILD_JOBS" \
    "$IMAGE_NAME"

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo "Binaries are available at:"
echo "  $BUILD_DIR/bin/"
echo ""
echo "Main executables:"
echo "  - Frontend: $BUILD_DIR/bin/Orbit"
echo "  - Service:  $BUILD_DIR/bin/OrbitService"
echo "========================================"

