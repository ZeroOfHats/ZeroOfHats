# Use ollama/ollama as the base image
FROM ollama/ollama

# Install Python and other necessary dependencies for Agent Zero
RUN apt-get update && \
    apt-get install -y python3 python3-pip git && \
    rm -rf /var/lib/apt/lists/*

# Clone the frdel/agent-zero repository into the Docker image
RUN git clone https://github.com/frdel/agent-zero.git /opt/agent-zero

# Install Agent Zero's Python dependencies
WORKDIR /opt/agent-zero
RUN pip3 install --no-cache-dir -r requirements.txt

# Set up the working directory
WORKDIR /opt/agent-zero

# Expose port 11434 for Ollama and port 50001 for Agent Zero's web UI
EXPOSE 11434
EXPOSE 50001

# Copy the entrypoint.sh script into the image and set it as the ENTRYPOINT
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# CMD is not strictly needed here as entrypoint.sh runs ollama serve
# and then the python app, but it's good practice to have one.
# However, entrypoint.sh is an exec script, so CMD won't be used.
# We can remove the previous CMD ["ollama", "serve"] or leave it commented.
