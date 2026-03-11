#!/bin/bash
# Docker entrypoint script for building Orbit with Conan 2.x
# This script is executed inside the Docker container

set -e  # Exit on error

# Ensure standard utilities are in PATH
export PATH="/usr/bin:/bin:/usr/local/bin:$PATH"

# Fix git dubious ownership warning (workspace is mounted from host)
git config --global --add safe.directory /workspace

# Default values
BUILD_TYPE="${BUILD_TYPE:-relwithdebinfo}"
STATIC_QT="${STATIC_QT:-false}"
BUILD_JOBS="${BUILD_JOBS:-}"

echo "========================================"
echo "Orbit Docker Build Environment (Conan 2.x)"
echo "========================================"
echo "Build Type: ${BUILD_TYPE}"
echo "Static Qt: ${STATIC_QT}"
if [ -n "$BUILD_JOBS" ]; then
    echo "Parallel Jobs: ${BUILD_JOBS}"
fi
echo "========================================"

# Ensure conan configuration is correct (in case cache was mounted)
echo "Setting up conan configuration..."
cd /workspace/third_party/conan/configs
./install.sh --assume-linux --force-public-remotes
cd /workspace

# Export local Orbit recipes to conan cache
echo "Exporting local conan recipes..."
if [ -f /workspace/third_party/conan/recipes/export_packages.sh ]; then
    bash /workspace/third_party/conan/recipes/export_packages.sh 2>&1 | grep -E "(Exporting|exported|Failed)" || true
    echo "Recipe export completed."
fi
cd /workspace

# Detect/create default profile
echo "Setting up conan profile..."
conan profile detect --force || conan profile detect

# Orbit's settings.yml may require os.platform and compiler.threads
echo "Configuring additional settings in profile..."
if grep -q "os=Linux" ~/.conan2/profiles/default; then
    if ! grep -q "os.platform" ~/.conan2/profiles/default; then
        sed -i '/^os=Linux$/a os.platform=None' ~/.conan2/profiles/default
    fi
fi
if grep -q "compiler=gcc" ~/.conan2/profiles/default || grep -q "compiler=clang" ~/.conan2/profiles/default; then
    if ! grep -q "compiler.threads" ~/.conan2/profiles/default; then
        sed -i '/^compiler\.libcxx=/a compiler.threads=posix' ~/.conan2/profiles/default
    fi
    if ! grep -q "compiler.exception" ~/.conan2/profiles/default; then
        sed -i '/^compiler\.threads=/a compiler.exception=seh' ~/.conan2/profiles/default
    fi
    if ! grep -q "compiler.fpo" ~/.conan2/profiles/default; then
        sed -i '/^compiler\.exception=/a compiler.fpo=None' ~/.conan2/profiles/default
    fi
fi

# Add buildenv to profile to ensure system tools are available
if ! grep -q "\[buildenv\]" ~/.conan2/profiles/default; then
    echo "" >> ~/.conan2/profiles/default
    echo "[buildenv]" >> ~/.conan2/profiles/default
fi
# Ensure /bin and /usr/bin are in PATH for builds (mv, cmake, etc.)
if ! grep -q "PATH=" ~/.conan2/profiles/default; then
    echo "PATH+=(path):/bin:/usr/bin" >> ~/.conan2/profiles/default
fi

# Verify cmake and mv are available
export PATH="/bin:/usr/bin:$PATH"
which cmake || echo "WARNING: cmake not found in PATH"
which mv || echo "WARNING: mv not found in PATH"

# Map build type to profile format
case "$BUILD_TYPE" in
    debug)
        PROFILE="default"
        BUILD_TYPE_CMAKE="Debug"
        ;;
    release)
        PROFILE="default"
        BUILD_TYPE_CMAKE="Release"
        ;;
    relwithdebinfo|*)
        PROFILE="default"
        BUILD_TYPE_CMAKE="RelWithDebInfo"
        ;;
esac

# Build directory name
BUILD_DIR="build_${BUILD_TYPE}"
BUILD_PATH="/workspace/$BUILD_DIR"

echo "========================================"
echo "Starting Conan 2.x build process..."
echo "Profile: $PROFILE"
echo "Build Type: $BUILD_TYPE_CMAKE"
echo "Build directory: $BUILD_DIR"
echo "========================================"

# The build directory is mounted as a writable volume from the host
# Just ensure it exists (should already be created by docker run)
[ ! -d "$BUILD_PATH" ] && echo "Warning: Build directory $BUILD_PATH doesn't exist!"

# Conan 2.x: Install dependencies
echo "Installing dependencies (will build from source if needed)..."
conan install /workspace \
    --output-folder="$BUILD_PATH" \
    --profile="$PROFILE" \
    --settings=build_type="$BUILD_TYPE_CMAKE" \
    --build=missing \
    --conf tools.system.package_manager:mode=install \
    --conf tools.system.package_manager:sudo=False

# Conan 2.x: Build Orbit
# Remove stale CMake cache to avoid referencing old Conan package paths
echo "Clearing CMake cache for fresh configure..."
rm -rf "$BUILD_PATH/CMakeCache.txt" "$BUILD_PATH/CMakeFiles"
echo "Building Orbit..."

# Set CMAKE_BUILD_PARALLEL_LEVEL to control parallel jobs if BUILD_JOBS is specified
if [ -n "$BUILD_JOBS" ]; then
    export CMAKE_BUILD_PARALLEL_LEVEL="$BUILD_JOBS"
    echo "Using $BUILD_JOBS parallel build jobs..."
fi

# In Conan 2.x, build from the output folder where generators were created
# Disable tests in Docker: integration tests need kernel access (perf_event_open, ptrace)
conan build /workspace \
    --output-folder="$BUILD_PATH" \
    --profile="$PROFILE" \
    --settings=build_type="$BUILD_TYPE_CMAKE" \
    -o run_tests=False

echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo "Binaries should be available at: build/$BUILD_TYPE_CMAKE/bin/"
echo ""
echo "Main binaries:"
echo "  - Orbit:        build/$BUILD_TYPE_CMAKE/bin/Orbit"
echo "  - OrbitService: build/$BUILD_TYPE_CMAKE/bin/OrbitService"
echo "========================================"
