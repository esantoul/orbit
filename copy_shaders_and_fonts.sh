#!/bin/bash
# Script to copy shader and font files from Conan cache to build directory
# Works both in Docker (where cache is at /root/.conan2) and on host

set -e

BUILD_BIN_DIR="${1}"
if [ -z "$BUILD_BIN_DIR" ]; then
    echo "Usage: $0 <build_bin_directory>"
    echo "Example: $0 /workspace/build/RelWithDebInfo/bin"
    exit 1
fi

echo "Copying shaders and fonts to ${BUILD_BIN_DIR}..."

# Determine Conan cache location
# In Docker: /root/.conan2
# On host: ~/.conan2 or .docker-conan2-cache
CONAN_CACHE_DIRS=()
if [ -d "/root/.conan2" ]; then
    CONAN_CACHE_DIRS+=("/root/.conan2")
fi
if [ -d "$HOME/.conan2" ]; then
    CONAN_CACHE_DIRS+=("$HOME/.conan2")
fi
# Check for mounted Docker cache
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || pwd)"
if [ -d "${SCRIPT_DIR}/.docker-conan2-cache" ]; then
    CONAN_CACHE_DIRS+=("${SCRIPT_DIR}/.docker-conan2-cache")
fi

# Find shader files in Conan cache
SHADER_SOURCE=""
for CACHE_DIR in "${CONAN_CACHE_DIRS[@]}"; do
    SHADER_SOURCE=$(find "$CACHE_DIR" -path "*/p/shaders/v3f-t2f-c4f.vert" -type f 2>/dev/null | head -1)
    if [ -n "$SHADER_SOURCE" ]; then
        break
    fi
    SHADER_SOURCE=$(find "$CACHE_DIR" -path "*/b/src/shaders/v3f-t2f-c4f.vert" -type f 2>/dev/null | head -1)
    if [ -n "$SHADER_SOURCE" ]; then
        break
    fi
done

# Find font file in Conan cache
FONT_SOURCE=""
for CACHE_DIR in "${CONAN_CACHE_DIRS[@]}"; do
    FONT_SOURCE=$(find "$CACHE_DIR" -path "*/p/fonts/Vera.ttf" -type f 2>/dev/null | head -1)
    if [ -n "$FONT_SOURCE" ]; then
        break
    fi
    FONT_SOURCE=$(find "$CACHE_DIR" -path "*/b/src/fonts/Vera.ttf" -type f 2>/dev/null | head -1)
    if [ -n "$FONT_SOURCE" ]; then
        break
    fi
done

if [ -z "$SHADER_SOURCE" ]; then
    echo "Error: Could not find shader files in Conan cache"
    echo "Searched in: ${CONAN_CACHE_DIRS[*]}"
    exit 1
fi

# Create directories
mkdir -p "${BUILD_BIN_DIR}/shaders"
mkdir -p "${BUILD_BIN_DIR}/fonts"

# Copy shader files
SHADER_DIR=$(dirname "${SHADER_SOURCE}")
cp "${SHADER_DIR}/v3f-t2f-c4f.vert" "${BUILD_BIN_DIR}/shaders/"
cp "${SHADER_DIR}/v3f-t2f-c4f.frag" "${BUILD_BIN_DIR}/shaders/"
echo "Copied shader files from ${SHADER_DIR}"

# Copy font file if found
if [ -n "$FONT_SOURCE" ]; then
    cp "${FONT_SOURCE}" "${BUILD_BIN_DIR}/fonts/"
    echo "Copied font file from $(dirname "${FONT_SOURCE}")"
else
    echo "Warning: Font file not copied (may cause font errors)"
fi

echo "Done! Files copied to:"
echo "  - ${BUILD_BIN_DIR}/shaders/"
echo "  - ${BUILD_BIN_DIR}/fonts/"

