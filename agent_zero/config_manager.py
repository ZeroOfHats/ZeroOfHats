import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages configuration settings for the Agent Zero application.
    Loads settings from environment variables and/or a .env file.
    """
    def __init__(self, dotenv_path: str = None):
        """
        Initializes the ConfigManager and loads configurations.

        Args:
            dotenv_path (str, optional): Path to a .env file.
                                         If None, it will try to load from '.env' in the current directory or parent directories.
        """
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path)
            logger.info(f"Loaded .env file from specified path: {dotenv_path}")
        else:
            # Try to find .env in current or parent dirs, useful for tests vs. main script
            if load_dotenv():
                 logger.info(f"Loaded .env file from default location.")
            else:
                 # Check one level up if running from a subdirectory like /tests
                 if load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env')):
                     logger.info(f"Loaded .env file from parent directory.")
                 else:
                    logger.info("No .env file found or python-dotenv not installed. Relying solely on environment variables.")

        # LLM (Ollama) Configuration
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost")
        self.ollama_port = int(os.getenv("OLLAMA_PORT", "11434"))
        self.ollama_default_model = os.getenv("OLLAMA_DEFAULT_MODEL", "phi3:mini") # A smaller default model
        self.ollama_request_timeout = int(os.getenv("OLLAMA_REQUEST_TIMEOUT", "300")) # seconds

        # ChromaDB Configuration
        self.chromadb_host = os.getenv("CHROMADB_HOST", "localhost") # ChromaDB client uses host directly, not http://
        self.chromadb_port = int(os.getenv("CHROMADB_PORT", "8000"))
        self.chromadb_default_collection_name = os.getenv("CHROMADB_DEFAULT_COLLECTION_NAME", "baby_zero_store")
        self.chromadb_experience_collection_name = os.getenv("CHROMADB_EXPERIENCE_COLLECTION_NAME", "baby_zero_experience")
        # For Chroma client: chromadb.HttpClient(host=self.chromadb_host, port=self.chromadb_port)

        # Agent Configuration
        self.agent_default_persona = os.getenv("AGENT_DEFAULT_PERSONA", "helpful assistant")
        self.agent_max_interactions = int(os.getenv("AGENT_MAX_INTERACTIONS", "50"))

        # Logging Configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_to_file = os.getenv("LOG_TO_FILE", "False").lower() == "true"
        self.log_file_path = os.getenv("LOG_FILE_PATH", "agent_zero.log")

        self._validate_configs()
        self._log_loaded_configs()

    def _validate_configs(self):
        """
        Validates critical configuration settings.
        Raises ValueError if a required setting is missing or invalid.
        """
        if not self.ollama_host:
            raise ValueError("OLLAMA_HOST configuration is missing.")
        if not self.ollama_port or not (1 <= self.ollama_port <= 65535):
            raise ValueError("OLLAMA_PORT configuration is missing or invalid.")
        if not self.ollama_default_model:
            raise ValueError("OLLAMA_DEFAULT_MODEL configuration is missing.")

        if not self.chromadb_host:
            raise ValueError("CHROMADB_HOST configuration is missing.")
        if not self.chromadb_port or not (1 <= self.chromadb_port <= 65535):
            raise ValueError("CHROMADB_PORT configuration is missing or invalid.")

        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in log_levels:
            logger.warning(f"Invalid LOG_LEVEL '{self.log_level}'. Defaulting to INFO. Valid options: {log_levels}")
            self.log_level = "INFO"

    def _log_loaded_configs(self):
        """Logs the loaded configurations, masking sensitive ones if any in the future."""
        # In the future, if sensitive keys are added, they should be masked here.
        logger.info("Configuration loaded:")
        logger.info(f"  OLLAMA_HOST: {self.ollama_host}")
        logger.info(f"  OLLAMA_PORT: {self.ollama_port}")
        logger.info(f"  OLLAMA_DEFAULT_MODEL: {self.ollama_default_model}")
        logger.info(f"  OLLAMA_REQUEST_TIMEOUT: {self.ollama_request_timeout}")
        logger.info(f"  CHROMADB_HOST: {self.chromadb_host}")
        logger.info(f"  CHROMADB_PORT: {self.chromadb_port}")
        logger.info(f"  CHROMADB_DEFAULT_COLLECTION_NAME: {self.chromadb_default_collection_name}")
        logger.info(f"  CHROMADB_EXPERIENCE_COLLECTION_NAME: {self.chromadb_experience_collection_name}")
        logger.info(f"  AGENT_DEFAULT_PERSONA: {self.agent_default_persona}")
        logger.info(f"  AGENT_MAX_INTERACTIONS: {self.agent_max_interactions}")
        logger.info(f"  LOG_LEVEL: {self.log_level}")
        logger.info(f"  LOG_TO_FILE: {self.log_to_file}")
        logger.info(f"  LOG_FILE_PATH: {self.log_file_path}")

    # Provide properties for easy access if needed, though direct attribute access is also fine.
    @property
    def ollama_url(self) -> str:
        # Ensure scheme is present for requests library if OLLAMA_HOST doesn't include it
        if "://" in self.ollama_host:
            return f"{self.ollama_host}:{self.ollama_port}"
        return f"http://{self.ollama_host}:{self.ollama_port}"


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Create a dummy .env file for testing
    with open(".env.test_config_manager", "w") as f:
        f.write("OLLAMA_HOST=http://testhost\n")
        f.write("OLLAMA_PORT=12345\n")
        f.write("OLLAMA_DEFAULT_MODEL=testmodel\n")
        f.write("CHROMADB_HOST=dbhost\n") # No scheme for chromadb client
        f.write("CHROMADB_PORT=54321\n")
        f.write("LOG_LEVEL=DEBUG\n")

    logger.info("--- Testing ConfigManager with .env.test_config_manager ---")
    try:
        config = ConfigManager(dotenv_path=".env.test_config_manager")
        assert config.ollama_host == "http://testhost"
        assert config.ollama_port == 12345
        assert config.ollama_url == "http://testhost:12345" # Testing property
        assert config.ollama_default_model == "testmodel"
        assert config.chromadb_host == "dbhost"
        assert config.chromadb_port == 54321
        assert config.log_level == "DEBUG"
        logger.info("ConfigManager loaded test .env successfully.")
    except Exception as e:
        logger.error(f"Error during ConfigManager test with .env: {e}", exc_info=True)
    finally:
        if os.path.exists(".env.test_config_manager"):
            os.remove(".env.test_config_manager")

    logger.info("\n--- Testing ConfigManager with environment variables (and no .env file) ---")
    # Temporarily set environment variables for this test
    os.environ["OLLAMA_HOST"] = "http://envhost"
    os.environ["OLLAMA_PORT"] = "23456"
    os.environ["OLLAMA_DEFAULT_MODEL"] = "envmodel"
    os.environ["CHROMADB_HOST"] = "envdbhost"
    os.environ["CHROMADB_PORT"] = "65432"
    os.environ["LOG_LEVEL"] = "WARNING"
    # Ensure no other .env file is loaded by mistake for this specific test part
    # by passing a non-existent dotenv_path if default loading is too broad.
    # However, the current ConfigManager logic tries to find .env, so this test
    # primarily ensures direct env vars override or are used if .env is not found.

    try:
        # To ensure ONLY env vars are used, we'd ideally run this where no .env is findable
        # or ensure our test .env was removed.
        config_env = ConfigManager(dotenv_path=".nonexistentenv") # Force no .env loading
        assert config_env.ollama_host == "http://envhost"
        assert config_env.ollama_port == 23456
        assert config_env.ollama_url == "http://envhost:23456"
        assert config_env.ollama_default_model == "envmodel"
        assert config_env.chromadb_host == "envdbhost"
        assert config_env.chromadb_port == 65432
        assert config_env.log_level == "WARNING"
        logger.info("ConfigManager loaded environment variables successfully.")
    except Exception as e:
        logger.error(f"Error during ConfigManager test with env vars: {e}", exc_info=True)
    finally:
        # Clean up environment variables set for the test
        del os.environ["OLLAMA_HOST"]
        del os.environ["OLLAMA_PORT"]
        del os.environ["OLLAMA_DEFAULT_MODEL"]
        del os.environ["CHROMADB_HOST"]
        del os.environ["CHROMADB_PORT"]
        del os.environ["LOG_LEVEL"]

    logger.info("\n--- Testing ConfigManager with missing critical env var ---")
    # Remove a critical env var to test validation
    original_ollama_host = os.getenv("OLLAMA_HOST_TEMP", "http://localhost") # Store if exists
    if "OLLAMA_HOST" in os.environ: del os.environ["OLLAMA_HOST"] # remove if set by prev test

    # Temporarily clear OLLAMA_HOST for this specific test case
    # This requires careful handling if other tests or the environment itself sets it.
    # For a clean test, it's better to run this in an isolated process or ensure
    # that the ConfigManager is instantiated after clearing the specific env var.

    # To be safe, let's use a temporary variable that ConfigManager won't pick up
    # and ensure OLLAMA_HOST is not set when we instantiate.

    # This part of the test is tricky without modifying global os.environ directly and then cleaning up.
    # The provided ConfigManager already tries to load from os.getenv,
    # so if OLLAMA_HOST is globally set (e.g. in the shell running the agent), this test won't be isolated.
    # For a true unit test of this, one might mock os.getenv.
    # The current test structure for `if __name__ == '__main__':` is more of an integration test.

    # Assuming we can unset it for the scope of this test:
    _old_host = os.environ.pop("OLLAMA_HOST", None)
    try:
        config_missing = ConfigManager(dotenv_path=".nonexistentenv") # Ensure no .env loads
        logger.error("ValueError was expected for missing OLLAMA_HOST but not raised.")
    except ValueError as ve:
        logger.info(f"Successfully caught expected ValueError: {ve}")
        assert "OLLAMA_HOST configuration is missing" in str(ve)
    except Exception as e:
        logger.error(f"An unexpected error occurred during missing config test: {e}", exc_info=True)
    finally:
        if _old_host is not None: # Restore if it was popped
            os.environ["OLLAMA_HOST"] = _old_host

    logger.info("ConfigManager tests completed.")
