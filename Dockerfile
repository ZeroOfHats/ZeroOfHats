# Phase 1: Foundation & Core Integration
# Base Image: NVIDIA CUDA image with Kali Linux tools overlaid

FROM nvidia/cuda:12.1.1-devel-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends     gnupg     curl     wget     git     python3     python3-pip     python3-venv     lsb-release     apt-transport-https     ca-certificates     && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://http.kali.org/kali/archive-key.asc | apt-key add -
RUN echo "deb https://http.kali.org/kali kali-rolling main non-free contrib" > /etc/apt/sources.list.d/kali.list

RUN apt-get update && apt-get install -y --no-install-recommends     kali-linux-core  && rm -rf /var/lib/apt/lists/*

RUN nvcc --version

LABEL maintainer="Jules for Project Agent Zero"
LABEL description="Agent Zero with Ollama, ChromaDB, GPU support on Kali Linux (via NVIDIA CUDA base)."

WORKDIR /app

# Install Agent Zero and its dependencies
COPY ./agent_zero /app/agent_zero
COPY ./0README.txt /app/0README.txt
RUN pip3 install --no-cache-dir -r /app/agent_zero/requirements.txt

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh
# Ollama models will be stored in /root/.ollama by default if OLLAMA_MODELS is not set.
# For offline use, ensure desired models are pulled into the mounted /root/.ollama volume.
# Example: Once the container is running with the volume mount, execute inside the container:
# docker exec -it <container_name> ollama pull llama2

# Install ChromaDB
RUN pip3 install --no-cache-dir chromadb

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

# CMD is inherited from nvidia/cuda base or can be overridden.
# For now, keeping bash for interactive checks.
CMD ["bash"]
