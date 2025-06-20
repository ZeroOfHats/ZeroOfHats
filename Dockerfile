# Phase 1: Foundation & Core Integration (Extended for Phase 3)
# Base Image: NVIDIA CUDA image with Kali Linux tools overlaid

FROM nvidia/cuda:12.1.1-devel-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Install prerequisites for adding Kali repository and basic tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    lsb-release \
    apt-transport-https \
    ca-certificates \
    # For Xvfb, if needed for headless, though modern Chrome often doesn't require it
    xvfb \
    # Fonts for browser rendering
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Add Kali Linux repository
RUN curl -fsSL https://http.kali.org/kali/archive-key.asc | apt-key add -
RUN echo "deb https://http.kali.org/kali kali-rolling main non-free contrib" > /etc/apt/sources.list.d/kali.list

# Update package lists again to include Kali packages and install Kali core tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    kali-linux-core \
    && rm -rf /var/lib/apt/lists/*

# Verify CUDA is accessible
RUN nvcc --version

# --- Phase 3 Additions: Selenium & Headless Chrome ---
# Install Chromium Browser from Ubuntu repos (more stable than trying to force Kali's if base is Ubuntu)
RUN apt-get update && apt-get install -y chromium-browser \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
# This is tricky due to version matching. We'll try to get a recent stable one.
# Option 1: Install via apt if a 'chromium-chromedriver' package matches.
# Option 2: Download specific version. Let's try apt first.
RUN apt-get update && apt-get install -y chromium-chromedriver \
    && rm -rf /var/lib/apt/lists/*

# As a fallback, or if specific version needed, one might download from:
# https://googlechromelabs.github.io/chrome-for-testing/ or https://chromedriver.chromium.org/downloads
# Example for a specific version (e.g., if chromium-browser is version 120):
# ARG CHROMEDRIVER_VERSION=120.0.6099.71 # Example, find this dynamically or fix
# RUN wget -q https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip -P /tmp \
#    && unzip /tmp/chromedriver-linux64.zip -d /tmp \
#    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
#    && chmod +x /usr/local/bin/chromedriver \
#    && rm -rf /tmp/chromedriver-linux64.zip /tmp/chromedriver-linux64
# For now, relying on 'chromium-chromedriver' from apt for simplicity.

# Check versions (optional, for debugging build)
RUN command -v chromium-browser && chromium-browser --version || echo "Chromium not found or version check failed"
RUN command -v chromedriver && chromedriver --version || echo "ChromeDriver not found or version check failed"
# --- End of Phase 3 Additions ---

LABEL maintainer="Jules for Project Agent Zero"
LABEL description="Agent Zero with Ollama, ChromaDB, GPU support, Web Scraping on Kali Linux (via NVIDIA CUDA base)."

WORKDIR /app

# Copy 0README first so changes to it don't invalidate agent_zero cache layer as much
COPY ./0README.txt /app/0README.txt

# Install Agent Zero and its dependencies
COPY ./agent_zero /app/agent_zero
# requirements.txt will be updated by the next step to include selenium, beautifulsoup4
RUN pip3 install --no-cache-dir -r /app/agent_zero/requirements.txt

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh
# Ollama models will be stored in /root/.ollama by default if OLLAMA_MODELS is not set.
# For offline use, ensure desired models are pulled into the mounted /root/.ollama volume.
# Example: Once the container is running with the volume mount, execute inside the container:
# docker exec -it <container_name> ollama pull llama2

# Install ChromaDB
RUN pip3 install --no-cache-dir chromadb # Already here, ensure it stays

# Create directories for persistent data
# These paths are intended to be used as volume mount points from the host.
RUN mkdir -p /root/.ollama
RUN mkdir -p /agent_data/chroma

# Expose Ollama port (default is 11434)
EXPOSE 11434

# Documentation for volume mounting (to be included in README or 0README.txt):
# To persist Ollama models (and ensure they are available offline after initial pull):
#   -v /your/local/path/to/ollama_models:/root/.ollama
# To persist ChromaDB data:
#   -v /your/local/path/to/chroma_data:/agent_data/chroma

CMD ["bash"]
