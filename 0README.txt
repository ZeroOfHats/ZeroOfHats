# 0README.txt - Project Agent Zero (Local GPU Edition)

## 1. Overview

Welcome to Agent Zero (Local GPU Edition)! This project provides a fully self-contained, offline-capable AI agent system that leverages local GPU resources for optimal performance. It integrates Ollama for Large Language Model (LLM) support and ChromaDB for local vector memory (though ChromaDB integration is primarily for later phases).

This `0README.txt` file is your primary guide to understanding, running, and interacting with the system. Meta Agent 0, an agent within the system, can help you parse and understand this document. (Future capability: Meta Agent 0 will also aim to search for and understand other README files within the container as a source for its self-play and learning).

**Core Principles:**
- **Fully Local & Offline:** All components (Agent Zero, Ollama, models, vector stores) run entirely on your local machine. No internet connection is required after initial setup and model download.
- **GPU Accelerated:** Designed to utilize NVIDIA GPUs via Ollama for LLM inference, significantly speeding up agent reasoning and generation tasks.
- **CPU Fallback/Balancing:** Smaller utility LLMs can be configured to run on the CPU, conserving VRAM for larger chat/reasoning models on the GPU.
- **Persistent Memory:** Ollama models and ChromaDB vector stores (future) are persisted locally using Docker volume mounts.
- **Extensible Agent Architecture:** Supports self-play, custom agent archetypes (future), and continuous learning (future).

## 2. System Setup & Running

### 2.1. Prerequisites
- Docker installed on your system.
- NVIDIA GPU with appropriate drivers installed on the host.
- `nvidia-container-toolkit` installed on the host to enable GPU access for Docker containers.
- Sufficient disk space for Docker images and Ollama models.

### 2.2. Building the Docker Image
Navigate to the project root directory (where this `0README.txt` and the `Dockerfile` are located) and run:
```bash
docker build -t agent-zero-gpu .
```

### 2.3. Running the Docker Container
To run the container with GPU access and persistent storage:

```bash
# Create local directories for Ollama models and ChromaDB data (if they don't exist)
mkdir -p ./ollama_models
mkdir -p ./chroma_data
# Note: Replace ./ollama_models and ./chroma_data with absolute paths if preferred.

docker run --gpus all -it \
  -v $(pwd)/ollama_models:/root/.ollama \
  -v $(pwd)/chroma_data:/agent_data/chroma \
  -p 11434:11434 \
  agent-zero-gpu bash
```
- `--gpus all`: Provides the container access to all host NVIDIA GPUs.
- `-v $(pwd)/ollama_models:/root/.ollama`: Mounts your local `./ollama_models` directory into the container where Ollama stores its models. This makes your models persistent.
- `-v $(pwd)/chroma_data:/agent_data/chroma`: Mounts your local `./chroma_data` directory for ChromaDB's persistent storage (used in later phases).
- `-p 11434:11434`: Exposes Ollama's API port to your host machine.

### 2.4. Initial Ollama Model Download (One-Time Setup)
Inside the running container (from the `bash` prompt obtained above), you need to pull the Ollama models that Agent Zero will use. You only need to do this once per model, as they will be saved in your mounted `ollama_models` directory.

**Recommended Models (Reflecting User Preferences & Agent Zero Configuration):**

*   **Primary Chat Model (GPU-focused):**
    ```bash
    ollama pull mistral:7b-instruct-q5_K_M
    ```
    *(This is the primary recommendation for chat tasks. Agent Zero's default chat model list can be configured during Agent initialization if alternatives like `llama2:7b-chat-q5_K_M` are preferred.)*
*   **Primary Utility Model (CPU-focused):**
    ```bash
    ollama pull tinydolphin:1.1b-q4_K_M
    ```
    *(This is the primary recommendation for utility tasks. Alternatives like `orca-mini:3b-q4_K_M` or `phi:2.7b-chat-q4_K_M` can also be used and configured in Agent Zero.)*
*   **Primary Embedding Model (for RAG - Phase 3):**
    ```bash
    ollama pull nomic-embed-text:latest
    ```
    *(Alternative lightweight embedding model: `all-minilm:l6-v2`)*

You can pull other models as Agent Zero's configuration allows for customization during Agent initialization.

### 2.5. Starting Services within the Container
Agent Zero relies on Ollama. Start the Ollama service in the background:
```bash
ollama serve &
```
Wait a few seconds for it to initialize. You can check its status or logs if needed.

## 3. Interacting with Agent Zero

### 3.1. Meta Agent 0 (Understanding the System)
Meta Agent 0 helps you understand this `0README.txt` file and the system's capabilities. To use it:

1.  Navigate to the application directory (if not already there): `cd /app`
2.  Use Python interactively (ensure Ollama is running):
    ```python
    from agent_zero.meta_agent_0.core import MetaAgent0
    # MetaAgent0 will use its default model (e.g., orca-mini or the first from its chat list)
    # This can be configured if needed: meta_agent = MetaAgent0(default_model="mistral:7b-instruct-q5_K_M")
    meta_agent = MetaAgent0()

    explanation = meta_agent.explain_readme_section("What is the GPU/CPU model balancing strategy?")
    print(explanation)

    explanation_self_play = meta_agent.explain_readme_section("How does self-play work?")
    print(explanation_self_play)
    ```

### 3.2. Self-Play Mechanism
The self-play mechanism allows Agent Zero to take an objective and iteratively work on it.

**To initiate self-play (example from within the container):**
1.  Ensure Ollama is running (`ollama serve &`).
2.  Navigate to the application directory: `cd /app`
3.  Use Python to run the self-play loop:
    ```python
    from agent_zero.self_play import Agent, TaskListManager, self_play_loop

    # 1. Initialize components
    # Configure the agent with preferred models:
    orchestrator = Agent(
        persona_name="Orchestrator_001",
        chat_models=["mistral:7b-instruct-q5_K_M"],       # Primary chat model
        utility_models=["tinydolphin:1.1b-q4_K_M", "orca-mini:3b-q4_K_M"], # Utility, with TinyDolphin first
        embedding_model="nomic-embed-text:latest"
    )
    task_manager = TaskListManager()

    # 2. Define an initial objective
    objective_prompt = "Develop a brief plan to learn about the basics of quantum computing."

    # 3. Optional: Define a callback to see updates from the loop
    def print_loop_update(data):
        print(f"LOOP UPDATE >>> Status: {data.get('objective_status', data.get('final_status'))}, Interaction: {data.get('interaction_count', 'N/A')}")
        if "task_summary" in data and isinstance(data["task_summary"], list):
             for tid, desc, status, prio in data["task_summary"][:3]:
                 print(f"  - Task (P{prio}, ID {tid[:4]}): {desc[:50]}... ({status})")

    # 4. Run the loop
    print(f"Starting self-play for objective: {objective_prompt}")
    final_objective, final_tasks = self_play_loop(
        initial_objective_prompt=objective_prompt,
        orchestrator_agent=orchestrator,
        task_list_manager=task_manager,
        max_interactions=5,
        on_interaction_callback=print_loop_update,
        use_cloning_for_tasks=True
    )

    # 5. Inspect results (details omitted for brevity)
    print(f"Objective '{final_objective.description}' finished with status: {final_objective.status.value}")
    ```

## 4. GPU/CPU Model Balancing Strategy

Agent Zero intelligently utilizes GPU and CPU resources:

- **Chat Models (GPU-Preferred):** Larger models for complex reasoning.
    - *Primary Recommendation:* `mistral:7b-instruct-q5_K_M`
    - *Alternatives:* `llama2:7b-chat-q5_K_M`

- **Utility Models (CPU-Preferred):** Smaller, faster models for simpler tasks.
    - *Primary Recommendation:* `tinydolphin:1.1b-q4_K_M`
    - *Alternatives:* `orca-mini:3b-q4_K_M`, `phi:2.7b-chat-q4_K_M`

- **Embedding Models:** Specialized models for RAG (Phase 3).
    - *Primary Recommendation:* `nomic-embed-text:latest`
    - *Alternatives:* `all-minilm:l6-v2` (very lightweight)

**How it Works:** The `Agent` class selects models from its configured lists based on task type. Agent initialization allows specifying these lists.

## 5. Future Development & Considerations

- **Phase 3: Enhanced Local Web Scraping & ChromaDB for RAG:**
    - Integration of Python-based headless browser tools (e.g., Selenium with Chromium/Firefox installed in the Docker image) for local web scraping. This is a **tool integration**, not an Ollama "scraper model."
    - Using Ollama's embedding models to vectorize scraped content for ChromaDB.
- **Phase 4: Archetype Refinement & Custom Agent Training.**
- **Phase 5: Code Review, Stability Hardening & Future-Proofing.**

---
End of 0README.txt
