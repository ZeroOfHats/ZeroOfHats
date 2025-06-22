# agent_zero/config_manager.py

from typing import List, Dict, Any, Optional
import os

# --- Core Configuration Settings ---
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

# --- Default Model Lists ---
# These can be overridden by environment variables or specific configurations
DEFAULT_CHAT_MODEL_LIST = ["mistral:7b-instruct-q5_K_M", "llama2:7b-chat-q5_K_M"]
DEFAULT_UTILITY_MODEL_LIST = ["tinydolphin:1.1b-q4_K_M", "orca-mini:3b-q4_K_M"]
DEFAULT_EMBEDDING_MODEL_NAME = "nomic-embed-text:latest"
DEFAULT_FALLBACK_MODEL = "orca-mini:3b-q4_K_M" # A small, likely available model

# --- Agent-Specific Defaults (can be part of a more complex config structure later) ---
DEFAULT_AGENT_PERSONA = "AgentZeroDefault"
DEFAULT_AGENT_SPECIALIZATION = "A general-purpose AI assistant."
DEFAULT_AGENT_CORE_DIRECTIVES = ["Be helpful and efficient.", "Provide accurate information."]

# --- ChromaDB Configuration ---
DEFAULT_CHROMA_SERVICE_PATH = "/agent_data/chroma" # Path inside the Docker container
DEFAULT_AGENT_MEMORY_COLLECTION_PREFIX = "agent_mem"
DEFAULT_EXPERIENCE_MEMORY_COLLECTION = "agent_experience_memory"

# --- RAG/Experience Defaults for Agents ---
DEFAULT_RAG_RESULTS_COUNT = 3
DEFAULT_RAG_MAX_CONTEXT_LENGTH = 2500
DEFAULT_EXPERIENCE_RESULTS_COUNT = 2
DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH = 1200

class ConfigManager:
    """
    Manages configuration settings for Agent Zero.
    Prioritizes environment variables over hardcoded defaults.
    """
    def __init__(self):
        # --- LLM Configuration ---
        self.ollama_host: str = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)

        # Model lists can be comma-separated strings in env vars
        self.chat_model_list: List[str] = self._get_env_list("AGENT_CHAT_MODELS", DEFAULT_CHAT_MODEL_LIST)
        self.utility_model_list: List[str] = self._get_env_list("AGENT_UTILITY_MODELS", DEFAULT_UTILITY_MODEL_LIST)
        self.embedding_model_name: str = os.getenv("AGENT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL_NAME)
        self.fallback_model: str = os.getenv("AGENT_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)

        # --- Agent Defaults (can be expanded) ---
        self.default_persona: str = os.getenv("AGENT_DEFAULT_PERSONA", DEFAULT_AGENT_PERSONA)
        self.default_specialization: str = os.getenv("AGENT_DEFAULT_SPECIALIZATION", DEFAULT_AGENT_SPECIALIZATION)
        self.default_core_directives: List[str] = self._get_env_list("AGENT_DEFAULT_DIRECTIVES", DEFAULT_AGENT_CORE_DIRECTIVES, separator="|") # Use pipe for multi-line directives

        # --- ChromaDB Configuration ---
        self.chroma_service_path: str = os.getenv("CHROMA_SERVICE_PATH", DEFAULT_CHROMA_SERVICE_PATH)
        self.agent_memory_collection_prefix: str = os.getenv("CHROMA_AGENT_MEM_PREFIX", DEFAULT_AGENT_MEMORY_COLLECTION_PREFIX)
        self.experience_memory_collection: str = os.getenv("CHROMA_EXPERIENCE_MEM_COLLECTION", DEFAULT_EXPERIENCE_MEMORY_COLLECTION)

        # --- RAG/Experience Defaults ---
        self.rag_results_count: int = self._get_env_int("AGENT_RAG_RESULTS_COUNT", DEFAULT_RAG_RESULTS_COUNT)
        self.rag_max_context_length: int = self._get_env_int("AGENT_RAG_MAX_CONTEXT_LENGTH", DEFAULT_RAG_MAX_CONTEXT_LENGTH)
        self.experience_results_count: int = self._get_env_int("AGENT_EXPERIENCE_RESULTS_COUNT", DEFAULT_EXPERIENCE_RESULTS_COUNT)
        self.experience_max_context_length: int = self._get_env_int("AGENT_EXPERIENCE_MAX_CONTEXT_LENGTH", DEFAULT_EXPERIENCE_MAX_CONTEXT_LENGTH)

        print("ConfigManager initialized.")
        # print(f"  Ollama Host: {self.ollama_host}") # For debugging
        # print(f"  Chat Models: {self.chat_model_list}") # For debugging

    def _get_env_list(self, env_var_name: str, default: List[str], separator: str = ',') -> List[str]:
        env_val = os.getenv(env_var_name)
        if env_val:
            return [item.strip() for item in env_val.split(separator) if item.strip()]
        return default

    def _get_env_int(self, env_var_name: str, default: int) -> int:
        env_val = os.getenv(env_var_name)
        if env_val and env_val.isdigit():
            return int(env_val)
        return default

    def get_ollama_host(self) -> str:
        return self.ollama_host

    def get_chat_model_list(self) -> List[str]:
        return list(self.chat_model_list) # Return a copy

    def get_primary_chat_model(self) -> str:
        return self.chat_model_list[0] if self.chat_model_list else self.fallback_model

    def get_utility_model_list(self) -> List[str]:
        return list(self.utility_model_list) # Return a copy

    def get_primary_utility_model(self) -> str:
        return self.utility_model_list[0] if self.utility_model_list else self.fallback_model

    def get_embedding_model(self) -> str:
        return self.embedding_model_name

    def get_fallback_model(self) -> str:
        return self.fallback_model

    def get_chroma_service_path(self) -> str:
        return self.chroma_service_path

    # Add other getters as needed for specific configurations

# Global instance (Singleton-like access for simplicity in this project)
# This allows other modules to import `config_manager` and access `config.PROPERTY`
config = ConfigManager()

if __name__ == '__main__':
    print("--- ConfigManager Test ---")
    print(f"Ollama Host: {config.get_ollama_host()}")
    print(f"Primary Chat Model: {config.get_primary_chat_model()}")
    print(f"All Chat Models: {config.get_chat_model_list()}")
    print(f"Primary Utility Model: {config.get_primary_utility_model()}")
    print(f"Embedding Model: {config.get_embedding_model()}")
    print(f"Fallback Model: {config.get_fallback_model()}")
    print(f"Chroma Service Path: {config.get_chroma_service_path()}")
    print(f"Default Persona: {config.default_persona}")
    print(f"RAG Results Count: {config.rag_results_count}")

    print("\n--- Testing with Environment Variable Overrides (Example) ---")
    print("To test overrides, you would set environment variables before running, e.g.:")
    print("  export OLLAMA_HOST=http://custom.host:12345")
    print("  export AGENT_CHAT_MODELS=custom_model_1:latest,custom_model_2:latest")
    print("  export AGENT_EMBEDDING_MODEL=custom_embed_model:v1")
    print("  export AGENT_RAG_RESULTS_COUNT=5")
    print("Then re-run this script.")

    # Example of how a module would use it:
    # from agent_zero.config_manager import config
    # ollama_endpoint = config.get_ollama_host()
    # main_model = config.get_primary_chat_model()
    # print(f"\nUsage example: Ollama at {ollama_endpoint}, Main model {main_model}")
    print("\nConfigManager test finished.")
