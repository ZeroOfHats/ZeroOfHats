# agent_zero/self_play/agent.py
import uuid
import ollama
from typing import List, Tuple, Optional, Dict, Any
from .models import Objective, Task, Status

class Agent:
    def __init__(self, agent_id: Optional[str] = None, ollama_host='http://localhost:11434', primary_model='orca-mini', persona_name: str = "GenericAgent"):
        self.agent_id = agent_id if agent_id else str(uuid.uuid4())
        self.ollama_client = ollama.Client(host=ollama_host)
        self.primary_model = primary_model
        self.persona_name = persona_name # Added persona_name
        print(f"Agent {self.agent_id} ({self.persona_name}) initialized with model {self.primary_model}.")

    def _llm_call(self, prompt: str, model: Optional[str] = None) -> str:
        """Generic LLM call wrapper."""
        target_model = model if model else self.primary_model
        # Incorporate persona into the system message or initial prompt if desired,
        # For now, just logging it. More advanced persona use would modify the actual prompt.
        print(f"Agent {self.agent_id} ({self.persona_name}) making LLM call to model {target_model} with prompt: '{prompt[:100]}...'")
        try:
            # For more advanced persona, you might adjust the system message in client.chat()
            # or prepend persona instructions to the user prompt.
            # system_prompt = f"You are {self.persona_name}. " # Example
            response = self.ollama_client.chat(
                model=target_model,
                # system=system_prompt, # If using system prompts with Ollama and model supports it
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response['message']['content']
        except Exception as e:
            print(f"Error during LLM call for agent {self.agent_id} ({self.persona_name}) with model {target_model}: {e}")
            error_message = f"LLM call failed: {str(e)}."
            if hasattr(e, 'response') and e.response is not None:
                try:
                    ollama_error = e.response.json()
                    error_detail = ollama_error.get('error', str(e))
                    if "model not found" in error_detail.lower() or "models are not available" in error_detail.lower():
                        error_message += f" The model '{target_model}' may not be pulled. Try `ollama pull {target_model}`."
                except ValueError:
                    pass
            return error_message

    def decompose_objective_into_tasks(self, objective: Objective, task_list_manager: Optional['TaskListManager'] = None) -> List[Task]:
        """
        Decomposes the objective into initial tasks using an LLM call.
        """
        print(f"Agent {self.agent_id} ({self.persona_name}) decomposing objective: {objective.description[:50]}...")
        prompt = f"Given the objective '{objective.description}', break it down into a short, numbered list of primary tasks. Each task should be a single concise sentence. Example: 1. First task. 2. Second task."
        response_text = self._llm_call(prompt)

        new_tasks = []
        if "LLM call failed" in response_text or not response_text.strip():
            print(f"Agent {self.agent_id} ({self.persona_name}) failed to decompose objective or got empty response.")
            # Create a generic fallback task
            task_desc = f"Address the objective: {objective.description}"
            fallback_task = Task(description=task_desc, objective_id=objective.objective_id, priority=1, created_by_agent_id=self.agent_id)
            new_tasks.append(fallback_task)
            if task_list_manager: task_list_manager.add_task(fallback_task)
        else:
            # Simple parsing: assumes numbered list
            for i, line_content in enumerate(response_text.split('\n')):
                line_content = line_content.strip()
                if not line_content: continue
                # Remove leading numbers like "1. ", "1) "
                task_desc = line_content
                if '.' in line_content and line_content.index('.') < 3 : # Check if a dot is near the beginning
                    potential_desc = line_content.split('.', 1)[1].strip()
                    if potential_desc: task_desc = potential_desc
                elif ')' in line_content and line_content.index(')') < 3: # Check if a parenthesis is near the beginning
                    potential_desc = line_content.split(')', 1)[1].strip()
                    if potential_desc: task_desc = potential_desc

                if task_desc:
                    task = Task(description=task_desc, objective_id=objective.objective_id, priority=i + 1, created_by_agent_id=self.agent_id)
                    new_tasks.append(task)
                    if task_list_manager: task_list_manager.add_task(task)

        if not new_tasks and not ("LLM call failed" in response_text): # If parsing failed but LLM call was okay
             task_desc = f"Address the objective: {objective.description}"
             fallback_task = Task(description=task_desc, objective_id=objective.objective_id, priority=1, created_by_agent_id=self.agent_id)
             new_tasks.append(fallback_task)
             if task_list_manager: task_list_manager.add_task(fallback_task)

        print(f"Agent {self.agent_id} ({self.persona_name}) decomposed objective into {len(new_tasks)} tasks.")
        return new_tasks

    def execute_task(self, task: Task, objective: Objective) -> Tuple[str, List[Task]]:
        """
        Executes a task. Returns result and any new tasks generated.
        """
        print(f"Agent {self.agent_id} ({self.persona_name}) executing task: {task.description[:50]}...")
        prompt = f"Execute the task: '{task.description}'. The overall objective is: '{objective.description}'. Provide a concise result or summary of the execution. If new, smaller, specific sub-tasks are identified as necessary *during* this execution, list them as a numbered list AFTER your result, starting with 'New sub-tasks:'. Example: Result: Completed the analysis. New sub-tasks: 1. Write report. 2. Archive data."

        response_text = self._llm_call(prompt)

        task_result = "Execution simulated. No specific result from LLM."
        new_sub_tasks = []

        if "LLM call failed" in response_text or not response_text.strip():
            task_result = "Execution failed or LLM call issue."
            task.status = Status.FAILED
        else:
            # Try to parse result and new tasks
            lines = response_text.split('\n')
            result_lines = []
            new_task_lines = []
            parsing_new_tasks = False

            for line_content in lines:
                stripped_line = line_content.strip()
                if stripped_line.lower().startswith("new sub-tasks:") or stripped_line.lower().startswith("new tasks:"):
                    parsing_new_tasks = True
                    # Capture text after "New sub-tasks:" if on the same line
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
                    new_task = Task(
                        description=f"(Sub-task of {task.task_id[:8]}): {task_desc}",
                        objective_id=task.objective_id,
                        priority=task.priority, # Inherit priority, or adjust
                        created_by_agent_id=self.agent_id,
                        dependencies=[task.task_id] # Depends on parent task
                    )
                    new_sub_tasks.append(new_task)
            task.status = Status.COMPLETED

        print(f"Agent {self.agent_id} ({self.persona_name}) task execution result: {task_result[:50]}... Generated {len(new_sub_tasks)} new sub-tasks.")
        return task_result, new_sub_tasks

    def is_objective_complete(self, objective: Objective, task_list_manager: 'TaskListManager') -> bool:
        """
        Checks if the objective is complete.
        """
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
        response_text = self._llm_call(prompt)

        if "yes" in response_text.lower().strip():
            print(f"Agent {self.agent_id} ({self.persona_name}) judges objective {objective.objective_id} as complete via LLM.")
            return True

        print(f"Agent {self.agent_id} ({self.persona_name}) judges objective {objective.objective_id} as NOT YET complete based on LLM response: '{response_text}'")
        return False

    def generate_next_steps(self, objective: Objective, task_list_manager: 'TaskListManager') -> List[Task]:
        """
        If objective is not complete and task list is empty, generate new tasks.
        """
        print(f"Agent {self.agent_id} ({self.persona_name}) generating next steps for objective: {objective.description[:50]}...")

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
        response_text = self._llm_call(prompt)

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
                task = Task(description=task_desc, objective_id=objective.objective_id, priority=base_priority + 1, created_by_agent_id=self.agent_id)
                new_tasks.append(task)

        print(f"Agent {self.agent_id} ({self.persona_name}) generated {len(new_tasks)} new next-step tasks.")
        return new_tasks

    def clone(self, agent_id_suffix: str = "clone", persona_name_override: Optional[str] = None, primary_model_override: Optional[str] = None):
        """
        Clones the agent.
        Allows overriding persona_name and primary_model for the clone.
        """
        cloned_agent_id = f"{self.agent_id}_{agent_id_suffix}"
        new_persona_name = persona_name_override if persona_name_override else f"{self.persona_name}Clone"
        new_primary_model = primary_model_override if primary_model_override else self.primary_model

        print(f"Agent {self.agent_id} ({self.persona_name}) cloning into Agent {cloned_agent_id} ({new_persona_name}) with model {new_primary_model}.")
        return Agent(
            agent_id=cloned_agent_id,
            ollama_host=self.ollama_client.host,
            primary_model=new_primary_model,
            persona_name=new_persona_name
        )
