FROM debian:bullseye

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required for Orbit
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    make \
    coreutils \
    perl \
    libglu1-mesa-dev \
    mesa-common-dev \
    libxmu-dev \
    libxi-dev \
    libopengl-dev \
    qtbase5-dev \
    qtwebengine5-dev \
    libqt5webchannel5-dev \
    libqt5websockets5-dev \
    libxxf86vm-dev \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Conan 2.x package manager
RUN pip3 install "conan>=2.0,<3.0"

# Set up working directory
WORKDIR /workspace

# Copy conan configuration installation script and configs
COPY third_party/conan/configs /tmp/conan-configs

# Install conan configuration (profiles, settings, etc.)
# This sets up the build profiles without needing the full source
RUN cd /tmp/conan-configs && \
    chmod +x install.sh && \
    ./install.sh --assume-linux --force-public-remotes && \
    rm -rf /tmp/conan-configs

# Copy the entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

