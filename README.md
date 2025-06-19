# Agent Zero with Ollama Docker Image

This repository provides a Dockerized setup for running Agent Zero with a local Ollama instance for LLM inference.

## Features

*   Combines Agent Zero and Ollama in a single Docker container.
*   Uses an entrypoint script to manage both services.
*   Allows local LLM model usage with Agent Zero.
*   Configurable default model pull on startup.

## Prerequisites

*   Docker installed on your system.
*   (Optional) An Ollama-compatible model file if you want to preload models without pulling.

## Project Structure

```
.
├── Dockerfile              # Defines the Docker image
├── entrypoint.sh           # Script to start Ollama and Agent Zero
├── docs/
│   └── ollama_integration_plan.md # Research and planning document
└── README.md               # This file
```

## Building the Docker Image

1.  **Clone the repository (or ensure you have the `Dockerfile` and `entrypoint.sh`):**
    ```bash
    # If you are developing this, you likely already have it.
    # Otherwise, for a user:
    # git clone <repository_url>
    # cd <repository_name>
    ```

2.  **Build the Docker image:**
    ```bash
    docker build -t agent-zero-ollama .
    ```

## Running the Docker Container

To run the container, you need to map ports for Ollama (11434) and Agent Zero's Web UI (50001). You should also mount a volume to persist Ollama models.

```bash
docker run -d \
  --name agent-zero-ollama-container \
  -p 11434:11434 \
  -p 50001:50001 \
  -v ollama_data:/root/.ollama \
  agent-zero-ollama
```

**Alternative: Mounting a local host directory for models**

If you prefer to manage your Ollama models directly on your host filesystem, you can mount a local directory instead of using a Docker named volume. Replace `/path/to/your/ollama_models` with the actual path on your host:

```bash
docker run -d \
  --name agent-zero-ollama-container \
  -p 11434:11434 \
  -p 50001:50001 \
  -v /path/to/your/ollama_models:/root/.ollama \
  agent-zero-ollama
```
Ensure that the directory `/path/to/your/ollama_models` exists on your host machine.

**Explanation of options:**

*   `-d`: Run the container in detached mode (in the background).
*   `--name agent-zero-ollama-container`: Assign a name to the container for easier management.
*   `-p 11434:11434`: Map port 11434 on your host to port 11434 in the container (for Ollama).
*   `-p 50001:50001`: Map port 50001 on your host to port 50001 in the container (for Agent Zero Web UI).
*   `-v ollama_data:/root/.ollama`: Mount a Docker volume named `ollama_data` to `/root/.ollama` inside the container. This is where Ollama stores its models, so they persist across container restarts. Docker will create the volume if it doesn't exist.
*   `agent-zero-ollama`: The name of the image you built.

**Optional: Pulling a specific model on startup**

You can specify a model for Ollama to pull when the container starts by setting the `OLLAMA_DEFAULT_MODEL` environment variable.

```bash
docker run -d \
  --name agent-zero-ollama-container \
  -p 11434:11434 \
  -p 50001:50001 \
  -v ollama_data:/root/.ollama \
  -e OLLAMA_DEFAULT_MODEL=llama3 \
  agent-zero-ollama
```
This will pull the `llama3` model if it's not already present in the mounted volume/directory.

## Accessing Services

*   **Ollama API:** Available at `http://localhost:11434` on your host machine.
*   **Agent Zero Web UI:** Available at `http://localhost:50001` on your host machine.

## Basic Usage

1.  Start the container as described above.
2.  Wait for Ollama to download any specified model (if applicable). You can check container logs: `docker logs agent-zero-ollama-container`.
3.  Open your web browser and navigate to `http://localhost:50001` to access Agent Zero.
4.  Agent Zero should automatically connect to the local Ollama instance. If you need to configure the LLM provider in Agent Zero, ensure it's set to use `http://localhost:11434` as the Ollama base URL (this is typically the default for Agent Zero when `OLLAMA_BASE_URL` is not set, or you can set `OLLAMA_BASE_URL="http://127.0.0.1:11434"` in the `entrypoint.sh` or via `-e` in `docker run`).

## Troubleshooting

*   **Check container logs:**
    ```bash
    docker logs agent-zero-ollama-container
    ```
*   **Access Ollama CLI inside the container:**
    ```bash
    docker exec -it agent-zero-ollama-container ollama list
    docker exec -it agent-zero-ollama-container ollama pull <model_name>
    ```
*   **Ensure ports are not already in use on your host.**

## Development Notes (from `ollama_integration_plan.md`)

This project was developed following a plan which included:
1.  Researching Agent Zero and Ollama configuration.
2.  Creating documentation (`docs/ollama_integration_plan.md`).
3.  Developing the `Dockerfile` using `ollama/ollama` as a base, installing Python, cloning Agent Zero, and setting up dependencies.
4.  Developing the `entrypoint.sh` script to manage Ollama and Agent Zero services.
5.  Updating this `README.md`.

---

*This README was generated as part of an AI-assisted development process.*
