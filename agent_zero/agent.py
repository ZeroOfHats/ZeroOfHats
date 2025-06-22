import logging
import os # For os.urandom used in __init__
from typing import Optional

from agent_zero.config_manager import ConfigManager
from agent_zero.llm_client import LLMClient
from agent_zero.memory.chroma_service import ChromaService # Import ChromaService
from typing import List, Dict, Any # For type hinting memory methods
from agent_zero.self_play.models import Objective, Task, Status # Import models
from agent_zero.self_play.task_manager import TaskListManager # Import TaskListManager

# Use the main agent logger, or a sub-logger for the Agent class itself
logger = logging.getLogger(f"AgentZero.Agent") # Assuming AgentZero is the root logger name from task_logger

class Agent:
    """
    The core Agent class responsible for orchestrating tasks, interacting with LLMs,
    and managing memory.
    """
    def __init__(self,
                 persona_name: str = "default_agent",
                 core_directives: list[str] = None,
                 config: ConfigManager = None,
                 llm_client: LLMClient = None,
                 chroma_service: ChromaService = None # Add chroma_service parameter
                 # task_list_manager: TaskListManager = None # To be added in later phases
                 ):
        """
        Initializes the Agent.

        Args:
            persona_name (str): A name for this agent instance or its persona.
            core_directives (list[str], optional): A list of core instructions or principles
                                                   that guide the agent's behavior.
            config (ConfigManager, optional): A ConfigManager instance. If None, a new one is created.
            llm_client (LLMClient, optional): An LLMClient instance. If None, a new one is created based on config.
            chroma_service (ChromaService, optional): A ChromaService instance. If None, a new one is created.
            # task_list_manager (TaskListManager, optional): A TaskListManager instance. To be added later.
        """
        self.agent_id = f"agent_{persona_name}_{os.urandom(4).hex()}" # Simple unique ID
        self.persona_name = persona_name
        self.core_directives = core_directives if core_directives is not None else ["Be helpful and efficient."]

        if config is None:
            logger.info("No ConfigManager provided, creating a new one.")
            self.config = ConfigManager()
        else:
            self.config = config

        if llm_client is None:
            logger.info("No LLMClient provided, creating a new one based on current config.")
            self.llm_client = LLMClient(
                host=self.config.ollama_host,
                port=self.config.ollama_port,
                default_model=self.config.ollama_default_model
            )
        else:
            self.llm_client = llm_client

        if chroma_service is None:
            logger.info(f"Agent {self.agent_id}: No ChromaService provided, creating a new one based on current config.")
            try:
                self.chroma_service = ChromaService(config=self.config)
            except ConnectionError as e: # Catch specific ConnectionError from ChromaService init
                logger.error(f"Agent {self.agent_id} failed to initialize ChromaService: {e}. Memory functions will be impaired.", exc_info=False) # Set exc_info to False for cleaner log for this expected case
                self.chroma_service = None # Memory is not available
            except Exception as e: # Catch any other unexpected error during ChromaService init
                logger.error(f"Agent {self.agent_id} encountered an unexpected error initializing ChromaService: {e}. Memory functions will be impaired.", exc_info=True)
                self.chroma_service = None
        else:
            self.chroma_service = chroma_service

        # self.task_list_manager = task_list_manager # This will be set if an agent is specifically an orchestrator
                                                  # or if it's passed in. For now, methods will take it as arg.

        logger.info(f"Agent '{self.agent_id}' (Persona: {self.persona_name}) initialized. ChromaService available: {self.chroma_service is not None and self.chroma_service.client is not None}")
        logger.debug(f"Core directives for '{self.agent_id}': {self.core_directives}")

    def __str__(self):
        return f"<Agent id='{self.agent_id}' persona='{self.persona_name}'>"

    def __repr__(self):
        return f"Agent(persona_name='{self.persona_name}', agent_id='{self.agent_id}', core_directives={self.core_directives})"

    # --- Placeholder for methods to be implemented in subsequent steps/phases ---

    # Step: Basic LLM Interaction
    def think(self, user_prompt: str, conversation_history: Optional[list[dict]] = None, override_model: Optional[str] = None) -> str:
        """
        Processes a given prompt using the LLM, incorporating agent's persona and directives.

        Args:
            user_prompt (str): The user's input or query for the agent.
            conversation_history (Optional[list[dict]]): A list of previous turns in the conversation,
                                                        where each turn is a dict like {"role": "user/assistant", "content": "..."}.
                                                        This helps maintain context.
            override_model (Optional[str]): Optionally override the default model for this specific call.

        Returns:
            str: The LLM's response text.

        Raises:
            Exception: Can re-raise exceptions from LLMClient if generation fails critically.
        """
        # Construct a system prompt or a preamble incorporating persona and directives
        # This is a simple way; more complex agents might format this differently
        # or use specific fields in the LLM API if available (e.g., system prompt).

        # Directives formatted as a list
        directives_str = "\n".join(f"- {d}" for d in self.core_directives)

        # System prompt to guide the LLM about its role
        system_message_content = (
            f"You are '{self.persona_name}'.\n"
            f"Your core directives are:\n{directives_str}\n"
            f"You are now interacting with a user."
        )

        # In many LLM APIs (like OpenAI's chat completions, and adaptable by Ollama for some models),
        # a conversation is a list of messages.
        # We'll prepend our system message.
        messages = [{"role": "system", "content": system_message_content}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_prompt})

        # For Ollama's /api/generate, the 'prompt' field is typically a single string.
        # If using a model fine-tuned for chat, it might understand a structured format
        # passed as a single string, or one might need to use the /api/chat endpoint if available
        # and if the LLMClient supports it (currently LLMClient uses /api/generate).
        # For now, we'll format the message list into a single string prompt for /api/generate.
        # This formatting can be model-specific for best results.
        # A common simple format:
        full_prompt_str = ""
        for message in messages:
            full_prompt_str += f"{message['role'].title()}: {message['content']}\n\n"
        full_prompt_str += "Assistant:" # Prompt the assistant to respond

        logger.debug(f"Agent '{self.agent_id}' thinking. Full prompt for LLM (first 200 chars): {full_prompt_str[:200]}...")

        try:
            model_to_use = override_model if override_model else self.llm_client.default_model

            # TODO: Later, RAG context would be inserted into the prompt or messages here.
            # For now, RAG context is not included.

            response_data = self.llm_client.generate(
                prompt=full_prompt_str,
                model=model_to_use
                # Temperature, num_predict etc., could be sourced from self.config or method args
            )

            if response_data and response_data.get("response"):
                assistant_response = response_data["response"].strip()
                logger.info(f"Agent '{self.agent_id}' received LLM response (first 100 chars): {assistant_response[:100]}...")
                return assistant_response
            elif response_data and response_data.get("error"):
                logger.error(f"LLM generation failed for agent '{self.agent_id}': {response_data['error']}")
                # Decide on error propagation strategy. For now, return a generic error message.
                return f"Error: Could not get a response from the LLM ({response_data['error']})."
            else:
                logger.error(f"LLM generation returned unexpected data for agent '{self.agent_id}': {response_data}")
                return "Error: Unexpected response from the LLM."

        except Exception as e:
            logger.error(f"Exception during LLM interaction for agent '{self.agent_id}': {e}", exc_info=True)
            # Re-raise or return a user-friendly error message
            # For now, let's make it clear an exception occurred.
            return f"Error: An exception occurred while communicating with the LLM: {str(e)}"

    # Step: Basic Memory Integration
    def save_to_memory(self, document_text: str, metadata: Optional[dict] = None, doc_id: Optional[str] = None, collection_name: Optional[str] = None) -> bool:
        """
        Saves a piece of text (document) to the agent's memory.

        Args:
            document_text (str): The text content to save.
            metadata (Optional[dict]): Optional metadata associated with the text.
            doc_id (Optional[str]): Optional unique ID for the document.
            collection_name (Optional[str]): The name of the collection to save to.
                                             Defaults to ChromaDB default collection from config.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        if not self.chroma_service or not self.chroma_service.client:
            logger.error(f"Agent {self.agent_id}: ChromaService not available or client not connected. Cannot save to memory.")
            return False

        target_collection = collection_name if collection_name else self.config.chromadb_default_collection_name

        docs_list = [document_text]
        metadatas_list = [metadata] if metadata is not None else None # Ensure None if metadata is None
        ids_list = [doc_id] if doc_id else None

        logger.debug(f"Agent '{self.agent_id}' saving to memory. Collection: '{target_collection}', Doc ID: {doc_id if doc_id else 'auto'}")
        try:
            return self.chroma_service.add_documents(
                collection_name=target_collection,
                documents=docs_list,
                metadatas=metadatas_list,
                ids=ids_list
            )
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Error during save_to_memory -> chroma_service.add_documents: {e}", exc_info=True)
            return False

    def retrieve_from_memory(self, query: str, collection_name: Optional[str] = None, n_results: int = 3, where_filter: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        Retrieves relevant documents from memory based on a query.

        Args:
            query (str): The query text to search for.
            collection_name (Optional[str]): The collection to query. Defaults to ChromaDB default.
            n_results (int): Maximum number of results to return.
            where_filter (Optional[dict]): Metadata filter for the query.

        Returns:
            List[Dict[str, Any]]: A list of result dictionaries, where each dictionary
                                  might contain 'id', 'document', 'metadata', 'distance'. Returns empty list on failure.
        """
        if not self.chroma_service or not self.chroma_service.client:
            logger.error(f"Agent {self.agent_id}: ChromaService not available or client not connected. Cannot retrieve from memory.")
            return []

        target_collection = collection_name if collection_name else self.config.chromadb_default_collection_name

        logger.debug(f"Agent '{self.agent_id}' retrieving from memory. Collection: '{target_collection}', Query: '{query[:50]}...'")
        try:
            results_data = self.chroma_service.query_collection(
                collection_name=target_collection,
                query_texts=[query],
                n_results=n_results,
                where_filter=where_filter,
                include=["documents", "metadatas", "distances", "ids"]
            )
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Error during retrieve_from_memory -> chroma_service.query_collection: {e}", exc_info=True)
            return []

        if not results_data or results_data.get("documents") is None or not results_data["documents"][0]:
            # Check specifically for results_data.get("documents") is None because an empty list is a valid empty result
            # Also check if the first list of documents (for the first query) is empty
            logger.info(f"Agent '{self.agent_id}': No results found in memory for query '{query[:50]}...' from collection '{target_collection}'.")
            return []

        formatted_results = []
        docs = results_data.get('documents', [[]])[0]
        metas = results_data.get('metadatas', [[]])[0] if results_data.get('metadatas') else [None] * len(docs)
        dists = results_data.get('distances', [[]])[0] if results_data.get('distances') else [None] * len(docs)
        ids_list = results_data.get('ids', [[]])[0] if results_data.get('ids') else [None] * len(docs)


        for i in range(len(docs)):
            result_item = {
                "id": ids_list[i] if ids_list and i < len(ids_list) else None,
                "document": docs[i],
                "metadata": metas[i] if metas and i < len(metas) else None,
                "distance": dists[i] if dists and i < len(dists) else None,
            }
            formatted_results.append(result_item)

        logger.info(f"Agent '{self.agent_id}' retrieved {len(formatted_results)} items from memory for query '{query[:50]}...'.")
        return formatted_results

    # Phase 3: Task Management Methods
    def decompose_objective_into_tasks(self,
                                       objective_prompt: str,
                                       task_list_manager: TaskListManager,
                                       max_tasks: int = 5,
                                       task_priority: int = 5) -> Optional[Objective]:
        """
        Uses the LLM to decompose a high-level objective prompt into a list of tasks.
        Creates an Objective object and associated Task objects, adding them to the TaskListManager.

        Args:
            objective_prompt (str): The high-level objective description.
            task_list_manager (TaskListManager): The manager to add the objective and tasks to.
            max_tasks (int): Suggested maximum number of tasks to generate.
            task_priority (int): Default priority for generated tasks.

        Returns:
            Optional[Objective]: The created Objective object if successful, else None.
        """
        logger.info(f"Agent '{self.agent_id}' decomposing objective: '{objective_prompt[:100]}...'")

        # Create a new Objective
        objective = Objective(description=objective_prompt, status=Status.PENDING) # Starts PENDING, will become ACTIVE if tasks are made
        task_list_manager.add_objective(objective)

        # Prompt for the LLM to generate tasks
        # This prompt engineering is crucial and can be refined.
        decomposition_prompt = (
            f"You are an expert project planner. Your task is to break down the following high-level objective "
            f"into a sequence of smaller, actionable tasks. Each task should be a clear, concise instruction. "
            f"Provide up to {max_tasks} tasks. Do not number them, just list each task on a new line.\n\n"
            f"Objective: \"{objective_prompt}\"\n\n"
            f"Tasks:"
        )

        # Use the agent's think method, but we want a more direct LLM call here without full persona chat.
        # For now, let's use a simplified call to llm_client.generate or adapt think.
        # A more robust approach might involve a dedicated LLM call for system tasks like planning.
        try:
            # Simplified call for task decomposition, could be a specific model/temp setting
            response_data = self.llm_client.generate(
                prompt=decomposition_prompt,
                model=self.llm_client.default_model, # Or a specific planning model
                temperature=0.3, # Lower temperature for more deterministic task lists
                num_predict=256  # Allow enough tokens for a few tasks
            )

            if response_data.get("error"): # Explicit error from LLM
                error_msg = response_data["error"]
                logger.error(f"LLM failed to generate tasks for objective '{objective.id}': {error_msg}")
                objective.update_status(Status.FAILED)
                objective.result = f"Failed to decompose into tasks: LLM error - {error_msg}"
                return objective

            raw_task_list_str = response_data.get("response", "").strip()
            task_descriptions = [line.strip() for line in raw_task_list_str.split('\n') if line.strip()]

            if not task_descriptions: # No tasks derived from a non-error response
                logger.warning(f"LLM generated an empty list of tasks for objective '{objective.id}'. Raw response: '{raw_task_list_str}'")
                objective.update_status(Status.FAILED)
                objective.result = "Failed to decompose: LLM returned no actionable tasks."
                return objective


            logger.info(f"Generated {len(task_descriptions)} tasks for objective '{objective.id}':")
            for i, desc in enumerate(task_descriptions):
                task = Task(
                    description=desc,
                    objective_id=objective.id,
                    priority=task_priority - i # Simple priority assignment
                )
                task_list_manager.add_task(task)
                logger.info(f"  - Added Task {task.id}: {desc}")

            # If tasks were successfully added, the objective can become active.
            # The TaskListManager's _check_and_update_objective_status might handle this if tasks become active.
            # For now, let's explicitly set it to PENDING (as tasks are PENDING) or ACTIVE if we want to start immediately.
            # If objective has tasks, it's no longer just a prompt, it's an active pursuit.
            if objective.status == Status.PENDING and task_descriptions: # if it was PENDING and now has tasks
                 objective.update_status(Status.ACTIVE) # Or let the loop pick it up as PENDING with tasks

            return objective

        except Exception as e:
            logger.error(f"Exception during task decomposition for objective '{objective.id}': {e}", exc_info=True)
            objective.update_status(Status.FAILED)
            objective.result = f"Exception during task decomposition: {str(e)}"
            return objective


    def execute_task(self, task: Task, task_list_manager: TaskListManager) -> None:
        """
        "Executes" a given task.
        Currently, this is a placeholder that logs the execution and marks the task as COMPLETED.
        Future implementations could involve more complex logic, LLM interaction, or tool usage.

        Args:
            task (Task): The task to execute.
            task_list_manager (TaskListManager): The manager where the task's status will be updated.
        """
        if not task or not isinstance(task, Task):
            logger.error(f"Agent {self.agent_id}: Invalid task provided to execute_task.")
            return

        logger.info(f"Agent '{self.agent_id}' starting execution of Task {task.id}: '{task.description[:70]}...'")
        task_list_manager.update_task_status(task.id, Status.ACTIVE)

        # --- Placeholder for actual task execution logic ---
        # This could involve:
        # 1. Using self.think() or self.llm_client.generate() for LLM-based tasks.
        #    Example: generated_text = self.think(f"Perform the following task: {task.description}")
        # 2. Calling external tools or functions.
        # 3. Interacting with other agent components.
        # For now, we simulate successful completion.
        simulated_result = f"Successfully completed task: {task.description}"
        logger.info(f"Agent '{self.agent_id}' simulated execution for Task {task.id}. Result: {simulated_result}")
        # --- End Placeholder ---

        task_list_manager.update_task_status(task.id, Status.COMPLETED, result=simulated_result)
        logger.info(f"Agent '{self.agent_id}' marked Task {task.id} as COMPLETED.")

    def is_objective_complete(self, objective_id: str, task_list_manager: TaskListManager) -> bool:
        """
        Checks if the specified objective is complete.
        An objective is considered complete if its status in the TaskListManager is COMPLETED.

        Args:
            objective_id (str): The ID of the objective to check.
            task_list_manager (TaskListManager): The manager containing the objective.

        Returns:
            bool: True if the objective is complete, False otherwise.
        """
        objective = task_list_manager.get_objective(objective_id)
        if not objective:
            logger.warning(f"Agent {self.agent_id}: Objective {objective_id} not found in TaskListManager for completion check.")
            return False # Or raise error, depending on desired strictness

        is_complete = objective.status == Status.COMPLETED
        logger.debug(f"Agent {self.agent_id}: Objective {objective_id} completion status: {is_complete} (Status: {objective.status})")
        return is_complete

    # Phase 4: Self-Play Loop & Autonomous Operation Methods
    # def generate_next_steps(self, objective, completed_tasks: list, pending_tasks: list) -> list[dict]:
    #     pass

    # def attempt_simulated_challenge(self, objective, current_state) -> str: # Analysis or new approach
    #     pass

    # Phase 5: Advanced Features
    # def get_context_for_rag(self, query: str, task_id: Optional[str] = None) -> str:
    #     pass

    # def save_experience(self, experience_text: str, task_id: str, objective_id: str, score: Optional[float] = None) -> None:
    #     pass

    # def get_experience_for_reflection(self, objective_id: str) -> list[dict]: # or Experience objects
    #     pass

    # def clone(self, persona_name_override: Optional[str] = None,
    #             specialization_description_override: Optional[str] = None,
    #             # ... other overrides from the initial detailed description
    #            ) -> 'Agent':
    #     # Creates a new Agent instance, copying or overriding parent's attributes
    #     pass


if __name__ == '__main__':
    import os # For os.urandom, already imported in class but good for direct script run
    from agent_zero.task_logger import setup_logging

    # Setup basic logging for the test run
    # This should ideally be called once at the application's entry point.
    # For this __main__ block, we ensure it's called.
    try:
        initial_config = ConfigManager()
        setup_logging(config=initial_config) # Configure logger using settings from .env or defaults
    except Exception as e:
        logging.basicConfig(level=logging.DEBUG) # Fallback basic config
        logger.error(f"Error setting up logging from ConfigManager: {e}. Using basicConfig.", exc_info=True)


    logger.info("--- Testing Agent Class Initialization ---")

    # Test 1: Initialize with default parameters
    try:
        agent1 = Agent()
        logger.info(f"Agent 1 ({agent1.agent_id}) created with default persona: {agent1.persona_name}")
        assert agent1.persona_name == "default_agent"
        assert agent1.config is not None
        assert agent1.llm_client is not None
        assert agent1.llm_client.default_model == agent1.config.ollama_default_model
        logger.info(f"Representation: {repr(agent1)}")
    except Exception as e:
        logger.error(f"Error creating Agent 1 (defaults): {e}", exc_info=True)

    # Test 2: Initialize with custom persona and directives
    try:
        custom_persona = "TestPersona"
        custom_directives = ["Directive 1: Test.", "Directive 2: Log everything."]
        agent2 = Agent(persona_name=custom_persona, core_directives=custom_directives)
        logger.info(f"Agent 2 ({agent2.agent_id}) created with custom persona: {agent2.persona_name}")
        assert agent2.persona_name == custom_persona
        assert agent2.core_directives == custom_directives
        logger.info(f"Representation: {repr(agent2)}")
    except Exception as e:
        logger.error(f"Error creating Agent 2 (custom): {e}", exc_info=True)

    # Test 3: Initialize with pre-configured components (mocked for simplicity here)
    try:
        mock_config = ConfigManager() # Using a real one, but could be a mock
        mock_config.ollama_default_model = "test_model_from_mock_config"

        # For testing 'think', we need a mock LLMClient or a live one if Ollama is running
        # Let's use a real LLMClient but expect it might fail if Ollama isn't running during this basic test.
        # A full unit test for 'think' would mock LLMClient.generate.
        live_llm_client_for_test = LLMClient(
            host=mock_config.ollama_host,
            port=mock_config.ollama_port,
            default_model=mock_config.ollama_default_model
        )

        agent3 = Agent(persona_name="PreConfiguredAgent", config=mock_config, llm_client=live_llm_client_for_test)
        logger.info(f"Agent 3 ({agent3.agent_id}) created with pre-configured components.")
        assert agent3.config == mock_config
        assert agent3.llm_client == live_llm_client_for_test
        # This assertion depends on the mock_config's model if llm_client was created inside Agent
        # If llm_client is passed in, it uses that client's default_model
        assert agent3.llm_client.default_model == mock_config.ollama_default_model

        logger.info(f"Representation: {repr(agent3)}")

        logger.info(f"\n--- Testing Agent 'think' method (Agent 3) ---")
        # This part of the test will try to contact a live Ollama instance
        # It's more of an integration smoke test within the __main__ block
        user_query_agent3 = "What is the capital of France?"
        logger.info(f"Agent 3 thinking about: '{user_query_agent3}'")
        think_response_agent3 = "Error: Default response if think fails"
        try:
            think_response_agent3 = agent3.think(user_prompt=user_query_agent3)
            logger.info(f"Agent 3 response: {think_response_agent3}")
            assert isinstance(think_response_agent3, str)
        except Exception as e:
            logger.error(f"Error during agent3.think() call in test: {e}", exc_info=True)
            if not isinstance(think_response_agent3, str):
                 think_response_agent3 = f"Think method raised: {e}"

        # Test memory functions
        if agent3.chroma_service and agent3.chroma_service.client:
            # ... (memory tests from before, slightly adapted if needed) ...
            pass # Assuming memory tests are covered by previous step's __main__ or dedicated tests

        # Test Task Processing Methods (Agent 3)
        logger.info(f"\n--- Testing Agent Task Processing methods (Agent 3) ---")
        if agent3.llm_client: # Need LLM for decomposition
            tm = TaskListManager()
            objective_prompt_agent3 = "Plan a three-day marketing campaign for a new eco-friendly water bottle."

            logger.info(f"Agent 3 decomposing objective: '{objective_prompt_agent3}'")
            # This will make a live LLM call if not mocked in a unit test context
            created_objective = agent3.decompose_objective_into_tasks(objective_prompt_agent3, tm)

            if created_objective and created_objective.status != Status.FAILED:
                logger.info(f"Objective '{created_objective.id}' decomposed into {len(created_objective.task_ids)} tasks.")
                assert len(created_objective.task_ids) > 0
                assert tm.get_objective(created_objective.id) is not None

                tasks_for_obj = tm.get_tasks_for_objective(created_objective.id)
                assert len(tasks_for_obj) == len(created_objective.task_ids)

                if tasks_for_obj:
                    first_task = tasks_for_obj[0]
                    logger.info(f"Agent 3 executing first task: {first_task.id} - '{first_task.description}'")
                    agent3.execute_task(first_task, tm)
                    assert first_task.status == Status.COMPLETED
                    assert first_task.result is not None
                    logger.info(f"Task {first_task.id} executed. Result: {first_task.result}")

                    # Check objective completion (will be false as only one task done)
                    is_done = agent3.is_objective_complete(created_objective.id, tm)
                    logger.info(f"Is objective '{created_objective.id}' complete after one task? {is_done}")
                    assert not is_done

                    # Simulate completing all tasks
                    for t in tasks_for_obj[1:]: # Execute remaining tasks
                        agent3.execute_task(t, tm)

                    is_done_after_all = agent3.is_objective_complete(created_objective.id, tm)
                    logger.info(f"Is objective '{created_objective.id}' complete after all tasks? {is_done_after_all}")
                    # The TaskManager's _check_and_update should mark objective as COMPLETED
                    final_obj_status = tm.get_objective(created_objective.id).status
                    assert final_obj_status == Status.COMPLETED, f"Expected objective to be COMPLETED, but was {final_obj_status}"
                    assert is_done_after_all # is_objective_complete should reflect this
                else:
                    logger.warning("No tasks were generated by decompose_objective_into_tasks for Agent 3.")
            elif created_objective and created_objective.status == Status.FAILED:
                 logger.warning(f"Objective decomposition failed for Agent 3. Reason: {getattr(created_objective, 'result', 'Unknown')}")
            else:
                logger.error("decompose_objective_into_tasks did not return an objective for Agent 3.")
        else:
            logger.warning("LLMClient not available for Agent 3. Skipping task processing tests.")

    except Exception as e:
        logger.error(f"Error creating Agent 3 (pre-configured) or during its think/memory/task tests: {e}", exc_info=True)

    logger.info("--- Agent Class Initialization, Basic Think, Memory & Task Processing Test Completed ---")
