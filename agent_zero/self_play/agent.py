# agent_zero/self_play/agent.py
import uuid
import ollama
from typing import List, Tuple, Optional, Dict, Any
from .models import Objective, Task, Status

# Default model lists (can be overridden in Agent constructor)
DEFAULT_CHAT_MODELS = ["mistral:7b-instruct-q5_K_M", "llama2:7b-chat-q5_K_M"]
DEFAULT_UTILITY_MODELS = ["orca-mini:3b-q4_K_M", "phi:2.7b-chat-q4_K_M", "nomic-embed-text:latest"]
# Fallback if preferred lists are empty or models fail
FALLBACK_MODEL = "orca-mini:3b-q4_K_M"

class Agent:
    def __init__(self,
                 agent_id: Optional[str] = None,
                 ollama_host='http://localhost:11434',
                 persona_name: str = "GenericAgent",
                 chat_models: Optional[List[str]] = None,
                 utility_models: Optional[List[str]] = None,
                 embedding_model: Optional[str] = None): # Specific for embeddings

        self.agent_id = agent_id if agent_id else str(uuid.uuid4())
        self.ollama_client = ollama.Client(host=ollama_host)
        self.persona_name = persona_name

        self.chat_models = chat_models if chat_models is not None else list(DEFAULT_CHAT_MODELS)
        self.utility_models = utility_models if utility_models is not None else list(DEFAULT_UTILITY_MODELS)
        self.embedding_model_name = embedding_model if embedding_model is not None else "nomic-embed-text:latest"

        self.primary_model = self.chat_models[0] if self.chat_models else FALLBACK_MODEL

        print(f"Agent {self.agent_id} ({self.persona_name}) initialized.")
        print(f"  Primary (Chat) Model: {self.primary_model}") # Note: self.primary_model is not actively used after this init
        print(f"  Available Chat Models: {self.chat_models}")
        print(f"  Available Utility Models: {self.utility_models}")
        print(f"  Embedding Model: {self.embedding_model_name}")


    def _get_model_from_list(self, model_list: List[str], requested_model: Optional[str] = None) -> str:
        if requested_model:
            # If a specific model is requested, we can check if it's in the preferred list,
            # but for now, we'll just use it directly. Future logic could validate against known/pulled models.
            return requested_model

        if model_list: # Return the first model in the preferred list for this category
            return model_list[0]

        print(f"Warning: Model list was empty for {self.persona_name}. Falling back to {FALLBACK_MODEL} for agent {self.agent_id}")
        return FALLBACK_MODEL

    def _llm_call(self,
                  prompt: str,
                  model_category: str = "chat", # "chat", "utility", or a specific model name
                  requested_model: Optional[str] = None) -> str:

        target_model_name = FALLBACK_MODEL # Default fallback

        if requested_model:
            target_model_name = requested_model
        elif model_category == "chat":
            target_model_name = self._get_model_from_list(self.chat_models)
        elif model_category == "utility":
            target_model_name = self._get_model_from_list(self.utility_models)
        elif model_category == "embedding":
            # This case should ideally not be hit by _llm_call; generate_embedding is preferred.
            print(f"Warning: _llm_call used for 'embedding' category with model {self.embedding_model_name}. This is not standard. Using chat mode for LLM call.")
            target_model_name = self._get_model_from_list(self.chat_models) # Fallback to a chat model
        else:
            # If model_category is not "chat", "utility", or "embedding", treat it as a specific model name.
            print(f"Treating model_category '{model_category}' as specific model name for {self.persona_name}.")
            target_model_name = model_category

        print(f"Agent {self.agent_id} ({self.persona_name}) using model '{target_model_name}' for prompt: '{prompt[:100]}...'")

        try:
            response = self.ollama_client.chat(
                model=target_model_name,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response['message']['content']
        except Exception as e:
            print(f"Error during LLM call for agent {self.agent_id} ({self.persona_name}) with model {target_model_name}: {e}")
            error_message = f"LLM call failed: {str(e)}."
            if hasattr(e, 'response') and e.response is not None:
                try:
                    ollama_error = e.response.json()
                    error_detail = ollama_error.get('error', str(e))
                    if "model not found" in error_detail.lower() or "models are not available" in error_detail.lower() or "pull model" in error_detail.lower():
                        error_message += f" The model '{target_model_name}' may not be pulled or available. Try `ollama pull {target_model_name}`."
                except ValueError: # If response is not JSON
                    pass
            return error_message

    def decompose_objective_into_tasks(self, objective: Objective, task_list_manager: Optional['TaskListManager'] = None) -> List[Task]:
        print(f"Agent {self.agent_id} ({self.persona_name}) decomposing objective (using 'chat' model category): {objective.description[:50]}...")
        prompt = f"Given the objective '{objective.description}', break it down into a short, numbered list of primary tasks. Each task should be a single concise sentence. Example: 1. First task. 2. Second task."
        response_text = self._llm_call(prompt, model_category="chat")
        new_tasks = []
        if "LLM call failed" in response_text or not response_text.strip():
            print(f"Agent {self.agent_id} ({self.persona_name}) failed to decompose objective or got empty response.")
            task_desc = f"Address the objective: {objective.description}"
            fallback_task = Task(description=task_desc, objective_id=objective.objective_id, priority=1, created_by_agent_id=self.agent_id)
            new_tasks.append(fallback_task)
            if task_list_manager: task_list_manager.add_task(fallback_task)
        else:
            for i, line_content in enumerate(response_text.split('\n')):
                line_content = line_content.strip()
                if not line_content: continue
                task_desc = line_content
                if '.' in line_content and line_content.index('.') < 3 :
                    potential_desc = line_content.split('.', 1)[1].strip()
                    if potential_desc: task_desc = potential_desc
                elif ')' in line_content and line_content.index(')') < 3:
                    potential_desc = line_content.split(')', 1)[1].strip()
                    if potential_desc: task_desc = potential_desc
                if task_desc:
                    task = Task(description=task_desc, objective_id=objective.objective_id, priority=i + 1, created_by_agent_id=self.agent_id)
                    new_tasks.append(task)
                    if task_list_manager: task_list_manager.add_task(task)
        if not new_tasks and not ("LLM call failed" in response_text):
             task_desc = f"Address the objective: {objective.description}"
             fallback_task = Task(description=task_desc, objective_id=objective.objective_id, priority=1, created_by_agent_id=self.agent_id)
             new_tasks.append(fallback_task)
             if task_list_manager: task_list_manager.add_task(fallback_task)
        print(f"Agent {self.agent_id} ({self.persona_name}) decomposed objective into {len(new_tasks)} tasks.")
        return new_tasks

    def execute_task(self, task: Task, objective: Objective, requested_model_for_execution: Optional[str] = None) -> Tuple[str, List[Task]]:
        # Default to 'chat' category for general task execution unless a specific model is requested.
        # More complex logic could determine category based on task.description.
        execution_model_category = "chat"
        model_to_use = requested_model_for_execution

        print(f"Agent {self.agent_id} ({self.persona_name}) executing task (using '{execution_model_category}' category, specific request: {model_to_use if model_to_use else 'None'}): {task.description[:50]}...")
        prompt = f"Execute the task: '{task.description}'. The overall objective is: '{objective.description}'. Provide a concise result or summary of the execution. If new, smaller, specific sub-tasks are identified as necessary *during* this execution, list them as a numbered list AFTER your result, starting with 'New sub-tasks:'. Example: Result: Completed the analysis. New sub-tasks: 1. Write report. 2. Archive data."

        response_text = self._llm_call(prompt, model_category=execution_model_category, requested_model=model_to_use)

        task_result = "Execution simulated. No specific result from LLM."
        new_sub_tasks = []
        if "LLM call failed" in response_text or not response_text.strip():
            task_result = "Execution failed or LLM call issue."
            task.status = Status.FAILED
        else:
            lines = response_text.split('\n')
            result_lines = []
            new_task_lines = []
            parsing_new_tasks = False
            for line_content in lines:
                stripped_line = line_content.strip()
                if stripped_line.lower().startswith("new sub-tasks:") or stripped_line.lower().startswith("new tasks:"):
                    parsing_new_tasks = True
                    potential_first_task = stripped_line.lower().split("new sub-tasks:",1)[1].strip() if stripped_line.lower().startswith("new sub-tasks:") else stripped_line.lower().split("new tasks:",1)[1].strip()
                    if potential_first_task: new_task_lines.append(potential_first_task)
                    continue
                if parsing_new_tasks:
                    new_task_lines.append(stripped_line)
                else:
                    result_lines.append(stripped_line)
            task_result = " ".join(result_lines).replace("Result:", "").strip()
            if not task_result: task_result = "Execution simulated, content parsed as new tasks or empty."
            for i, sub_task_desc_line in enumerate(new_task_lines):
                sub_task_desc_line = sub_task_desc_line.strip()
                if not sub_task_desc_line: continue
                task_desc = sub_task_desc_line
                if '.' in sub_task_desc_line and sub_task_desc_line.index('.') < 3 :
                    potential_desc = sub_task_desc_line.split('.', 1)[1].strip()
                    if potential_desc: task_desc = potential_desc
                elif ')' in sub_task_desc_line and sub_task_desc_line.index(')') < 3:
                    potential_desc = sub_task_desc_line.split(')', 1)[1].strip()
                    if potential_desc: task_desc = potential_desc
                if task_desc:
                    new_task_obj = Task(
                        description=f"(Sub-task of {task.task_id[:8]}): {task_desc}",
                        objective_id=task.objective_id,
                        priority=task.priority,
                        created_by_agent_id=self.agent_id,
                        dependencies=[task.task_id]
                    )
                    new_sub_tasks.append(new_task_obj)
            task.status = Status.COMPLETED
        print(f"Agent {self.agent_id} ({self.persona_name}) task execution result: {task_result[:50]}... Generated {len(new_sub_tasks)} new sub-tasks.")
        return task_result, new_sub_tasks

    def is_objective_complete(self, objective: Objective, task_list_manager: 'TaskListManager') -> bool:
        pending_tasks = [t for t in task_list_manager.get_all_tasks() if t.objective_id == objective.objective_id and t.status == Status.PENDING]
        if pending_tasks:
            print(f"Agent {self.agent_id} ({self.persona_name}) judges objective not complete: {len(pending_tasks)} tasks still pending.")
            return False
        completed_task_details = []
        for t in task_list_manager.get_all_tasks():
            if t.objective_id == objective.objective_id and t.status == Status.COMPLETED and t.result:
                completed_task_details.append(f"- Task: {t.description} (Result: {str(t.result)[:100]})")
        if not completed_task_details:
             print(f"Agent {self.agent_id} ({self.persona_name}) judges objective not complete: No completed tasks with results found to verify.")
             return False
        completed_summary = "\n".join(completed_task_details)
        prompt = f"Given the objective '{objective.description}' and the following completed tasks and their results:\n{completed_summary}\n\nIs the objective fully achieved? Answer with only YES or NO."
        # Using 'chat' category for this kind of reasoning task
        response_text = self._llm_call(prompt, model_category="chat")
        if "yes" in response_text.lower().strip():
            print(f"Agent {self.agent_id} ({self.persona_name}) judges objective {objective.objective_id} as complete via LLM.")
            return True
        print(f"Agent {self.agent_id} ({self.persona_name}) judges objective {objective.objective_id} as NOT YET complete based on LLM response: '{response_text}'")
        return False

    def generate_next_steps(self, objective: Objective, task_list_manager: 'TaskListManager') -> List[Task]:
        print(f"Agent {self.agent_id} ({self.persona_name}) generating next steps (using 'chat' model category) for objective: {objective.description[:50]}...")
        task_details = []
        for t in task_list_manager.get_all_tasks():
             if t.objective_id == objective.objective_id:
                status_info = f"(Status: {t.status.value}"
                if t.status == Status.COMPLETED and t.result:
                    status_info += f", Result: {str(t.result)[:100]}"
                status_info += ")"
                task_details.append(f"- Task: {t.description} {status_info}")
        tasks_summary = "\n".join(task_details)
        prompt = f"Objective: '{objective.description}'.\nSummary of current tasks:\n{tasks_summary}\n\nBased on this, what are the next specific, actionable tasks to achieve the objective? If the objective seems complete, say 'OBJECTIVE LOOKS COMPLETE'. Otherwise, list new tasks as a numbered list. Focus on what's missing or needs to be done next."
        # Using 'chat' category for this kind of planning/reasoning task
        response_text = self._llm_call(prompt, model_category="chat")
        new_tasks = []
        if "LLM call failed" in response_text or "OBJECTIVE LOOKS COMPLETE" in response_text.upper() or not response_text.strip():
            print(f"Agent {self.agent_id} ({self.persona_name}) LLM failed to generate next steps or indicated objective looks complete.")
            return new_tasks
        for i, line_content in enumerate(response_text.split('\n')):
            line_content = line_content.strip()
            if not line_content: continue
            task_desc = line_content
            if '.' in line_content and line_content.index('.') < 3 :
                potential_desc = line_content.split('.', 1)[1].strip()
                if potential_desc: task_desc = potential_desc
            elif ')' in line_content and line_content.index(')') < 3:
                potential_desc = line_content.split(')', 1)[1].strip()
                if potential_desc: task_desc = potential_desc
            if task_desc:
                highest_priority_task = task_list_manager.get_highest_priority_task()
                base_priority = highest_priority_task.priority if highest_priority_task else 0
                new_task_obj = Task(description=task_desc, objective_id=objective.objective_id, priority=base_priority + 1, created_by_agent_id=self.agent_id)
                new_tasks.append(new_task_obj)
        print(f"Agent {self.agent_id} ({self.persona_name}) generated {len(new_tasks)} new next-step tasks.")
        return new_tasks

    def generate_embedding(self, text_to_embed: str, requested_embedding_model: Optional[str] = None) -> Optional[List[float]]:
        """Generates embeddings for a given text using the specified embedding model."""
        embed_model_to_use = requested_embedding_model if requested_embedding_model else self.embedding_model_name

        # Ensure the model chosen is actually an embedding model, or warn if using a non-standard one.
        # This basic check assumes embedding model names might contain "embed"
        if "embed" not in embed_model_to_use.lower() and embed_model_to_use not in DEFAULT_UTILITY_MODELS and embed_model_to_use not in DEFAULT_CHAT_MODELS:
            print(f"Warning: Agent {self.agent_id} ({self.persona_name}) attempting to use potentially non-embedding model '{embed_model_to_use}' for embeddings.")

        print(f"Agent {self.agent_id} ({self.persona_name}) generating embedding using model '{embed_model_to_use}' for text: '{text_to_embed[:100]}...'")
        try:
            # Use ollama.embeddings for generating embeddings
            response = self.ollama_client.embeddings(model=embed_model_to_use, prompt=text_to_embed)
            # The structure of the response for ollama.embeddings is typically {"embedding": [0.1, 0.2, ...]}
            return response.get("embedding")
        except Exception as e:
            print(f"Error during embedding generation for agent {self.agent_id} with model {embed_model_to_use}: {e}")
            error_detail_str = str(e).lower()
            if "model not found" in error_detail_str or "pull model" in error_detail_str or "models are not available" in error_detail_str:
                 print(f"Embedding model '{embed_model_to_use}' may not be pulled or available. Try `ollama pull {embed_model_to_use}`.")
            return None

    def clone(self, agent_id_suffix: str = "clone", persona_name_override: Optional[str] = None,
              chat_models_override: Optional[List[str]] = None,
              utility_models_override: Optional[List[str]] = None,
              embedding_model_override: Optional[str] = None):
        cloned_agent_id = f"{self.agent_id}_{agent_id_suffix}"
        new_persona_name = persona_name_override if persona_name_override is not None else f"{self.persona_name}Clone"

        # Ensure that we pass lists, not None, to the new Agent constructor if overrides are None
        final_chat_models = chat_models_override if chat_models_override is not None else list(self.chat_models)
        final_utility_models = utility_models_override if utility_models_override is not None else list(self.utility_models)
        final_embedding_model = embedding_model_override if embedding_model_override is not None else self.embedding_model_name

        print(f"Agent {self.agent_id} ({self.persona_name}) cloning into Agent {cloned_agent_id} ({new_persona_name}).")
        return Agent(
            agent_id=cloned_agent_id,
            ollama_host=self.ollama_client.host,
            persona_name=new_persona_name,
            chat_models=final_chat_models,
            utility_models=final_utility_models,
            embedding_model=final_embedding_model
        )
