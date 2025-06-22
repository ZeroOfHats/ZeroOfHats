import os
import sys
import logging

# Add project root to Python path to allow module imports from agent_zero
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agent_zero.config_manager import ConfigManager
from agent_zero.llm_client import LLMClient
from agent_zero.task_logger import setup_logging, AGENT_LOGGER_NAME # Use the main logger name

# Get the specific logger instance for this script, child of the main agent logger
script_logger = logging.getLogger(f"{AGENT_LOGGER_NAME}.SimpleLLMTest")

def run_llm_test():
    """
    Initializes ConfigManager, LLMClient, and attempts a simple LLM generation.
    """
    try:
        # 1. Load Configuration
        script_logger.info("Initializing Configuration Manager...")
        config = ConfigManager() # Loads from .env or environment variables

        # 2. Setup Logging (using the configuration)
        # This will configure the root AGENT_LOGGER_NAME and its children
        setup_logging(config)
        script_logger.info("Logging setup complete based on configuration.")
        script_logger.info(f"Using Ollama URL: {config.ollama_url}")
        script_logger.info(f"Using default Ollama model: {config.ollama_default_model}")

        # 3. Initialize LLMClient
        script_logger.info("Initializing LLM Client...")
        llm = LLMClient(
            host=config.ollama_host, # Or directly use config.ollama_url if LLMClient takes full URL
            port=config.ollama_port,
            default_model=config.ollama_default_model
        )
        # If LLMClient is changed to take full url: LLMClient(ollama_url=config.ollama_url, ...)

    except ValueError as ve:
        script_logger.error(f"Configuration error: {ve}", exc_info=True)
        script_logger.error("Please ensure your .env file or environment variables are correctly set.")
        return
    except Exception as e:
        script_logger.error(f"An unexpected error occurred during setup: {e}", exc_info=True)
        return

    # 4. List available models from Ollama
    try:
        script_logger.info("Attempting to list available models from Ollama...")
        available_models = llm.list_models()
        if available_models:
            script_logger.info(f"Available models: {[m.get('name') for m in available_models]}")
            # Check if the configured default model is available
            if not any(m.get('name', '').startswith(config.ollama_default_model.split(':')[0]) for m in available_models):
                script_logger.warning(f"The configured default model '{config.ollama_default_model}' "
                                      f"does not appear to be available in Ollama. "
                                      f"You may need to pull it first (e.g., `ollama pull {config.ollama_default_model}`).")
        else:
            script_logger.warning("No models found in Ollama or Ollama is not accessible.")
            script_logger.warning(f"Please ensure Ollama is running at {config.ollama_url} and you have pulled some models.")
            # Optionally, could exit here or try generation anyway.
            # For this test, we'll proceed to try generation.

    except requests.exceptions.ConnectionError:
        script_logger.error(f"Could not connect to Ollama at {config.ollama_url}. "
                            f"Please ensure Ollama is running and accessible.")
        return
    except Exception as e:
        script_logger.error(f"Error listing models: {e}", exc_info=True)
        # Continue to generation test anyway, it might provide more specific errors.

    # 5. Attempt a simple generation
    prompt = "Why is the sky blue? Explain briefly."
    target_model = config.ollama_default_model # Use the configured default model

    script_logger.info(f"\nAttempting to generate text using model '{target_model}' with prompt: '{prompt}'")

    try:
        # You can override num_predict or other options here if desired for the test
        response_data = llm.generate(prompt=prompt, model=target_model, num_predict=100)

        if response_data and response_data.get("response"):
            script_logger.info("--- LLM Generation Successful ---")
            script_logger.info(f"Model Used: {response_data.get('model', 'N/A')}")
            script_logger.info(f"Prompt: {prompt}")
            script_logger.info(f"Response: {response_data['response'].strip()}")
            if response_data.get("total_duration"):
                duration_seconds = response_data['total_duration'] / 1_000_000_000  # Nanoseconds to seconds
                script_logger.info(f"Generation Duration: {duration_seconds:.2f} seconds")
        elif response_data and response_data.get("error"):
            script_logger.error(f"LLM Generation failed with API error: {response_data['error']}")
            script_logger.error(f"Make sure the model '{target_model}' is available in Ollama. You might need to run: `ollama pull {target_model}`")
        else:
            script_logger.error(f"LLM Generation failed. Unexpected response format: {response_data}")

    except requests.exceptions.ConnectionError:
        script_logger.error(f"Could not connect to Ollama at {config.ollama_url} during generation. "
                            f"Please ensure Ollama is running.")
    except ValueError as ve: # Handles errors like Ollama API error from client
        script_logger.error(f"LLM Generation failed: {ve}")
    except Exception as e:
        script_logger.error(f"An unexpected error occurred during LLM generation: {e}", exc_info=True)

if __name__ == "__main__":
    # Initial basic logging setup for the script itself before full config is loaded
    # This ensures that issues during ConfigManager init are also logged.
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - [%(name)s:%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
                        stream=sys.stdout) # Log to stdout initially

    script_logger.info("Starting Simple LLM Test Script...")
    run_llm_test()
    script_logger.info("Simple LLM Test Script finished.")
