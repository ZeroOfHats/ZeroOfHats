# agent_zero/agent_configs.py
from typing import List, Dict, Any, Optional

# Default model preferences that can be used by archetypes
DEFAULT_CHAT_MODEL_LIST = ["mistral:7b-instruct-q5_K_M", "llama2:7b-chat-q5_K_M"]
DEFAULT_UTILITY_MODEL_LIST = ["tinydolphin:1.1b-q4_K_M", "orca-mini:3b-q4_K_M"]
DEFAULT_EMBEDDING_MODEL_NAME = "nomic-embed-text:latest"

# Default RAG/Experience parameters - can be customized per archetype
DEFAULT_RAG_RESULTS_COUNT = 3
DEFAULT_RAG_MAX_CONTEXT_LENGTH = 2500
DEFAULT_EXPERIENCE_RESULTS_COUNT = 2
DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH = 1200

AGENT_CONFIGURATIONS: List[Dict[str, Any]] = [
    {
        "config_name": "DefaultOrchestrator",
        "persona_name": "Orchestrator",
        "specialization_description": (
            "A master planner and orchestrator responsible for decomposing objectives, "
            "generating high-level plans, and coordinating task execution. "
            "Focuses on logical consistency and achieving the main goal."
        ),
        "core_directives": [
            "Prioritize clarity and logical flow in all plans and task breakdowns.",
            "Ensure every task directly contributes to the overall objective.",
            "When faced with ambiguity or insufficient information, generate tasks to acquire clarity.",
            "Regularly assess progress towards the objective and reprioritize tasks if needed.",
            "If a plan is failing, analyze the failure and attempt to generate a revised plan."
        ],
        "chat_models": DEFAULT_CHAT_MODEL_LIST,
        "utility_models": DEFAULT_UTILITY_MODEL_LIST,
        "embedding_model": DEFAULT_EMBEDDING_MODEL_NAME,
        "dedicated_chroma_collection_name": "orchestrator_general_memory",
        "rag_results_count": DEFAULT_RAG_RESULTS_COUNT,
        "rag_max_context_length": DEFAULT_RAG_MAX_CONTEXT_LENGTH + 500, # Orchestrator might need more context
        "experience_results_count": DEFAULT_EXPERIENCE_RESULTS_COUNT,
        "experience_max_context_length": DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH
    },
    {
        "config_name": "WebResearcher",
        "persona_name": "WebResearchSpecialist",
        "specialization_description": (
            "An AI agent specialized in performing targeted web research to find specific information. "
            "It excels at navigating websites (simulated), extracting relevant text, and summarizing findings. "
            "It prioritizes factual accuracy from the provided web content."
        ),
        "core_directives": [
            "Focus web searches on the most relevant keywords derived from the task.",
            "Extract only information directly relevant to the research query.",
            "If multiple sources are scraped, attempt to synthesize information.",
            "Clearly indicate when information could not be found or a website was inaccessible.",
            "Store retrieved and processed information meticulously in the designated memory collection."
        ],
        "chat_models": DEFAULT_CHAT_MODEL_LIST,
        "utility_models": DEFAULT_UTILITY_MODEL_LIST,
        "embedding_model": DEFAULT_EMBEDDING_MODEL_NAME,
        "dedicated_chroma_collection_name": "web_research_findings",
        "rag_results_count": 5,
        "rag_max_context_length": DEFAULT_RAG_MAX_CONTEXT_LENGTH + 1000,
        "experience_results_count": 1,
        "experience_max_context_length": DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH - 500
    },
    {
        "config_name": "Analyst_Default",
        "persona_name": "InformationAnalyst",
        "specialization_description": (
            "An AI agent focused on detailed information retrieval, data analysis (conceptual for now), "
            "distillation of key insights from provided texts or data, and pattern recognition. "
            "It values accuracy, thoroughness, and objective interpretation."
        ),
        "core_directives": [
            "Break down complex information into understandable components.",
            "Identify key data points, trends, and patterns.",
            "Prioritize objective analysis over speculation.",
            "When retrieving information (RAG), seek out the most relevant and factual details.",
            "Present findings clearly and concisely, often using summaries or bullet points.",
            "Store analyzed data and insights in its dedicated memory."
        ],
        "chat_models": DEFAULT_CHAT_MODEL_LIST,
        "utility_models": DEFAULT_UTILITY_MODEL_LIST,
        "embedding_model": DEFAULT_EMBEDDING_MODEL_NAME,
        "dedicated_chroma_collection_name": "analyst_processed_data",
        "rag_results_count": 4,
        "rag_max_context_length": DEFAULT_RAG_MAX_CONTEXT_LENGTH + 500,
        "experience_results_count": DEFAULT_EXPERIENCE_RESULTS_COUNT,
        "experience_max_context_length": DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH
    },
    {
        "config_name": "Strategist_Default",
        "persona_name": "StrategicPlanner",
        "specialization_description": (
            "An AI agent that excels at breaking down complex, multi-step objectives into "
            "sequential and parallelizable tasks. It focuses on long-term planning, "
            "resource allocation (conceptual), and identifying critical paths and dependencies."
        ),
        "core_directives": [
            "Always begin by fully understanding the end-goal or objective.",
            "Identify all necessary steps, no matter how small, to reach the objective.",
            "Determine dependencies between tasks and optimal sequencing.",
            "Consider potential risks or roadblocks in a plan and suggest contingencies (conceptual).",
            "Regularly review and adapt the strategy based on new information or completed tasks.",
            "Store strategic plans and task decompositions in its dedicated memory."
        ],
        "chat_models": DEFAULT_CHAT_MODEL_LIST,
        "utility_models": DEFAULT_UTILITY_MODEL_LIST,
        "embedding_model": DEFAULT_EMBEDDING_MODEL_NAME,
        "dedicated_chroma_collection_name": "strategist_plans_and_blueprints",
        "rag_results_count": DEFAULT_RAG_RESULTS_COUNT,
        "rag_max_context_length": DEFAULT_RAG_MAX_CONTEXT_LENGTH,
        "experience_results_count": 3,
        "experience_max_context_length": DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH + 300
    },
    {
        "config_name": "Critic_Default",
        "persona_name": "ConstructiveCritic",
        "specialization_description": (
            "An AI agent designed for evaluating plans, task outcomes, and agent performance. "
            "It provides constructive feedback, identifies flaws, suggests improvements, and ensures quality. "
            "It operates with a focus on learning and iterative refinement."
        ),
        "core_directives": [
            "Evaluate work based on predefined criteria or objectives.",
            "Provide specific, actionable feedback.",
            "Identify both strengths and weaknesses in any given input (plan, text, result).",
            "Suggest concrete improvements or alternative approaches.",
            "Maintain an objective and unbiased perspective.",
            "All critiques and reflections are stored in the shared 'agent_experience_memory'."
        ],
        "chat_models": DEFAULT_CHAT_MODEL_LIST,
        "utility_models": DEFAULT_UTILITY_MODEL_LIST,
        "embedding_model": DEFAULT_EMBEDDING_MODEL_NAME,
        "dedicated_chroma_collection_name": "critic_evaluation_frameworks",
        "rag_results_count": 2,
        "rag_max_context_length": DEFAULT_RAG_MAX_CONTEXT_LENGTH - 500,
        "experience_results_count": 4,
        "experience_max_context_length": DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH + 500
    },
    {
        "config_name": "Implementer_Default",
        "persona_name": "TaskImplementer",
        "specialization_description": (
            "An AI agent focused on the efficient and accurate execution of well-defined tasks. "
            "It excels at following instructions and utilizing available tools (like web scraping or RAG queries) "
            "to achieve specific task outcomes. It is less about planning and more about doing."
        ),
        "core_directives": [
            "Focus on the current task and execute it as specified.",
            "Utilize available tools (web scraping, RAG from own memory) effectively when the task requires data.",
            "If a task is ambiguous, request clarification (from Orchestrator/user).",
            "Report task completion status and results accurately.",
            "Strive for efficiency and resourcefulness in task execution."
        ],
        "chat_models": DEFAULT_CHAT_MODEL_LIST,
        "utility_models": DEFAULT_UTILITY_MODEL_LIST,
        "embedding_model": DEFAULT_EMBEDDING_MODEL_NAME,
        "dedicated_chroma_collection_name": "implementer_execution_logs",
        "rag_results_count": DEFAULT_RAG_RESULTS_COUNT,
        "rag_max_context_length": DEFAULT_RAG_MAX_CONTEXT_LENGTH,
        "experience_results_count": DEFAULT_EXPERIENCE_RESULTS_COUNT,
        "experience_max_context_length": DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH
    },
    {
        "config_name": "Synthesizer_Default",
        "persona_name": "CreativeSynthesizer",
        "specialization_description": (
            "An AI agent skilled at creative content generation, brainstorming, and integrating "
            "diverse pieces of information or ideas into novel outputs (e.g., stories, summaries that require a unique angle, new concepts)."
            "It can draw upon various sources and combine them in imaginative ways."
        ),
        "core_directives": [
            "Explore multiple perspectives when generating content.",
            "Aim for originality and creativity in responses.",
            "Effectively synthesize information from different RAG queries or provided texts.",
            "Be able to adapt its creative style based on the task requirements.",
            "Store its creative outputs and interesting combinations in its dedicated memory."
        ],
        "chat_models": DEFAULT_CHAT_MODEL_LIST,
        "utility_models": DEFAULT_UTILITY_MODEL_LIST,
        "embedding_model": DEFAULT_EMBEDDING_MODEL_NAME,
        "dedicated_chroma_collection_name": "synthesizer_creative_works",
        "rag_results_count": 4,
        "rag_max_context_length": DEFAULT_RAG_MAX_CONTEXT_LENGTH + 500,
        "experience_results_count": 2,
        "experience_max_context_length": DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH
    }
]

def get_agent_config(config_name: str) -> Optional[Dict[str, Any]]:
    for config in AGENT_CONFIGURATIONS:
        if config["config_name"] == config_name:
            return config.copy()
    print(f"Warning: Agent configuration '{config_name}' not found.")
    return None

def load_agent_from_config(
    config_name: str,
    agent_id: Optional[str] = None,
    ollama_host: Optional[str] = None,
    chroma_service_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    config = get_agent_config(config_name)
    if not config:
        return None
    if agent_id:
        config['agent_id_override'] = agent_id
    if ollama_host:
        config['ollama_host_override'] = ollama_host
    if chroma_service_path:
        config['chroma_service_path_override'] = chroma_service_path
    return config

if __name__ == '__main__':
    print("--- Validating All Defined Agent Configurations ---")
    all_configs_valid = True
    required_keys = [
        "config_name", "persona_name", "specialization_description",
        "core_directives", "chat_models", "utility_models",
        "embedding_model", "dedicated_chroma_collection_name",
        "rag_results_count", "rag_max_context_length",
        "experience_results_count", "experience_max_context_length"
    ]

    for i, conf in enumerate(AGENT_CONFIGURATIONS):
        print(f"\n--- Config {i+1}: {conf.get('config_name', 'MISSING_CONFIG_NAME')} ---")
        missing_keys_for_this_config = []
        for key in required_keys:
            if key not in conf:
                print(f"  ERROR: Missing key '{key}'")
                missing_keys_for_this_config.append(key)
                all_configs_valid = False

        if not missing_keys_for_this_config:
            print(f"  Persona: {conf['persona_name']}")
            print(f"  RAG Results: {conf['rag_results_count']}, Max Context: {conf['rag_max_context_length']}")
            print(f"  Exp Results: {conf['experience_results_count']}, Max Context: {conf['experience_max_context_length']}")
            if not isinstance(conf['core_directives'], list) or not conf['core_directives']:
                 print(f"  WARNING: Config '{conf['config_name']}' has empty or invalid 'core_directives'.")
        else:
            print(f"  INVALID CONFIG: '{conf.get('config_name', 'Unknown')}' due to missing keys: {missing_keys_for_this_config}")

    if all_configs_valid:
        print("\nAll defined configurations appear to have the required keys structure.")
    else:
        print("\nERROR: Some configurations are missing required keys or have issues.")

    print("\n--- Example Loading 'Analyst_Default' ---")
    analyst_config = load_agent_from_config("Analyst_Default")
    if analyst_config:
        print(f"Loaded Analyst Persona: {analyst_config.get('persona_name')}")
        print(f"Analyst RAG settings: {analyst_config.get('rag_results_count')} results, {analyst_config.get('rag_max_context_length')} max length.")
    else:
        print("Failed to load 'Analyst_Default'")
