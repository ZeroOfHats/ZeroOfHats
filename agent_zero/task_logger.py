import logging
import os
from agent_zero.config_manager import ConfigManager
from agent_zero.file_utils import FileUtils

# Global logger instance, will be configured by setup_logging
# Using a specific name for the project's logger
AGENT_LOGGER_NAME = "AgentZero"
logger = logging.getLogger(AGENT_LOGGER_NAME)

def setup_logging(config: ConfigManager = None, logger_name: str = AGENT_LOGGER_NAME) -> logging.Logger:
    """
    Sets up global logging for the application based on ConfigManager settings.

    Args:
        config (ConfigManager, optional): An instance of ConfigManager.
                                          If None, a default ConfigManager will be instantiated.
        logger_name (str): The name of the logger to configure.

    Returns:
        logging.Logger: The configured logger instance.
    """
    if config is None:
        config = ConfigManager()

    current_logger = logging.getLogger(logger_name)

    # Prevent adding multiple handlers if already configured
    if current_logger.hasHandlers() and not getattr(current_logger, '_configured_by_agent_zero', False):
        # If handlers exist but not set by this function, respect them but warn
        # or clear them if we want full control. For now, let's assume we want full control if called.
        # current_logger.warning("Logger already has handlers. Reconfiguring.") # Optional warning
        for handler in current_logger.handlers[:]: # Iterate over a copy
            current_logger.removeHandler(handler)
        current_logger.propagate = False # Avoid issues with root logger if we add our own

    # Set log level
    log_level_str = config.log_level.upper()
    numeric_level = getattr(logging, log_level_str, logging.INFO)
    current_logger.setLevel(numeric_level)

    # Define log format
    log_format = '%(asctime)s - %(levelname)s - [%(name)s:%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
    formatter = logging.Formatter(log_format)

    # Console Handler
    if not any(isinstance(h, logging.StreamHandler) for h in current_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        current_logger.addHandler(console_handler)
        # current_logger.debug(f"Console handler added with level {log_level_str}.")

    # File Handler (optional)
    if config.log_to_file:
        if not any(isinstance(h, logging.FileHandler) for h in current_logger.handlers):
            try:
                log_file_path_sanitized = FileUtils.sanitize_filepath(config.log_file_path)

                # Use secure_join if a base directory for logs is established, otherwise ensure path is safe.
                # For now, assume log_file_path is relative to project root or an absolute safe path.
                # If it's just a filename, it will be in the current working directory.
                # Let's ensure the directory for the log file exists.
                log_dir = os.path.dirname(log_file_path_sanitized)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                    # current_logger.debug(f"Created log directory: {log_dir}")

                file_handler = logging.FileHandler(log_file_path_sanitized, mode='a', encoding='utf-8')
                file_handler.setFormatter(formatter)
                current_logger.addHandler(file_handler)
                # current_logger.debug(f"File handler added for {log_file_path_sanitized} with level {log_level_str}.")
            except Exception as e:
                current_logger.error(f"Failed to configure file logger for {config.log_file_path}: {e}", exc_info=True)

    setattr(current_logger, '_configured_by_agent_zero', True) # Mark as configured

    # Initial log message to confirm setup
    # current_logger.info(f"Logging setup complete. Level: {log_level_str}, File logging: {config.log_to_file}")
    return current_logger


class TaskLogger:
    """
    A wrapper class providing specific logging methods for agent tasks and activities.
    It uses the globally configured logger.
    """
    def __init__(self, component_name: str = None, logger_to_use: logging.Logger = None):
        """
        Initializes the TaskLogger.

        Args:
            component_name (str, optional): Name of the component using this logger.
                                           This will be part of the log message or logger name.
            logger_to_use (logging.Logger, optional): An existing logger instance to use.
                                                      Defaults to the global AGENT_LOGGER_NAME.
        """
        if logger_to_use:
            self.logger = logger_to_use
        elif component_name:
            self.logger = logging.getLogger(f"{AGENT_LOGGER_NAME}.{component_name}")
        else:
            self.logger = logging.getLogger(AGENT_LOGGER_NAME) # Default to the main app logger

        # Ensure the base logger is configured if this is called before global setup
        # This is a bit of a chicken-and-egg, ideally setup_logging is called once at app start.
        if not getattr(logging.getLogger(AGENT_LOGGER_NAME), '_configured_by_agent_zero', False):
            # print(f"Warning: TaskLogger instantiated for '{component_name}' before global logging setup. Attempting default setup.")
            setup_logging() # Attempt to setup with default config if not already done.


    def log_event(self, event_type: str, details: dict, level: int = logging.INFO):
        """Logs a structured event."""
        message = f"Event: {event_type} - Details: {json.dumps(details)}"
        self.logger.log(level, message)

    def task_started(self, task_id: str, task_description: str, objective_id: str = None):
        details = {"task_id": task_id, "description": task_description}
        if objective_id:
            details["objective_id"] = objective_id
        self.log_event("TaskStarted", details, logging.INFO)

    def task_progress(self, task_id: str, progress_message: str, percentage: float = None):
        details = {"task_id": task_id, "message": progress_message}
        if percentage is not None:
            details["percentage"] = percentage
        self.log_event("TaskProgress", details, logging.DEBUG) # Usually debug level

    def task_completed(self, task_id: str, result: str = None, metrics: dict = None):
        details = {"task_id": task_id}
        if result:
            details["result"] = result
        if metrics:
            details["metrics"] = metrics
        self.log_event("TaskCompleted", details, logging.INFO)

    def task_failed(self, task_id: str, error_message: str, error_details: dict = None):
        details = {"task_id": task_id, "error": error_message}
        if error_details:
            details["error_details"] = error_details
        self.log_event("TaskFailed", details, logging.ERROR)

    def llm_request(self, model: str, prompt: any, options: dict = None):
        # Prompt could be large, consider truncating or summarizing if necessary for logs
        details = {"model": model, "prompt_preview": str(prompt)[:200] + "..." if len(str(prompt)) > 200 else str(prompt)}
        if options:
            details["options"] = options
        self.log_event("LLMRequest", details, logging.DEBUG) # Debug, as it can be verbose

    def llm_response(self, model: str, response: any, duration_ms: int = None):
        # Response could be large
        details = {"model": model, "response_preview": str(response)[:200] + "..." if len(str(response)) > 200 else str(response)}
        if duration_ms is not None:
            details["duration_ms"] = duration_ms
        self.log_event("LLMResponse", details, logging.DEBUG) # Debug

    def llm_error(self, model: str, error_message: str, prompt: any = None):
        details = {"model": model, "error": error_message}
        if prompt:
            details["prompt_preview"] = str(prompt)[:200] + "..." if len(str(prompt)) > 200 else str(prompt)
        self.log_event("LLMError", details, logging.ERROR)

    def general_info(self, message: str, **kwargs):
        self.logger.info(f"{message} {json.dumps(kwargs) if kwargs else ''}")

    def general_warning(self, message: str, **kwargs):
        self.logger.warning(f"{message} {json.dumps(kwargs) if kwargs else ''}")

    def general_error(self, message: str, exc_info=False, **kwargs):
        self.logger.error(f"{message} {json.dumps(kwargs) if kwargs else ''}", exc_info=exc_info)

    def general_debug(self, message: str, **kwargs):
        self.logger.debug(f"{message} {json.dumps(kwargs) if kwargs else ''}")


if __name__ == '__main__':
    import json # Required for TaskLogger methods if not already imported globally

    # --- Test Basic Logging Setup ---
    print("--- Testing Basic Logging Setup ---")
    # Create a dummy .env for this test
    with open(".env.test_logger", "w") as f:
        f.write("LOG_LEVEL=DEBUG\n")
        f.write("LOG_TO_FILE=True\n")
        f.write("LOG_FILE_PATH=./temp_test_logs/test_agent_zero.log\n") # Use a subdirectory

    test_config = ConfigManager(dotenv_path=".env.test_logger")

    # Clean up old log file if it exists to ensure fresh test
    log_file_to_test = FileUtils.sanitize_filepath(test_config.log_file_path)
    if os.path.exists(log_file_to_test):
        os.remove(log_file_to_test)
    if os.path.exists(os.path.dirname(log_file_to_test)):
        # remove dir if empty, otherwise just the file
        if not os.listdir(os.path.dirname(log_file_to_test)):
             os.rmdir(os.path.dirname(log_file_to_test))


    # Setup logging using the test config
    # This will configure the global AGENT_LOGGER_NAME logger
    main_logger = setup_logging(config=test_config)
    main_logger.info("This is an INFO message from main_logger after setup.")
    main_logger.debug("This is a DEBUG message from main_logger after setup.")

    # Test if file logging worked
    assert os.path.exists(log_file_to_test), f"Log file {log_file_to_test} was not created."
    with open(log_file_to_test, "r") as f:
        log_content = f.read()
        assert "INFO message from main_logger" in log_content
        assert "DEBUG message from main_logger" in log_content
    print(f"Basic logging to console and file '{log_file_to_test}' verified.")


    # --- Test TaskLogger ---
    print("\n--- Testing TaskLogger ---")
    # Assuming setup_logging has already configured the root 'AgentZero' logger
    # TaskLogger will use sub-loggers or the main logger

    # Test TaskLogger with a specific component name
    component_logger = TaskLogger(component_name="DecisionMaker")
    component_logger.general_info("DecisionMaker component initialized.")
    component_logger.task_started(task_id="task_123", task_description="Analyze market data", objective_id="obj_001")
    component_logger.llm_request(model="claude-3", prompt="What are the current trends?")
    component_logger.llm_response(model="claude-3", response="Trends are positive.", duration_ms=1200)
    component_logger.task_completed(task_id="task_123", result="Market is bullish.")

    # Test TaskLogger using the default (main agent) logger
    default_task_logger = TaskLogger() # Uses AGENT_LOGGER_NAME
    default_task_logger.general_warning("A general warning from default task logger.")
    default_task_logger.task_failed(task_id="task_456", error_message="Network timeout during API call")

    print("TaskLogger specific methods tested. Check console and log file for output.")

    # Verify TaskLogger messages in the file
    with open(log_file_to_test, "r") as f:
        log_content_after_tasklogger = f.read()
        assert "DecisionMaker" in log_content_after_tasklogger # Check component name in log
        assert "TaskStarted" in log_content_after_tasklogger
        assert "task_id_task_123" # Check for quotes around task_id if json stringified
        assert "LLMRequest" in log_content_after_tasklogger
        assert "TaskFailed" in log_content_after_tasklogger
        assert "Network timeout" in log_content_after_tasklogger
    print(f"TaskLogger messages verified in '{log_file_to_test}'.")

    # --- Test logging without prior setup (TaskLogger should trigger it) ---
    # To do this properly, we need to reset the logger's state or use a different logger name.
    # For simplicity in __main__, we assume the previous setup affects the global state.
    # A more isolated test would use unittest.mock or different logger names.
    # print("\n--- Testing TaskLogger triggering setup (conceptual) ---")
    # Note: This test is harder to make fully isolated in a single script run without resetting logging internals.
    # If AGENT_LOGGER_NAME was already configured, this won't re-trigger in a way that's easily visible
    # unless we clear handlers and the '_configured_by_agent_zero' flag.
    # For now, we'll assume the earlier setup_logging call is the primary one.

    # Cleanup
    if os.path.exists(".env.test_logger"):
        os.remove(".env.test_logger")
    # Optionally remove the created log file and directory if it's empty
    # if os.path.exists(log_file_to_test):
    #     os.remove(log_file_to_test)
    # if os.path.exists(os.path.dirname(log_file_to_test)) and not os.listdir(os.path.dirname(log_file_to_test)):
    #     os.rmdir(os.path.dirname(log_file_to_test))
    # print(f"Cleaned up .env.test_logger. Log file '{log_file_to_test}' remains for inspection.")

    print("\nTaskLogger tests completed.")
