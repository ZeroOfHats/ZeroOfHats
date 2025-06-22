# Agent Zero: "baby_zero"

Agent Zero ("baby_zero") is a fully self-contained, offline-capable AI agent system leveraging local GPU/CPU resources for optimal performance.

## Project Goal

To create an autonomous AI agent that can:
- Operate entirely locally and offline (after initial setup).
- Utilize local LLMs via Ollama, accelerated by NVIDIA GPUs with CPU fallback.
- Maintain persistent memory using ChromaDB for contextual understanding and learning.
- Follow a configurable and extensible agent architecture.
- Execute complex objectives through a self-play loop and task management.

## Setup

1.  **Prerequisites:**
    *   Docker and Docker Compose
    *   Python 3.9+
    *   NVIDIA GPU with drivers installed (for GPU acceleration with Ollama)

2.  **Configuration:**
    *   Copy `.env.example` to `.env` and configure your settings (e.g., Ollama models). (Note: `.env.example` will be created later).

3.  **Build and Run Services:**
    ```bash
    docker-compose up --build -d
    ```

4.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the Agent:**
    (Instructions to be added once the main script is developed, e.g., `python main.py --objective "your objective"`)

## Project Structure

```
agent_zero/        # Core agent logic
  memory/          # Memory components (e.g., ChromaDB service)
  self_play/       # Self-play loop, task management, models
  agent.py         # Main Agent class
  llm_client.py    # Client for LLM interaction
  # ... other core modules
config/            # Configuration files, Dockerfiles
  ollama.Dockerfile
  chromadb.Dockerfile
scripts/           # Utility scripts
tests/             # Test suite
main.py            # Main entry point to run the agent (to be created)
docker-compose.yml # Docker services definition
requirements.txt   # Python dependencies
README.md          # This file
```

## Development Phases (High-Level)

1.  **Foundation & Core Utilities:** Basic setup, LLM client, config manager, loggers.
2.  **Agent Core & Basic Memory:** Agent class, initial memory integration with ChromaDB.
3.  **Task Management & Objective Handling:** Task/Objective models, TaskListManager.
4.  **Self-Play Loop & Autonomous Operation:** Core autonomous loop, basic self-correction.
5.  **Advanced Features & Refinement:** RAG, experience memory, agent cloning, testing.

---
*This project is being developed by an AI agent.*
