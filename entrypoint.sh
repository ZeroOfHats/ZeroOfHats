#!/bin/bash
set -e

# Start Ollama server in the background
echo "Starting Ollama server..."
ollama serve &
ollama_pid=$!
echo "Ollama server PID: $ollama_pid"

# Wait for Ollama to be ready
echo "Waiting for Ollama server to be ready..."
while true; do
  if curl -s http://localhost:11434 > /dev/null; then
    echo "Ollama server is ready."
    break
  else
    echo "Ollama not yet available, sleeping for 2 seconds..."
    sleep 2
  fi
done

# (Optional) If OLLAMA_DEFAULT_MODEL is set and no models are found, pull that model.
if [ -n "$OLLAMA_DEFAULT_MODEL" ]; then
  echo "Checking for existing models..."
  if ! ollama list | grep -q "$OLLAMA_DEFAULT_MODEL"; then
    echo "Default model $OLLAMA_DEFAULT_MODEL not found. Pulling it..."
    ollama pull "$OLLAMA_DEFAULT_MODEL"
  else
    echo "Default model $OLLAMA_DEFAULT_MODEL already exists."
  fi
else
  echo "OLLAMA_DEFAULT_MODEL not set, skipping model pull."
fi

# Set Agent Zero environment variables
# OLLAMA_BASE_URL is already defaulted by Agent Zero to http://127.0.0.1:11434 if not set.
# export OLLAMA_BASE_URL="http://localhost:11434" # Explicitly set if needed

echo "Starting Agent Zero Web UI..."
# Ensure we are in the correct directory
cd /opt/agent-zero
exec python3 run_ui.py

# Keep the script running if run_ui.py exits, or manage Ollama's lifecycle
# For now, if run_ui.py exits, the container will exit.
# To keep Ollama running, we might need to wait for its PID:
# wait $ollama_pid
# However, with exec, this script will no longer be running to execute wait.
# Proper signal handling and process supervision for ollama would require a more complex setup
# if python3 run_ui.py was not the main foreground process.
# Given python3 run_ui.py is the main app, exec is appropriate for it to receive signals.
