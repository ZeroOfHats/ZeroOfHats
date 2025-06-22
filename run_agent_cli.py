#!/usr/bin/env python3
import sys
import os

# Ensure the agent_zero module can be found
# This is important if running the script from the project root
# or if agent_zero is not installed as a package.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent_zero.self_play.agent import Agent
from agent_zero.config_manager import config # Global config instance
from agent_zero.llm_client import LLMClient # Though Agent uses it, good to have for direct tests

def main_cli():
    """
    Basic command-line interface for interacting with a single Agent Zero instance.
    """
    print("--- Agent Zero CLI (Phase 1: Basic Interaction) ---")
    print(f"Using Ollama host: {config.get_ollama_host()}")
    print(f"Default primary chat model for Agent: {config.get_primary_chat_model()}")
    print("Initializing agent...")

    # For Phase 1, we'll instantiate a default agent.
    # More complex agent selection or configuration loading can be added later.
    try:
        # Agent uses LLMClient and ConfigManager internally now
        agent = Agent(
            persona_name="CLI_Assistant",
            specialization_description="A helpful AI assistant responding to user queries via CLI.",
            core_directives=["Be concise.", "Answer directly based on your knowledge."]
            # Other parameters will use defaults from ConfigManager or Agent's own defaults
        )
        print(f"Agent '{agent.persona_name}' (ID: {agent.agent_id}) initialized successfully.")
        print(f"  Using primary model: {agent.primary_model}")
        print(f"  Agent's default memory collection: {agent.default_memory_collection}")
        print(f"  Agent's experience memory collection: {agent.experience_memory_collection_name}")
    except Exception as e:
        print(f"Error initializing agent: {e}")
        print("Please ensure Ollama is running and configured models are available.")
        return

    print("\nType 'exit', 'quit', or 'bye' to end the session.")
    print("Enter your prompt below:")

    while True:
        try:
            user_prompt = input(">>> ")
            if user_prompt.lower() in ['exit', 'quit', 'bye']:
                print("Exiting Agent Zero CLI. Goodbye!")
                break
            if not user_prompt.strip():
                continue

            # For Phase 1, a simple direct call to a method that invokes the LLM.
            # The `Agent` class doesn't have a simple `think(prompt)` method yet that
            # directly corresponds to a single user prompt for general chat without tasks.
            # We will use its internal `_llm_call` for this basic CLI.
            # A more sophisticated `think` or `process_user_query` method would be
            # part of future development (e.g. Phase 4).

            # Constructing a system message similar to how Agent does it internally for _llm_call
            system_message_parts = [
                f"You are an AI assistant: '{agent.persona_name}'.",
                f"Specialization: {agent.specialization_description}"
            ]
            if agent.core_directives:
                system_message_parts.append("Core Directives:")
                system_message_parts.extend(f"{i+1}. {d}" for i, d in enumerate(agent.core_directives))
            cli_system_message = "\n".join(system_message_parts)

            print(f"... (Thinking with model: {agent.primary_model}) ...")

            # Using the agent's llm_client directly for this simple CLI interaction
            # This bypasses any RAG or complex state management in the Agent for now.
            response = agent.llm_client.call_llm(
                prompt=user_prompt,
                system_message=cli_system_message,
                model=agent.primary_model # Use the agent's chosen primary model
            )

            # Alternatively, if we want to use the Agent's _llm_call method (which does the same):
            # response = agent._llm_call(prompt=user_prompt, model_category="chat")


            if "LLM call failed" in response or "Error:" in response :
                print(f"Agent Response (Error): {response}")
            else:
                print(f"Agent: {response}")

        except KeyboardInterrupt:
            print("\nExiting Agent Zero CLI (Ctrl+C). Goodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            # Optionally, decide if the loop should break on other errors

if __name__ == "__main__":
    # This ensures the script can be run directly, e.g., `python run_agent_cli.py`
    # from the project root.

    # Basic check for Ollama service before starting - COMMENTED OUT FOR NOW TO ISOLATE TIMEOUT
    # # This is a very simplified check.
    # try:
    #     print("Checking Ollama connection...")
    #     llm_client_test = LLMClient(host=config.get_ollama_host())
    #     # A lightweight way to test connection without making a full model call
    #     # client.list() would show models, but can be slow if many models.
    #     # A dummy embedding call is small.
    #     test_embed = llm_client_test.generate_embedding("test", model=config.get_embedding_model())
    #     if test_embed is None :
    #          # Check if it's a model not found error, which is different from connection error
    #         if "model not found" in llm_client_test.call_llm("test", model=config.get_embedding_model()): # A bit hacky
    #              print(f"Warning: Default embedding model '{config.get_embedding_model()}' may not be pulled. CLI might still work if chat models are present.")
    #         else:
    #             print(f"Failed to connect to Ollama or pull default embedding model '{config.get_embedding_model()}'.")
    #             print("Please ensure Ollama is running and the embedding model is available (`ollama pull {config.get_embedding_model()}`).")
    #             # sys.exit(1) # Optionally exit if connection fails
    #     else:
    #         print("Ollama connection seems OK (embedding model responded).")
    # except Exception as e:
    #     print(f"Could not establish initial connection to Ollama: {e}")
    #     print(f"Please ensure Ollama is running at {config.get_ollama_host()} and models are available.")
    #     # sys.exit(1) # Optionally exit

    main_cli()
