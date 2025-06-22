import unittest
import os
import sys

# Add project root to Python path to allow module imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agent_zero.config_manager import ConfigManager
from agent_zero.task_logger import setup_logging # For logging within tests if needed

# Setup basic logging for the test execution itself (optional)
# setup_logging() # Or configure a specific test logger

class TestConfigManager(unittest.TestCase):

    def setUp(self):
        """Setup for each test method."""
        self.test_env_file = ".env.test_config_manager_unittest"
        self.original_env_vars = {}
        self.vars_to_manage = [
            "OLLAMA_HOST", "OLLAMA_PORT", "OLLAMA_DEFAULT_MODEL",
            "CHROMADB_HOST", "CHROMADB_PORT", "LOG_LEVEL"
        ]
        # Store original environment variables
        for var_name in self.vars_to_manage:
            if var_name in os.environ:
                self.original_env_vars[var_name] = os.environ[var_name]

        # Clear these vars to ensure tests are isolated
        for var_name in self.vars_to_manage:
            if var_name in os.environ:
                del os.environ[var_name]

    def tearDown(self):
        """Teardown after each test method."""
        if os.path.exists(self.test_env_file):
            os.remove(self.test_env_file)

        # Restore original environment variables
        for var_name, value in self.original_env_vars.items():
            os.environ[var_name] = value
        # Remove any vars that were set during tests but not originally present
        for var_name in self.vars_to_manage:
            if var_name not in self.original_env_vars and var_name in os.environ:
                del os.environ[var_name]


    def test_load_from_dotenv_file(self):
        with open(self.test_env_file, "w") as f:
            f.write("OLLAMA_HOST=http://dotenvhost\n")
            f.write("OLLAMA_PORT=11111\n")
            f.write("OLLAMA_DEFAULT_MODEL=dotenvmodel\n")
            f.write("CHROMADB_HOST=dbdotenv\n")
            f.write("CHROMADB_PORT=22222\n")
            f.write("LOG_LEVEL=DEBUG\n")

        config = ConfigManager(dotenv_path=self.test_env_file)
        self.assertEqual(config.ollama_host, "http://dotenvhost")
        self.assertEqual(config.ollama_port, 11111)
        self.assertEqual(config.ollama_default_model, "dotenvmodel")
        self.assertEqual(config.chromadb_host, "dbdotenv")
        self.assertEqual(config.chromadb_port, 22222)
        self.assertEqual(config.log_level, "DEBUG")

    def test_load_from_environment_variables(self):
        os.environ["OLLAMA_HOST"] = "http://envhost"
        os.environ["OLLAMA_PORT"] = "33333"
        os.environ["OLLAMA_DEFAULT_MODEL"] = "envmodel"
        os.environ["CHROMADB_HOST"] = "dbenv"
        os.environ["CHROMADB_PORT"] = "44444"
        os.environ["LOG_LEVEL"] = "WARNING"

        # Pass a non-existent dotenv_path to ensure .env isn't accidentally loaded
        config = ConfigManager(dotenv_path=".nonexistentenvfileintest")
        self.assertEqual(config.ollama_host, "http://envhost")
        self.assertEqual(config.ollama_port, 33333)
        self.assertEqual(config.ollama_default_model, "envmodel")
        self.assertEqual(config.chromadb_host, "dbenv")
        self.assertEqual(config.chromadb_port, 44444)
        self.assertEqual(config.log_level, "WARNING")

    def test_default_values(self):
        # Ensure no .env file and no relevant env vars are set
        config = ConfigManager(dotenv_path=".nonexistentenvfileintest_defaults")

        self.assertEqual(config.ollama_host, "http://localhost") # Default
        self.assertEqual(config.ollama_port, 11434) # Default
        self.assertTrue(config.ollama_default_model) # Check it has some default
        self.assertEqual(config.chromadb_host, "localhost") # Default
        self.assertEqual(config.chromadb_port, 8000) # Default
        self.assertEqual(config.log_level, "INFO") # Default

    def test_validation_error_missing_critical_config(self):
        # OLLAMA_DEFAULT_MODEL is critical and has no fallback that would make it empty
        # For this test, let's assume OLLAMA_HOST is made empty
        # Note: ConfigManager currently has defaults for OLLAMA_HOST, so we need to test one that can be truly empty.
        # The validation logic raises ValueError if a required setting is empty AFTER trying env and defaults.
        # Let's test by setting an env var to an empty string for a usually defaulted but validated field.

        # According to current ConfigManager, OLLAMA_HOST, PORT, DEFAULT_MODEL are critical.
        # And they all have defaults. So, to trigger validation, one would need to provide an *invalid* value.
        # E.g. OLLAMA_PORT="invalid_port_string"

        os.environ["OLLAMA_PORT"] = "notanumber"
        with self.assertRaises(ValueError) as context: # Casting to int will fail
             ConfigManager(dotenv_path=".nonexistentenvfileintest_validation")
        self.assertTrue("invalid literal for int()" in str(context.exception) or "OLLAMA_PORT" in str(context.exception))
        del os.environ["OLLAMA_PORT"] # Clean up

        # Test invalid LOG_LEVEL (it defaults, but logs a warning - not a ValueError)
        os.environ["LOG_LEVEL"] = "INVALIDLOGLEVEL"
        config = ConfigManager(dotenv_path=".nonexistentenvfileintest_validation_log")
        self.assertEqual(config.log_level, "INFO") # Should default to INFO after warning
        del os.environ["LOG_LEVEL"]


    def test_env_overrides_dotenv(self):
        with open(self.test_env_file, "w") as f:
            f.write("OLLAMA_HOST=http://dotenvhost\n")
            f.write("OLLAMA_PORT=11111\n")

        os.environ["OLLAMA_HOST"] = "http://envhost_override"
        os.environ["OLLAMA_PORT"] = "55555"

        config = ConfigManager(dotenv_path=self.test_env_file)

        self.assertEqual(config.ollama_host, "http://envhost_override") # Env var should take precedence
        self.assertEqual(config.ollama_port, 55555) # Env var should take precedence

if __name__ == '__main__':
    unittest.main()
