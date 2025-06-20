# 0README.txt - Agent Zero (Local GPU Edition)

## 1. Overview

Welcome to Agent Zero (Local GPU Edition)! This document is your comprehensive guide to understanding, setting up, running, and interacting with this fully self-contained, offline-capable AI agent system. Agent Zero leverages local GPU resources for optimal performance, integrating Ollama for Large Language Model (LLM) support and ChromaDB for local vector memory.

Meta Agent 0, an agent within the system, is designed to parse and explain this `0README.txt`, assisting you in navigating its features. (Future capability: Meta Agent 0 will also aim to search and understand other README files within the container for self-play and learning).

**Core Principles:**
- **Fully Local & Offline:** All components run on your local machine. No internet is required after initial setup and model downloads.
- **GPU Accelerated:** Utilizes NVIDIA GPUs via Ollama for LLM inference.
- **CPU Fallback/Balancing:** Strategically uses CPU for smaller utility LLMs to conserve VRAM.
- **Persistent Memory:** Ollama models and ChromaDB vector stores are persisted using Docker volume mounts.
- **Configurable & Extensible Agent Architecture:** Supports self-play, customizable agent archetypes, and self-improvement loops.
- **Modularity:** Designed with distinct components to facilitate understanding and future upgrades.

## 2. System Setup & Deployment Guidelines

Follow these steps to get Agent Zero up and running.

### 2.1. Prerequisites
- Docker installed on your host system.
- An NVIDIA GPU with the latest proprietary drivers installed.
- `nvidia-container-toolkit` (or its predecessor `nvidia-docker2`) installed on your host to enable GPU access for Docker containers.
- Sufficient disk space:
    - Docker image: ~15-20GB (estimate, includes Kali base, CUDA, Python environment, tools).
    - Ollama Models: Each model can range from ~1GB (e.g., TinyDolphin q4) to ~5GB (e.g., Mistral 7B q5).
    - ChromaDB Data: Will grow with usage.
    - **Target:** The entire deployment (image + a useful set of models + initial data) should aim to fit on a 64GB flash drive. Careful model selection is key.

### 2.2. Building the Docker Image
1.  Clone the Agent Zero repository to your local machine.
2.  Navigate to the project root directory (containing this `0README.txt` and the `Dockerfile`).
3.  Run the build command:
    ```bash
    docker build -t agent-zero-gpu .
    ```
    This process may take some time as it downloads the base image and installs all dependencies.

### 2.3. Running the Docker Container

1.  **Create Host Directories for Persistent Storage:**
    Before running the container for the first time, create directories on your host machine to store persistent data. This ensures your Ollama models and ChromaDB data survive container restarts.
    ```bash
    mkdir -p ./agent_zero_data/ollama_models
    mkdir -p ./agent_zero_data/chroma_data
    # Using a subdirectory like ./agent_zero_data helps keep things organized.
    # You can use absolute paths if you prefer, e.g., /opt/agent_zero_data/ollama_models
    ```

2.  **Run the Container:**
    Use the following command to run the Agent Zero container with GPU access and persistent storage:
    ```bash
    docker run --gpus all -it \
      -v $(pwd)/agent_zero_data/ollama_models:/root/.ollama \
      -v $(pwd)/agent_zero_data/chroma_data:/agent_data/chroma \
      -p 11434:11434 \
      agent-zero-gpu bash
    ```
    **Explanation of `docker run` options:**
    -   `--gpus all`: Grants the container access to all available NVIDIA GPUs on your host.
    -   `-it`: Runs the container in interactive mode with a pseudo-TTY, giving you a bash shell.
    -   `-v $(pwd)/agent_zero_data/ollama_models:/root/.ollama`: Mounts your local `ollama_models` directory into the container at `/root/.ollama`, where Ollama stores its models.
    -   `-v $(pwd)/agent_zero_data/chroma_data:/agent_data/chroma`: Mounts your local `chroma_data` directory into the container at `/agent_data/chroma`, where `ChromaService` persists its vector database.
    -   `-p 11434:11434`: Exposes Ollama's API port (11434) from the container to your host machine. This allows you to potentially interact with Ollama directly from your host if needed, but Agent Zero itself communicates with Ollama within the container.
    -   `agent-zero-gpu`: The name of the Docker image you built.
    -   `bash`: Starts a bash shell inside the container upon launch.

### 2.4. Initial Ollama Model Downloads (Inside Container)
Once inside the container's bash shell:
1.  **Start Ollama Service:**
    ```bash
    ollama serve &
    ```
    Wait a few seconds for the service to initialize. You should see some output.
2.  **Pull Recommended Models:** Download the models Agent Zero is configured to use. This needs to be done only once per model, as they'll be saved in your mounted `ollama_models` volume.
    *   **Primary Chat Model (GPU-focused):**
        ```bash
        ollama pull mistral:7b-instruct-q5_K_M
        ```
    *   **Primary Utility Model (CPU-focused):**
        ```bash
        ollama pull tinydolphin:1.1b-q4_K_M
        ```
    *   **Primary Embedding Model (for RAG):**
        ```bash
        ollama pull nomic-embed-text:latest
        ```
    *   **Alternative/Additional Models (Optional, mind storage limits):**
        ```bash
        # ollama pull llama2:7b-chat-q5_K_M  # Alternative Chat
        # ollama pull orca-mini:3b-q4_K_M     # Alternative Utility
        # ollama pull phi:2.7b-chat-q4_K_M      # Alternative Utility
        # ollama pull all-minilm:l6-v2        # Alternative Lightweight Embedding
        ```
    Refer to `agent_zero/agent_configs.py` for default model lists for various archetypes. You can customize these lists or pass them during `Agent` instantiation.

## 3. Interacting with Agent Zero (Inside Container)

All interactions typically occur within the running Docker container. Navigate to the application directory:
```bash
cd /app
```
From here, you can use Python to interact with Agent Zero components.

### 3.1. Meta Agent 0: Your Guide to the System
Meta Agent 0 (`agent_zero.meta_agent_0.core.MetaAgent0`) helps you understand this `0README.txt`.
```python
# Example Python interaction:
from agent_zero.meta_agent_0.core import MetaAgent0
from agent_zero.self_play.models import Status # Added for callback example

# Ensure Ollama is running (ollama serve &)
meta_agent = MetaAgent0()

# Ask about a section (it will use its default Ollama model)
explanation = meta_agent.explain_readme_section("How does Agent Zero manage GPU and CPU resources?")
print(explanation)

# Another example
explanation_rag = meta_agent.explain_readme_section("What is the RAG flow in Agent Zero?")
print(explanation_rag)
```

### 3.2. Self-Play Loop: Autonomous Task Execution
The self-play mechanism (`agent_zero.self_play.loop.self_play_loop`) allows an agent (typically an "Orchestrator") to autonomously pursue an objective.

```python
# Example Python interaction for self-play:
from agent_zero.self_play import Agent, TaskListManager, self_play_loop, AgentState
from agent_zero.agent_configs import load_agent_from_config # To load archetypes
from agent_zero.self_play.models import Status # Ensure Status is imported for callback

# 1. Load an Orchestrator configuration
orchestrator_config_dict = load_agent_from_config("DefaultOrchestrator")
if not orchestrator_config_dict:
    raise ValueError("Failed to load DefaultOrchestrator config.")

# Add runtime parameters not in static config (Agent __init__ handles defaults if not provided)
orchestrator_config_dict['agent_id'] = "main_orchestrator_01"
# orchestrator_config_dict['ollama_host'] = 'http://localhost:11434' # Default already set in Agent
# orchestrator_config_dict['chroma_service_path'] = '/agent_data/chroma' # Default already set in Agent

# Instantiate the Orchestrator Agent
orchestrator = Agent(**orchestrator_config_dict)
task_manager = TaskListManager()

# 2. Define an initial objective
objective_prompt = "Research the current state of AI in renewable energy, identify three key applications, and provide a brief summary for each."

# 3. Optional: Define a callback to see updates from the loop
def print_loop_update(data):
    state = data.get('objective_status', data.get('final_status', 'Unknown'))
    count = data.get('interaction_count', 'N/A')
    print(f"LOOP UPDATE >>> Objective Status: {state}, Interaction: {count}")
    if "task_summary" in data and isinstance(data["task_summary"], list) and state != "completed":
         pending_tasks = [t for t in data["task_summary"] if t[2] == Status.PENDING.value]
         if pending_tasks:
             print(f"  Pending tasks ({len(pending_tasks)}):")
             for tid, desc, status, prio in pending_tasks[:2]: # Show top 2 pending
                 print(f"    - P{prio} ID {tid[:4]}: {desc[:50]}... ({status})")
         else:
             print("  No pending tasks currently in summary.")


# 4. Run the self-play loop
print(f"Starting self-play for objective: '{objective_prompt}'")
final_objective, final_tasks_manager = self_play_loop(
    initial_objective_prompt=objective_prompt,
    orchestrator_agent=orchestrator,
    task_list_manager=task_manager,
    max_interactions=10,  # Adjust as needed to prevent overly long runs during testing
    on_interaction_callback=print_loop_update,
    use_cloning_for_tasks=True # Enable for task execution by specialized clones
)

# 5. Inspect results
print("\n--- Self-Play Loop Ended ---")
print(f"Objective: {final_objective.description}")
print(f"Final Status: {final_objective.status.value}")
print("Tasks Overview:")
for task_obj in final_tasks_manager.get_all_tasks():
    print(f"  - P{task_obj.priority} [{task_obj.status.value}] {task_obj.description}")
    if task_obj.result:
        print(f"    Result: {str(task_obj.result)[:150]}...")
```
- **`max_interactions`**: Controls loop duration.
- **`use_cloning_for_tasks`**: If `True`, the Orchestrator clones a temporary "Executor" agent for each task. If `False`, the Orchestrator performs tasks itself.

## 4. Agent Archetypes & Customization

Agent Zero supports different agent roles or "archetypes," each with specific configurations. These are defined in `agent_zero/agent_configs.py`.

### 4.1. Predefined Archetypes
The system comes with several predefined archetypes:
-   **`DefaultOrchestrator`**: The master planner, breaks down objectives, manages task flow. (Primary agent for `self_play_loop`).
-   **`WebResearcher`**: Specializes in scraping web pages and extracting information. Stores findings in `web_research_findings` ChromaDB collection.
-   **`Analyst_Default` (`InformationAnalyst`)**: Focuses on information retrieval, data analysis, and insight distillation. Uses `analyst_processed_data` collection.
-   **`Strategist_Default` (`StrategicPlanner`)**: Excels at multi-step planning and task sequencing. Uses `strategist_plans_and_blueprints` collection.
-   **`Critic_Default` (`ConstructiveCritic`)**: Evaluates plans and outcomes, provides feedback, and contributes to `agent_experience_memory`. Also uses `critic_evaluation_frameworks` for its own criteria.
-   **`Implementer_Default` (`TaskImplementer`)**: Efficiently executes well-defined tasks using available tools. Uses `implementer_execution_logs` collection.
-   **`Synthesizer_Default` (`CreativeSynthesizer`)**: Skilled in creative content generation and integrating diverse information. Uses `synthesizer_creative_works` collection.

Each archetype configuration includes:
-   `persona_name`: E.g., "Orchestrator", "WebResearchSpecialist".
-   `specialization_description`: Details its role.
-   `core_directives`: Guiding principles for its behavior.
-   `chat_models`, `utility_models`, `embedding_model`: Preferred Ollama models.
-   `dedicated_chroma_collection_name`: Its primary ChromaDB collection for specialized knowledge.
-   RAG/Experience parameters (e.g., `rag_results_count`): Controls memory consultation depth.

### 4.2. Creating Custom Agents
You can create custom agents by:
1.  **Defining a new configuration** in `agent_zero/agent_configs.py` following the structure of existing archetypes.
2.  **Instantiating an `Agent` directly** with custom parameters:
    ```python
    from agent_zero.self_play import Agent
    my_custom_agent = Agent(
        persona_name="MyExpert",
        specialization_description="Expert on topic X, providing detailed explanations.",
        core_directives=["Always verify facts.", "Explain simply."],
        chat_models=["mistral:7b-instruct-q5_K_M"],
        dedicated_chroma_collection_name="my_expert_knowledge_base",
        rag_results_count=5
        # ... other Agent __init__ parameters ...
    )
    ```

## 5. System Architecture and Components
This section provides an overview of Agent Zero's architecture, its key components, and how they interact to deliver its capabilities.

### 5.1. Core Architectural Principles
Agent Zero is designed around a modular architecture with the following principles:
- **Agent-Centric:** The `Agent` class is the core actor, capable of reasoning, tool use, and learning.
- **LLM-Powered:** Ollama provides the underlying Large Language Models for all text generation, understanding, and reasoning tasks.
- **Memory-Driven:** ChromaDB serves as the persistent vector memory, enabling agents to store and retrieve information (for RAG) and experiences (for self-improvement).
- **Configurable & Extensible:** Agent behaviors and specializations are defined through configurations, allowing for the creation of diverse archetypes.
- **Offline First:** All core operations are designed to function without internet access post-setup.

### 5.2. Key Components

1.  **`Agent` (`agent_zero.self_play.agent.Agent`)**:
    *   The primary intelligent entity. Responsible for decision-making, task execution, learning, and interaction with other components.
    *   **Key Capabilities:** LLM interaction (via `_llm_call`), web scraping (via `scrape_website`), RAG (information retrieval and context augmentation), experience-based learning (reflection and simulated challenges), task decomposition, state management (`AgentState`).
    *   Customizable via configurations (`agent_configs.py`) for persona, specialization, directives, model preferences, and dedicated memory.

2.  **Ollama (External Service)**:
    *   The local LLM provider. Agent Zero communicates with the Ollama API (typically running at `http://localhost:11434`) to execute LLM inference tasks using various open-source models (e.g., Mistral, Llama2, TinyDolphin, Nomic Embed).
    *   Handles GPU acceleration and model management.

3.  **ChromaDB Service (`agent_zero.memory.chroma_service.ChromaService`)**:
    *   A wrapper around the `chromadb` client library, providing an interface for managing vector collections and performing CRUD operations on embeddings and associated documents/metadata.
    *   Used for:
        *   Storing processed text chunks and their embeddings (e.g., from web scrapes) in agent-specific or general collections.
        *   Storing agent reflections and learnings in the shared `agent_experience_memory` collection.
        *   Querying these collections to retrieve relevant context for RAG.
    *   Configured for persistent storage via Docker volume mounts (`/agent_data/chroma`).

4.  **Web Scraper (`agent_zero.tools.web_scraper`)**:
    *   A utility module using Selenium and BeautifulSoup to fetch and extract main text content from web pages.
    *   Called by an `Agent` when a "scrape" task is identified.

5.  **Text Processor (`agent_zero.utils.text_processing`)**:
    *   Provides functions for cleaning raw text and splitting it into manageable chunks suitable for embedding and RAG. Used by the `Agent` after scraping or when processing large texts for memory storage.

6.  **Self-Play Loop (`agent_zero.self_play.loop.self_play_loop`)**:
    *   The main orchestration logic for autonomous agent operation.
    *   Takes an initial objective and an `Orchestrator` agent.
    *   Manages the cycle of:
        1.  Task decomposition by the Orchestrator.
        2.  Selection of the highest priority task.
        3.  Task execution (by the Orchestrator or a cloned specialist `Agent`).
        4.  Reflection on the completed task by the Orchestrator.
        5.  Generation of new tasks if the objective is not yet met.
    *   Includes mechanisms for agent cloning, interaction limits, and basic state management for the primary Orchestrator.

7.  **Task Management (`agent_zero.self_play.models` & `task_manager`)**:
    *   `Objective` and `Task` dataclasses define the structure of goals and work items.
    *   `TaskListManager` holds the list of tasks for an objective, providing methods for adding, retrieving (by priority), and managing tasks.

8.  **Agent Configurations (`agent_zero.agent_configs`)**:
    *   A centralized Python module defining various agent archetypes (e.g., Orchestrator, WebResearcher, Analyst, Critic) as configuration dictionaries.
    *   These configs specify persona, specialization, directives, model preferences (chat, utility, embedding), RAG/experience parameters, and dedicated ChromaDB collections, allowing for the instantiation of diverse, specialized agents.

9.  **Meta Agent 0 (`agent_zero.meta_agent_0.core.MetaAgent0`)**:
    *   A specialized agent designed to help users understand the Agent Zero system by parsing and explaining the `0README.txt` file using Ollama.

### 5.3. Key Interaction Flows

1.  **Retrieval Augmented Generation (RAG) Flow:**
    *   **Trigger:** An `Agent` needs to answer a query or perform a task requiring external knowledge (e.g., in `execute_task`, `decompose_objective_into_tasks`).
    *   **Query Embedding:** The `Agent` generates an embedding for the query/task description using `Agent.generate_embedding()`.
    *   **ChromaDB Query:** The `Agent` calls `ChromaService.query_collection()` with the query embedding to search its `default_memory_collection` (its specialized knowledge) for relevant text chunks.
    *   **Context Augmentation:** Retrieved chunks are formatted and prepended to the original prompt by `Agent._augment_prompt_with_rag_context()`.
    *   **LLM Call:** The augmented prompt is sent to Ollama via `Agent._llm_call()` for a more informed response.

2.  **Experience-Augmented Decision Making:**
    *   Similar to RAG, but queries the `EXPERIENCE_MEMORY_COLLECTION` using `Agent._augment_prompt_with_experience_context()`.
    *   Retrieved past reflections/learnings are added to the prompt (often layered with general RAG context).
    *   Used in methods like `execute_task`, `decompose_objective_into_tasks`, and `generate_next_steps` to leverage past experiences.

3.  **Web Content Ingestion & Storage Flow:**
    *   **Trigger:** An `Agent` executes a "scrape <URL>" task.
    *   **Scraping:** `Agent.scrape_website()` calls `web_scraper.get_text_from_url()` to fetch and extract text.
    *   **Processing:** `Agent.process_and_store_text_in_memory()` uses `text_processing.split_text_into_chunks()` on the scraped content.
    *   **Embedding:** For each chunk, `Agent.generate_embedding()` is called.
    *   **Storage:** Chunks, their embeddings, and metadata (URL, task ID, timestamp) are stored in the `Agent`'s `default_memory_collection` via `ChromaService.add_documents()`.
    *   **Result:** The task result includes a summary of the scraped content and a report of the storage process.

4.  **Self-Play Loop Cycle (Simplified):**
    *   **Objective:** `self_play_loop` starts with an objective.
    *   **Decomposition:** `OrchestratorAgent` decomposes objective into tasks (using RAG + Experience). Tasks added to `TaskListManager`.
    *   **Task Selection:** Highest priority pending task is selected.
    *   **Execution:** `OrchestratorAgent` (or a clone) executes the task (using RAG + Experience). Task result and new sub-tasks are generated.
    *   **Reflection:** `OrchestratorAgent` calls `reflect_and_learn_from_task()` on the completed/failed task, storing reflection in `EXPERIENCE_MEMORY_COLLECTION`.
    *   **Next Steps/Completion Check:**
        *   If task list is empty, `OrchestratorAgent` checks if objective is complete (using RAG + Experience).
        *   If not complete, `OrchestratorAgent` generates next steps (using RAG + Experience).
        *   If stuck (no new steps), `OrchestratorAgent` may attempt a `simulated_challenge()`.
    *   **Loop:** Continues until objective complete, max interactions, or intervention needed.

5.  **Agent Customization & Instantiation:**
    *   `agent_configs.py` stores archetype definitions.
    *   External logic (e.g., in `self_play_loop` examples or a future agent manager) uses `load_agent_from_config()` to get a configuration dictionary.
    *   An `Agent` instance is created by passing these configuration values to its `__init__` method, resulting in a specialized agent.

## 6. GPU/CPU Model Balancing & Resource Management
(This section was updated in a previous step and is assumed to be up-to-date. It covers Agent Zero's Model Selection, Ollama's Role, Model Quantization, Storage Considerations including the 64GB target, Monitoring Resource Usage with `nvidia-smi` and `docker stats`, and Customizing Model Lists.)

## 7. Self-Improvement Mechanisms

Agent Zero incorporates mechanisms for agents to learn and adapt over time. These are primarily designed for use when an agent is `IDLE` (not actively working on an assigned task), often referred to as "Play/Break Time."

### 7.1. Agent States
Agents can exist in several states, managed by the `AgentState` enum (e.g., `IDLE`, `TASKED`, `SELF_IMPROVING`). The `self_play_loop` includes basic logic to transition the orchestrator agent's state and trigger self-improvement activities.

### 7.2. Reflection & Critique (Experience Memory)
-   **Process:** After a task is completed (or fails), an agent (especially an Orchestrator or a Critic archetype) can call its `reflect_and_learn_from_task(completed_task)` method.
-   **Mechanism:** This method uses an LLM to generate a structured reflection on the task's execution, considering what went well, what could be improved, insights gained, and unexpected challenges.
-   **Storage:** The reflection text is vectorized, and both the text and its embedding are stored in a shared ChromaDB collection named `agent_experience_memory`. This metadata-rich storage includes links to the original task, the reflecting agent, and timestamps.
-   **Benefit:** This allows the system to build a memory of past learnings.

### 7.3. Retrieval of Experiences for Decision-Making
-   The `Agent` class's core decision-making methods (`decompose_objective_into_tasks`, `execute_task`, `generate_next_steps`, `is_objective_complete`) are enhanced to query this `agent_experience_memory` using the `_augment_prompt_with_experience_context` helper.
-   Relevant past experiences are retrieved and added to the LLM prompt, allowing the agent to "learn" from previous successes or failures when tackling new, similar situations.

### 7.4. Simulated Challenges & Experimentation
-   **Process:** When an agent is `IDLE` and the system determines it's time for self-improvement (e.g., in `self_play_loop` when no tasks can be generated for the current objective), it can call its `attempt_simulated_challenge()` method.
-   **Mechanism:**
    1.  The agent generates a persona-relevant hypothetical question or micro-problem using an LLM.
    2.  It then attempts to solve this challenge, using its full RAG capabilities (querying both its specialized memory and the shared experience memory).
    3.  The challenge, its attempted solution, and the outcome are then processed using `reflect_and_learn_from_task` to store this self-generated learning episode into the `agent_experience_memory`.
-   **Benefit:** Allows agents to proactively test their knowledge and reasoning, identify gaps, and reinforce learning in a safe, simulated environment.

### 7.5. Knowledge Consolidation (Future Aspect)
While not fully implemented, the design allows for future mechanisms where idle agents could actively process and synthesize information from their RAG memories (e.g., `default_memory_collection`) to refine their specialized knowledge, create summaries, or identify new connections.

## 8. Security Considerations
(This section was added in a previous step and is assumed to be up-to-date. It covers Kali Linux Awareness, Docker Volume Mounts, Offline Operation & Network Exposure, and Model Security.)

## 9. Testing and System Evaluation
(This section was added in a previous step and is assumed to be up-to-date. It covers Recommended Testing Layers - Unit, Integration, E2E - and Stress Testing Scenarios.)

## 10. Troubleshooting (NEW SECTION)

This section provides solutions to common issues you might encounter.

-   **Docker Issues:**
    *   **"Cannot connect to the Docker daemon"**: Ensure the Docker service/daemon is running on your host machine.
    *   **Permission Denied (Docker socket)**: You might need to run Docker commands with `sudo` or add your user to the `docker` group.
-   **GPU Access Problems:**
    *   **`docker: Error response from daemon: could not select device driver "" with capabilities: [[gpu]]`**:
        *   Verify `nvidia-container-toolkit` (or `nvidia-docker2`) is correctly installed and configured on your host.
        *   Ensure your NVIDIA drivers are up-to-date and compatible with your CUDA version and `nvidia-container-toolkit`.
        *   Try restarting the Docker daemon.
    *   **Ollama not using GPU (check `nvidia-smi` on host)**:
        *   Ensure the `--gpus all` flag was used in `docker run`.
        *   Check Ollama logs inside the container (see "Monitoring Resource Usage") for GPU detection messages.
        *   Very small models might primarily use CPU even if GPU is available; test with a larger "chat" model.
-   **Ollama Model Issues:**
    *   **"Error: model ... not found, try `ollama pull ...`"**: The required Ollama model has not been downloaded into Ollama's accessible storage.
        *   Solution: Inside the running container, use `ollama pull <model_name_tag>` (e.g., `ollama pull mistral:7b-instruct-q5_K_M`). Ensure the model name and tag are correct.
    *   **Slow model responses/downloads:** Depends on your internet speed (for downloads) and system resources (CPU, RAM, GPU for inference). Quantized models are generally faster and smaller.
-   **ChromaDB / Memory Issues:**
    *   **"CRITICAL: Agent ... failed to initialize ChromaService ..."**:
        *   Check permissions for the host directory mounted to `/agent_data/chroma` in the container. The container user needs write access.
        *   Ensure the path specified in `Agent(chroma_service_path=...)` matches the mount point if overridden.
    *   **Data not persisting:** Verify your `docker run -v ...:/agent_data/chroma` volume mount is correctly specified and uses an absolute path or a correct relative path (`$(pwd)/...`) on your host.
-   **Python / Agent Zero Errors:**
    *   **`ModuleNotFoundError`**: If running Python scripts directly, ensure you are in the `/app` directory within the container or that your `PYTHONPATH` is set up correctly to find the `agent_zero` modules. Using `python3 -m agent_zero.some_module` can sometimes help if running from outside `/app`.
    *   **Scraping Failures**: Web scraping can be fragile. Websites change structure, or might block automated requests. The current scraper is basic.
        *   Check the URL.
        *   The `load_wait_time` in `scrape_website` might need adjustment for very dynamic pages.
        *   The site might be using anti-scraping measures.
-   **Resource Exhaustion (VRAM/RAM):**
    *   If you experience crashes or extreme slowness, monitor VRAM and RAM usage (see Section 6.3).
    *   Reduce the number of concurrently loaded large models (though Agent Zero primarily uses one at a time per agent).
    *   Use more aggressively quantized models.
    *   Ensure no other applications on your host are consuming all GPU VRAM.

## 11. Future Development & Considerations (Previously Section 9)
(This section was updated in a previous step and is assumed to be up-to-date. It includes subsections on Vector DB Abstraction/LanceDB, Advanced Agent Lifecycle Management, Enhanced Reasoning, Tool Usage, and UI.)

---
End of 0README.txt
