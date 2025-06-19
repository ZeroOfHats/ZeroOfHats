# Agent Zero with Ollama Integration Plan

This document outlines the plan for creating a Docker image that combines Agent Zero and Ollama for local LLM inference.

## Phase 1: Research and Planning

**Objective:** Understand Agent Zero and Ollama, their integration, and Docker best practices.

**Findings:**

*   **Agent Zero Configuration:**
    *   Agent Zero uses the `OLLAMA_BASE_URL` environment variable to connect to an Ollama instance. The default value is `http://127.0.0.1:11434`.
    *   Agent Zero's Web UI port is configurable via `WEB_UI_PORT`, defaulting to `50001`.
*   **Ollama Docker:**
    *   Official Docker image: `ollama/ollama`.
    *   Models are stored in `/root/.ollama` within the container.
    *   Ollama API is on port `11434`.
*   **Multi-Service Containers:** An entrypoint script will be used to manage both services.

**Plan (as approved):**

1.  *Research Agent Zero Configuration for Ollama.* (Completed)
    *   Examine the `frdel/agent-zero` GitHub repository, specifically the `example.env` file and any documentation related to LLM provider configuration.
    *   Determine the exact environment variables or configuration file changes needed to make Agent Zero use a local Ollama instance at `http://localhost:11434`.
2.  *Create `docs/` directory and Initial Markdown Document.* (Current)
    *   Create a `docs/` directory.
    *   Create a markdown file (e.g., `docs/ollama_integration_plan.md`) to document research findings and the evolving plan.
3.  *Develop the Dockerfile.*
    *   Use `ollama/ollama` as the base image.
    *   Install Python and other necessary dependencies for Agent Zero.
    *   Clone the `frdel/agent-zero` repository into the Docker image (e.g., into `/opt/agent-zero`).
    *   Install Agent Zero's Python dependencies from `requirements.txt`.
    *   Set up the working directory (e.g., `/opt/agent-zero`).
    *   Expose port 11434 for Ollama and port 50001 for Agent Zero's web UI.
    *   Copy the `entrypoint.sh` script into the image and set it as the `ENTRYPOINT`.
4.  *Develop the `entrypoint.sh` Script.*
    *   Start the Ollama server in the background (`ollama serve &`).
    *   Implement a loop that waits for Ollama to be ready (e.g., `curl http://localhost:11434` or `ollama list`).
    *   (Optional) If `OLLAMA_DEFAULT_MODEL` is set and no models are found, pull that model.
    *   Set Agent Zero environment variables (e.g., `OLLAMA_BASE_URL`).
    *   Start Agent Zero's web UI (`python run_ui.py`).
5.  *Update `README.md`.*
    *   Instructions for building and running the Docker image (including volume mounts for models and port mappings).
    *   Basic usage and troubleshooting.
6.  *Testing and Refinement.*
    *   Build, run, and test the container.
    *   Verify API and UI accessibility.
7.  *Submit the changes.*
