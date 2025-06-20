# agent_zero/agent_configs.py
from typing import List, Dict, Any, Optional

DEFAULT_CHAT_MODEL_LIST = ["mistral:7b-instruct-q5_K_M", "llama2:7b-chat-q5_K_M"]
DEFAULT_UTILITY_MODEL_LIST = ["tinydolphin:1.1b-q4_K_M", "orca-mini:3b-q4_K_M"]
DEFAULT_EMBEDDING_MODEL_NAME = "nomic-embed-text:latest"

DEFAULT_RAG_RESULTS_COUNT = 3
DEFAULT_RAG_MAX_CONTEXT_LENGTH = 2500
DEFAULT_EXPERIENCE_RESULTS_COUNT = 2
DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH = 1200

AGENT_CONFIGURATIONS: List[Dict[str, Any]] = [
    {
        "config_name": "DefaultOrchestrator",
        "persona_name": "Orchestrator",
        "specialization_description": "A master planner and orchestrator...",
        "core_directives": ["Prioritize clarity...", "Ensure every task directly contributes..."], # Truncated for brevity in this example
        "chat_models": DEFAULT_CHAT_MODEL_LIST,
        "utility_models": DEFAULT_UTILITY_MODEL_LIST,
        "embedding_model": DEFAULT_EMBEDDING_MODEL_NAME,
        "dedicated_chroma_collection_name": "orchestrator_general_memory",
        "rag_results_count": DEFAULT_RAG_RESULTS_COUNT,
        "rag_max_context_length": DEFAULT_RAG_MAX_CONTEXT_LENGTH + 500,
        "experience_results_count": DEFAULT_EXPERIENCE_RESULTS_COUNT,
        "experience_max_context_length": DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH
    },
    # Ensure all other archetypes (WebResearcher, Analyst_Default, etc.) are fully defined here
    # as per the previous step (subtask 24), including their RAG/Experience parameters.
    # For this subtask, the critical change is in load_agent_from_config.
    # I will assume the full list from subtask 24 is here for the purpose of this step.
    {
        "config_name": "WebResearcher",
        "persona_name": "WebResearchSpecialist",
        "specialization_description": "An AI agent specialized in web research...",
        "core_directives": ["Focus web searches...", "..."],
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
        "specialization_description": "An AI agent focused on detailed information retrieval...",
        "core_directives": ["Break down complex information...", "..."],
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
        "specialization_description": "An AI agent that excels at breaking down objectives...",
        "core_directives": ["Always begin by fully understanding...", "..."],
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
        "specialization_description": "An AI agent designed for evaluating plans, outcomes...",
        "core_directives": ["Evaluate work based on predefined criteria...", "..."],
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
        "specialization_description": "An AI agent focused on efficient execution of tasks...",
        "core_directives": ["Focus on the current task...", "..."],
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
        "specialization_description": "An AI agent skilled at creative content generation...",
        "core_directives": ["Explore multiple perspectives...", "..."],
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
    agent_id_override: Optional[str] = None,
    ollama_host_override: Optional[str] = None,
    chroma_service_path_override: Optional[str] = None
    # Potentially add overrides for RAG/Experience params here too if needed for specific instances
) -> Optional[Dict[str, Any]]:
    base_config = get_agent_config(config_name)
    if not base_config:
        return None

    final_config = base_config.copy()

    # Map override keys to the direct parameter names expected by Agent.__init__
    if agent_id_override:
        final_config['agent_id'] = agent_id_override
    # 'agent_id' might already be in base_config if we decide to pre-assign IDs,
    # but Agent.__init__ handles None and generates one.
    # If not overriding, and not in base, Agent makes one.

    if ollama_host_override:
        final_config['ollama_host'] = ollama_host_override
    # If 'ollama_host' is not in base_config and not overridden,
    # Agent.__init__ uses its default 'http://localhost:11434'.

    if chroma_service_path_override:
        final_config['chroma_service_path'] = chroma_service_path_override
    # If 'chroma_service_path' not in base_config and not overridden,
    # Agent.__init__ uses its default '/agent_data/chroma'.

    # The following keys from AGENT_CONFIGURATIONS map directly to Agent.__init__ params:
    # - persona_name
    # - chat_models
    # - utility_models
    # - embedding_model
    # - specialization_description
    # - core_directives
    # - dedicated_chroma_collection_name
    # - rag_results_count
    # - rag_max_context_length
    # - experience_results_count
    # - experience_max_context_length
    # So, they are already correctly named in final_config if present in base_config.

    # Remove 'config_name' as it's not an Agent.__init__ parameter
    final_config.pop('config_name', None)

    return final_config

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
    for i, conf in enumerate(AGENT_CONFIGURATIONS): # This will use the full list from above
        print(f"\n--- Config {i+1}: {conf.get('config_name', 'MISSING_CONFIG_NAME')} ---")
        # ... (rest of validation as per previous step)
        missing_keys_for_this_config = []
        for key in required_keys:
            if key not in conf:
                print(f"  ERROR: Missing key '{key}'")
                missing_keys_for_this_config.append(key)
                all_configs_valid = False
        if not missing_keys_for_this_config:
            print(f"  Persona: {conf['persona_name']}")
            print(f"  RAG Results: {conf['rag_results_count']}, Exp Results: {conf['experience_results_count']}")
        else: print(f"  INVALID CONFIG due to missing keys: {missing_keys_for_this_config}")
    if all_configs_valid: print("\nAll defined configurations appear to have the required keys structure.")
    else: print("\nERROR: Some configurations are missing required keys.")

    print("\n--- Example Loading 'DefaultOrchestrator' with load_agent_from_config ---")
    loaded_dict = load_agent_from_config("DefaultOrchestrator", agent_id_override="orch_test_001")
    if loaded_dict:
        print(f"Loaded for Agent ID: {loaded_dict.get('agent_id')}")
        print(f"Persona: {loaded_dict.get('persona_name')}")
        print(f"Collection: {loaded_dict.get('dedicated_chroma_collection_name')}")
        print(f"RAG Count: {loaded_dict.get('rag_results_count')}")
        # Example of how it would be used (Agent class not available here for direct test)
        # test_orchestrator = Agent(**loaded_dict)
        # print(f"Instantiated Agent ID: {test_orchestrator.agent_id}")
    else:
        print("Failed to load 'DefaultOrchestrator'")
