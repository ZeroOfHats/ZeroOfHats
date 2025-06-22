# Using a specific version of Ollama for consistency
FROM ollama/ollama:0.1.32

# Expose the default Ollama port
EXPOSE 11434

# Default command (Ollama serves by default)
CMD ["serve"]

# Optional: Pre-pull a model (e.g., llama2)
# RUN ollama pull llama2
# Note: Pre-pulling models can make the initial image build larger and longer.
# It might be better to pull models dynamically after the container is running.
