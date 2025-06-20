# agent_zero/self_play/agent.py
import uuid
import ollama
from typing import List, Tuple, Optional, Dict, Any
import re
import time
from enum import Enum
import datetime

from .models import Objective, Task, Status
from ..tools.web_scraper import get_text_from_url
from ..utils.text_processing import split_text_into_chunks
from ..memory.chroma_service import ChromaService

DEFAULT_CHAT_MODELS = ["mistral:7b-instruct-q5_K_M", "llama2:7b-chat-q5_K_M"]
DEFAULT_UTILITY_MODELS = ["tinydolphin:1.1b-q4_K_M", "orca-mini:3b-q4_K_M", "phi:2.7b-chat-q4_K_M"]
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text:latest"
FALLBACK_MODEL = "orca-mini:3b-q4_K_M"
EXPERIENCE_MEMORY_COLLECTION = "agent_experience_memory"

class AgentState(Enum): IDLE="idle"; TASKED="tasked"; SELF_IMPROVING="self_improving"; SUSPENDED="suspended"

class Agent:
    def __init__(self,
                 agent_id: Optional[str] = None,
                 ollama_host: str = 'http://localhost:11434',
                 persona_name: str = "Orchestrator",
                 chat_models: Optional[List[str]] = None,
                 utility_models: Optional[List[str]] = None,
                 embedding_model: Optional[str] = None,
                 chroma_service_path: str = "/agent_data/chroma",
                 specialization_description: Optional[str] = "A general-purpose AI assistant.",
                 core_directives: Optional[List[str]] = None,
                 dedicated_chroma_collection_name: Optional[str] = None,
                 # New RAG/Experience parameters
                 rag_results_count: int = 3,
                 rag_max_context_length: int = 2500, # Adjusted default
                 experience_results_count: int = 2,
                 experience_max_context_length: int = 1200 # Adjusted default
                ):

        self.agent_id = agent_id if agent_id else str(uuid.uuid4())
        self.ollama_client = ollama.Client(host=ollama_host)
        self.persona_name = persona_name

        self.chat_models = chat_models if chat_models is not None else list(DEFAULT_CHAT_MODELS)
        self.utility_models = utility_models if utility_models is not None else list(DEFAULT_UTILITY_MODELS)
        self.embedding_model_name = embedding_model if embedding_model is not None else DEFAULT_EMBEDDING_MODEL
        self.primary_model = self.chat_models[0] if self.chat_models else FALLBACK_MODEL

        self.specialization_description = specialization_description if specialization_description else "A general-purpose AI assistant."
        self.core_directives = core_directives if core_directives else ["Be helpful and efficient."]

        self.chroma_service_path = chroma_service_path
        self.default_memory_collection = dedicated_chroma_collection_name if dedicated_chroma_collection_name else f"agent_{self.agent_id}_memory"

        self.current_state: AgentState = AgentState.IDLE

        # Store RAG/Experience parameters
        self.rag_results_count = rag_results_count
        self.rag_max_context_length = rag_max_context_length
        self.experience_results_count = experience_results_count
        self.experience_max_context_length = experience_max_context_length

        print(f"Agent {self.agent_id} ({self.persona_name}) initializing...")
        # print(f"  Default Chat Model (Primary Fallback): {self.primary_model}") # Verbose
        # print(f"  Available Chat Models: {self.chat_models}")
        # print(f"  Available Utility Models: {self.utility_models}")
        # print(f"  Embedding Model: {self.embedding_model_name}")
        # print(f"  Specialization: {self.specialization_description[:100]}...") # Verbose
        # print(f"  Core Directives: {self.core_directives[:2]}...") # Verbose
        # print(f"  RAG Settings: Results={self.rag_results_count}, MaxContextLen={self.rag_max_context_length}") # Verbose
        # print(f"  Experience Settings: Results={self.experience_results_count}, MaxExpLen={self.experience_max_context_length}") # Verbose


        try:
            self.chroma_service = ChromaService(path=self.chroma_service_path)
            self.chroma_service.get_or_create_collection(self.default_memory_collection)
            self.chroma_service.get_or_create_collection(EXPERIENCE_MEMORY_COLLECTION)
            # print(f"Agent {self.agent_id} ({self.persona_name}) connected to ChromaDB. Default Mem: '{self.default_memory_collection}', Exp. Mem: '{EXPERIENCE_MEMORY_COLLECTION}'.") # Verbose
        except Exception as e:
            print(f"CRITICAL: Agent {self.agent_id} ({self.persona_name}) failed to initialize ChromaService at {self.chroma_service_path}: {e}")
            self.chroma_service = None
        print(f"Agent {self.agent_id} ('{self.persona_name}') initialized with state {self.current_state.value}.")

    def _get_model_from_list(self, model_list: List[str], requested_model: Optional[str]=None) -> str:
        if requested_model: return requested_model
        if model_list: return model_list[0]
        print(f"Warning: Model list empty for {self.persona_name}. Falling back to {FALLBACK_MODEL}"); return FALLBACK_MODEL

    def _llm_call(self, prompt: str, model_category: str="chat", requested_model: Optional[str]=None) -> str:
        target_model_name = FALLBACK_MODEL
        if requested_model: target_model_name = requested_model
        elif model_category == "chat": target_model_name = self._get_model_from_list(self.chat_models)
        elif model_category == "utility": target_model_name = self._get_model_from_list(self.utility_models)
        elif model_category != "embedding": target_model_name = model_category
        else: target_model_name = self._get_model_from_list(self.chat_models)
        system_message_parts = [f"You are an AI assistant: '{self.persona_name}'.", f"Specialization: {self.specialization_description}"]
        if self.core_directives: system_message_parts.append("Core Directives:"); system_message_parts.extend(f"{i+1}. {d}" for i,d in enumerate(self.core_directives))
        system_message_content = "\n".join(system_message_parts)
        # print(f"Agent {self.agent_id} ({self.persona_name}) model '{target_model_name}'. System: '{system_message_content[:100]}...'. User: '{prompt[:100]}...'") # Verbose
        try:
            response = self.ollama_client.chat(model=target_model_name, messages=[{'role': 'system', 'content': system_message_content},{'role': 'user', 'content': prompt}])
            return response['message']['content']
        except Exception as e: print(f"Error LLM call ({target_model_name}): {e}"); return f"LLM call failed: {e}"

    def generate_embedding(self, text_to_embed: str, requested_embedding_model: Optional[str] = None) -> Optional[List[float]]:
        embed_model_to_use = requested_embedding_model if requested_embedding_model else self.embedding_model_name
        try: response = self.ollama_client.embeddings(model=embed_model_to_use, prompt=text_to_embed); return response.get("embedding")
        except Exception as e: print(f"Error embedding generation ({embed_model_to_use}): {e}"); return None

    def process_and_store_text_in_memory(self, text_content: str, source_metadata: Dict[str, Any], collection_name: Optional[str] = None, chunk_strategy: str = "paragraph", chunk_size: int = 500, chunk_overlap: int = 50) -> Tuple[int, int]:
        if not self.chroma_service: return 0,0
        if not text_content: return 0,0
        target_collection = collection_name if collection_name else self.default_memory_collection
        chunks = split_text_into_chunks(text_content, chunk_size=chunk_size, chunk_overlap=chunk_overlap, strategy=chunk_strategy)
        if not chunks: return 0,0
        embeddings_to_store: List[List[float]] = []; documents_to_store: List[str] = []; metadatas_to_store: List[Dict[str, Any]] = []; ids_to_store: List[str] = []
        processed_chunks_count = 0
        for i, chunk_text in enumerate(chunks):
            processed_chunks_count += 1; embedding = self.generate_embedding(chunk_text)
            if embedding:
                embeddings_to_store.append(embedding); documents_to_store.append(chunk_text)
                chunk_metadata = source_metadata.copy(); chunk_metadata['chunk_index'] = i; metadatas_to_store.append(chunk_metadata)
                raw_id_part = f"{source_metadata.get('task_id', 'unk_task')}_{source_metadata.get('url', 'unk_src')[:50]}_chunk{i}"
                sanitized_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', raw_id_part); sanitized_id = re.sub(r'_{2,}', '_', sanitized_id); sanitized_id = re.sub(r'\.{2,}', '.', sanitized_id);
                if sanitized_id.startswith('.'): sanitized_id = '_' + sanitized_id[1:];
                if sanitized_id.endswith('.'): sanitized_id = sanitized_id[:-1] + '_';
                if len(sanitized_id) > 63: sanitized_id = sanitized_id[:63];
                if not sanitized_id : sanitized_id = f"default_id_{uuid.uuid4().hex[:8]}"
                ids_to_store.append(sanitized_id)
        if not documents_to_store: return processed_chunks_count, 0
        success = self.chroma_service.add_documents(collection_name=target_collection, documents=documents_to_store, embeddings=embeddings_to_store, metadatas=metadatas_to_store, ids=ids_to_store)
        return processed_chunks_count, (len(documents_to_store) if success else 0)

    def retrieve_relevant_info_from_memory(self, query_text: str, collection_name: Optional[str]=None, n_results: int=3, where_filter: Optional[Dict[str, Any]]=None) -> List[str]:
        if not self.chroma_service or not query_text: return []
        target_collection = collection_name if collection_name else self.default_memory_collection
        query_embedding = self.generate_embedding(query_text)
        if not query_embedding: return []
        query_results = self.chroma_service.query_collection(collection_name=target_collection, query_embeddings=[query_embedding], n_results=n_results, where_filter=where_filter, include_fields=["documents"])
        if query_results and query_results.get('documents') and query_results['documents'][0]: return [d for d in query_results['documents'][0] if d is not None]
        return []

    def _augment_prompt_with_rag_context(self, original_prompt: str, query_for_rag: str) -> str:
        if not self.chroma_service: return original_prompt
        rag_collection_to_query = self.default_memory_collection
        retrieved_chunks = self.retrieve_relevant_info_from_memory(query_text=query_for_rag, collection_name=rag_collection_to_query, n_results=self.rag_results_count)
        if not retrieved_chunks: return original_prompt
        context_str = "\n\n---\n\n".join(retrieved_chunks)
        if len(context_str) > self.rag_max_context_length: context_str = context_str[:self.rag_max_context_length] + "... (truncated)"
        return (f"Context from memory ('{rag_collection_to_query}'):\n--- START ---\n{context_str}\n--- END ---\n\nRespond to:\n{original_prompt}")

    def _augment_prompt_with_experience_context(self, original_prompt: str, query_for_experience: str) -> str:
        if not self.chroma_service: return original_prompt
        retrieved_experiences = self.retrieve_relevant_info_from_memory(query_text=query_for_experience,collection_name=EXPERIENCE_MEMORY_COLLECTION, n_results=self.experience_results_count)
        if not retrieved_experiences: return original_prompt
        experience_str = "\n\n---\n\n".join(retrieved_experiences)
        if len(experience_str) > self.experience_max_context_length: experience_str = experience_str[:self.experience_max_context_length] + "... (truncated)"
        # print(f"Agent {self.agent_id} ({self.persona_name}): Augmenting prompt with {len(retrieved_experiences)} past experience(s).") # Verbose
        return (f"Past experiences/reflections:\n--- START ---\n{experience_str}\n--- END ---\n\nInformed by these, address:\n{original_prompt}")

    def reflect_and_learn_from_task(self, completed_task: Task) -> Optional[str]:
        if not self.chroma_service: print(f"Agent {self.agent_id}: Chroma unavailable for reflection."); return None
        if completed_task.status not in [Status.COMPLETED, Status.FAILED] or not completed_task.result: print(f"Agent {self.agent_id}: Task {completed_task.task_id} not ended or no result. No reflection."); return None

        original_state = self.current_state # Store state
        self.current_state = AgentState.SELF_IMPROVING
        print(f"Agent {self.agent_id} ({self.persona_name}): State: {self.current_state.value}. Reflecting on task '{completed_task.description[:50]}...'")

        reflection_persona_prompt = f"You are '{self.persona_name}'. Specialization: {self.specialization_description}. "
        if self.persona_name == "Critic" or "Critic" in self.persona_name : reflection_persona_prompt = "You are a 'Critic' agent evaluating a completed task. Identify strengths, weaknesses, improvements. Be constructive."
        prompt = (f"{reflection_persona_prompt}\n\nTask: \"{completed_task.description}\"\nStatus: {completed_task.status.value}\nResult: \"{str(completed_task.result)[:1000]}\"\n\nReflection points: 1. Outcome quality? Success? 2. Key factors? 3. Insights gained? 4. Future improvements? 5. Unexpected challenges/learnings? Structured text.")
        reflection_text = self._llm_call(prompt, model_category="chat")

        if "LLM call failed" in reflection_text or not reflection_text.strip():
            print(f"Agent {self.agent_id}: Failed reflection generation for task {completed_task.task_id}.")
            self.current_state = original_state; return None # Restore state

        reflection_embedding = self.generate_embedding(reflection_text)
        if not reflection_embedding:
            print(f"Agent {self.agent_id}: Failed reflection embedding. Cannot store.");
            self.current_state = original_state; return reflection_text

        reflection_metadata = {"source_type": "task_reflection", "original_task_id": completed_task.task_id, "original_task_description": completed_task.description[:250], "original_task_status": completed_task.status.value, "original_task_result_snippet": str(completed_task.result)[:250], "reflecting_agent_id": self.agent_id, "reflecting_agent_persona": self.persona_name, "reflection_timestamp": datetime.datetime.utcnow().isoformat(), "objective_id": completed_task.objective_id}
        reflection_id = f"refl_{completed_task.task_id}_{uuid.uuid4().hex[:8]}"
        success = self.chroma_service.add_documents(collection_name=EXPERIENCE_MEMORY_COLLECTION, documents=[reflection_text], embeddings=[reflection_embedding], metadatas=[reflection_metadata], ids=[reflection_id])
        # print(f"Agent {self.agent_id}: Stored reflection (Success: {success}).") # Verbose

        self.current_state = original_state # Restore state
        print(f"Agent {self.agent_id} ({self.persona_name}): State restored to {self.current_state.value} after reflection.")
        return reflection_text

    def attempt_simulated_challenge(self) -> Optional[str]:
        original_state = self.current_state
        self.current_state = AgentState.SELF_IMPROVING
        print(f"Agent {self.agent_id} ({self.persona_name}): State: {self.current_state.value}. Attempting simulated challenge.")

        challenge_generation_prompt = (f"You are '{self.persona_name}' ({self.specialization_description}). Generate a single, specific, concise hypothetical question or micro-problem relevant to your persona/specialization for self-testing. Example: 'What are three key differences between X and Y?' or 'Outline a basic approach to Z.'")
        challenge_text = self._llm_call(challenge_generation_prompt, model_category="chat")
        if "LLM call failed" in challenge_text or not challenge_text.strip():
            print(f"Agent {self.agent_id}: Failed to generate simulated challenge."); self.current_state = original_state; return None

        print(f"Agent {self.agent_id}: Generated Challenge: '{challenge_text[:150]}...'")
        solution_base_prompt = f"Attempt to answer/solve self-generated challenge: '{challenge_text}'. Explain reasoning and provide a clear solution."
        prompt_with_rag = self._augment_prompt_with_rag_context(original_prompt=solution_base_prompt, query_for_rag=challenge_text)
        final_solution_prompt = self._augment_prompt_with_experience_context(original_prompt=prompt_with_rag, query_for_experience=challenge_text)
        solution_text = self._llm_call(final_solution_prompt, model_category="chat")
        challenge_status = Status.COMPLETED if "LLM call failed" not in solution_text else Status.FAILED
        if "LLM call failed" in solution_text: solution_text = "Attempted challenge, but LLM call failed during solution."

        print(f"Agent {self.agent_id}: Solution/Attempt: '{solution_text[:150]}...'")
        simulated_task = Task(task_id=f"sim_chal_{uuid.uuid4().hex[:12]}", objective_id="self_improvement_objective", description=f"Self-Generated Challenge: {challenge_text}", status=challenge_status, result=solution_text, created_by_agent_id=self.agent_id)
        reflection_outcome = self.reflect_and_learn_from_task(simulated_task) # This method now handles its own state changes for reflection

        summary_report = (f"Simulated Challenge by {self.agent_id} ({self.persona_name}):\nChallenge: {challenge_text}\nOutcome: {solution_text[:200]}...\nReflection Stored: {'Yes' if reflection_outcome else 'No'}")
        self.current_state = original_state # Restore state from before challenge attempt
        print(f"Agent {self.agent_id} ({self.persona_name}): State restored to {self.current_state.value} after simulated challenge cycle.")
        return summary_report

    def execute_task(self, task: Task, objective: Objective, requested_model_for_execution: Optional[str] = None) -> Tuple[str, List[Task]]:
        # ... (Copied, ensure latest version with RAG and Experience augmentation) ...
        task_description_lower = task.description.lower()
        if task_description_lower.startswith("scrape ") or task_description_lower.startswith("fetch website ") or task_description_lower.startswith("get content of url "):
            try: # ... (Full scraping logic from previous step)
                parts = task.description.split(" ", 1); url = parts[1].strip() if len(parts) >= 2 and parts[1].strip() else (_ for _ in ()).throw(ValueError("URL missing")) # type: ignore
                if not (url.startswith("http://") or url.startswith("https://")): url = "http://" + url
                scraped_content = self.scrape_website(url)
                if scraped_content:
                    source_meta = {'url': url, 'task_id': task.task_id, 'objective_id': objective.objective_id, 'source_type': 'web_scrape', 'scraped_timestamp': time.time()}
                    processed, stored = self.process_and_store_text_in_memory(scraped_content, source_meta)
                    storage_report = f"Processed {processed} chunks. Stored {stored} in '{self.default_memory_collection}'."
                    summary_prompt = f"Summarize scraped text from {url} (max 2-3 sentences):\n{scraped_content[:2000]}"
                    summary_result = self._llm_call(summary_prompt, model_category="utility")
                    final_result = f"Summary of {url}: {summary_result if 'LLM call failed' not in summary_result else 'Summarization failed'}. {storage_report}"
                    task.status = Status.COMPLETED; return final_result, []
                else: task.status = Status.FAILED; return f"Failed to scrape {url}.", []
            except Exception as e: task.status = Status.FAILED; return f"Scraping task error for '{task.description}': {e}", []
        execution_model_category = "chat"; model_to_use = requested_model_for_execution
        base_execution_prompt = (f"Execute the task: '{task.description}'. Overall objective: '{objective.description}'. Provide result/summary. If new sub-tasks arise, list them starting with 'New sub-tasks:'.")
        prompt_with_rag_context = self._augment_prompt_with_rag_context(original_prompt=base_execution_prompt, query_for_rag=task.description)
        final_execution_prompt = self._augment_prompt_with_experience_context(original_prompt=prompt_with_rag_context, query_for_experience=task.description)
        response_text = self._llm_call(final_execution_prompt, model_category=execution_model_category, requested_model=model_to_use)
        task_result = "Execution sim. No result."; new_sub_tasks = []
        if "LLM call failed" in response_text or not response_text.strip(): task_result = "Exec failed/LLM issue."; task.status = Status.FAILED
        else: # ... (Full parsing logic from previous step)
            lines = response_text.split('\n'); result_lines = []; new_task_lines = []; parsing_new_tasks = False
            for line_content in lines: stripped_line = line_content.strip();_ = stripped_line.lower().startswith(("new sub-tasks:", "new tasks:")) and (parsing_new_tasks := True) and (potential_first_task := stripped_line.lower().split("new sub-tasks:",1)[1].strip() if stripped_line.lower().startswith("new sub-tasks:") else stripped_line.lower().split("new tasks:",1)[1].strip()) and (_ = potential_first_task and new_task_lines.append(potential_first_task)) and (_ := next) # type: ignore
            _ = parsing_new_tasks and new_task_lines.append(stripped_line) or result_lines.append(stripped_line) # type: ignore
            task_result = " ".join(result_lines).replace("Result:", "").strip() or "Execution sim, content parsed as new tasks/empty."
            for i, sub_task_desc_line in enumerate(new_task_lines): sub_task_desc_line = sub_task_desc_line.strip(); task_desc = re.sub(r'^\s*[\d\W]+\s*', '', sub_task_desc_line) ;_ = not task_desc and (_ := next);_ = task_desc and new_sub_tasks.append(Task(description=f"(Sub of {task.task_id[:8]}): {task_desc}", objective_id=task.objective_id, priority=task.priority, created_by_agent_id=self.agent_id,dependencies=[task.task_id])) # type: ignore
            task.status = Status.COMPLETED
        return task_result, new_sub_tasks

    def decompose_objective_into_tasks(self, objective: Objective, task_list_manager: Optional['TaskListManager'] = None) -> List[Task]: # Copied
        base_prompt = (f"You are an '{self.persona_name}' agent. Decompose objective: '{objective.description}' into primary, actionable tasks (numbered list, 1 sentence each).")
        prompt_with_rag_context = self._augment_prompt_with_rag_context(original_prompt=base_prompt, query_for_rag=objective.description)
        final_prompt = self._augment_prompt_with_experience_context(original_prompt=prompt_with_rag_context, query_for_experience=objective.description)
        response_text = self._llm_call(final_prompt, model_category="chat")
        new_tasks = []; # ... (Full parsing logic from previous step)
        if "LLM call failed" in response_text or not response_text.strip(): task_desc = f"Critically review and address the objective: {objective.description}"; fallback_task = Task(description=task_desc, objective_id=objective.objective_id, priority=1, created_by_agent_id=self.agent_id); new_tasks.append(fallback_task);_ = task_list_manager and task_list_manager.add_task(fallback_task)
        else:
            for i, line_content in enumerate(response_text.split('\n')): line_content = line_content.strip(); task_desc = re.sub(r'^\s*[\d\W]+\s*', '', line_content);_ = not task_desc and (_ := next);_ = task_desc and (task_obj := Task(description=task_desc, objective_id=objective.objective_id, priority=i + 1, created_by_agent_id=self.agent_id)) and new_tasks.append(task_obj) and (_ = task_list_manager and task_list_manager.add_task(task_obj)) # type: ignore
        if not new_tasks and not ("LLM call failed" in response_text): task_desc = f"Critically review and address the objective: {objective.description}"; fallback_task = Task(description=task_desc, objective_id=objective.objective_id, priority=1, created_by_agent_id=self.agent_id); new_tasks.append(fallback_task);_ = task_list_manager and task_list_manager.add_task(fallback_task)
        return new_tasks

    def is_objective_complete(self, objective: Objective, task_list_manager: 'TaskListManager') -> bool: # Copied
        prompt_header = f"You are an '{self.persona_name}' agent assessing objective completion."
        pending_tasks = [t for t in task_list_manager.get_all_tasks() if t.objective_id == objective.objective_id and t.status == Status.PENDING];_ = pending_tasks and (_ := (_ for _ in ()).throw(StopIteration)) # type: ignore
        completed_task_details = [f"- Task: {t.description} (Result: {str(t.result)[:100]})" for t in task_list_manager.get_all_tasks() if t.objective_id == objective.objective_id and t.status == Status.COMPLETED and t.result];_ = not completed_task_details and (_ := (_ for _ in ()).throw(StopIteration)) # type: ignore
        base_prompt = f"Objective: '{objective.description}'. Completed tasks:\n{chr(10).join(completed_task_details)}\nIs objective fully achieved? Answer YES or NO."
        prompt_with_rag = self._augment_prompt_with_rag_context(original_prompt=base_prompt, query_for_rag=objective.description)
        final_prompt = self._augment_prompt_with_experience_context(original_prompt=prompt_with_rag, query_for_experience=objective.description)
        response_text = self._llm_call(final_prompt, model_category="chat")
        if "yes" in response_text.lower().strip(): return True
        return False

    def generate_next_steps(self, objective: Objective, task_list_manager: 'TaskListManager') -> List[Task]: # Copied
        prompt_header = f"You are '{self.persona_name}' determining next actions."
        task_details = [f"- Task: {t.description} (Status: {t.status.value}{f', Result: {str(t.result)[:100]}' if t.status == Status.COMPLETED and t.result else ''})" for t in task_list_manager.get_all_tasks() if t.objective_id == objective.objective_id]
        base_prompt = f"Objective: '{objective.description}'.\nTasks:\n{chr(10).join(task_details)}\nNext specific, actionable tasks? If complete: 'OBJECTIVE LOOKS COMPLETE'. If stuck: 'CANNOT DETERMINE NEXT STEPS'. Else, list new tasks."
        prompt_with_rag = self._augment_prompt_with_rag_context(original_prompt=base_prompt, query_for_rag=objective.description)
        final_prompt = self._augment_prompt_with_experience_context(original_prompt=prompt_with_rag, query_for_experience=objective.description)
        response_text = self._llm_call(final_prompt, model_category="chat")
        new_tasks = [];
        if "LLM call failed" in response_text or "OBJECTIVE LOOKS COMPLETE" in response_text.upper() or "CANNOT DETERMINE NEXT STEPS" in response_text.upper() or not response_text.strip(): return new_tasks
        for i, line_content in enumerate(response_text.split('\n')): line_content = line_content.strip(); task_desc = re.sub(r'^\s*[\d\W]+\s*', '', line_content);_ = not task_desc and (_ := next);_ = task_desc and (highest_priority_task := task_list_manager.get_highest_priority_task()) and (base_priority := highest_priority_task.priority if highest_priority_task else 0) and new_tasks.append(Task(description=task_desc, objective_id=objective.objective_id, priority=base_priority + 1, created_by_agent_id=self.agent_id)) # type: ignore
        return new_tasks

    def clone(self, agent_id_suffix: str = "clone", persona_name_override: Optional[str] = None, chat_models_override: Optional[List[str]] = None, utility_models_override: Optional[List[str]] = None, embedding_model_override: Optional[str] = None, specialization_description_override: Optional[str] = None, core_directives_override: Optional[List[str]] = None, dedicated_chroma_collection_name_override: Optional[str] = None, rag_results_count_override: Optional[int] = None, rag_max_context_length_override: Optional[int] = None, experience_results_count_override: Optional[int] = None, experience_max_context_length_override: Optional[int] = None): # Copied
        cloned_agent_id = f"{self.agent_id}_{agent_id_suffix}"
        final_persona_name = persona_name_override if persona_name_override is not None else self.persona_name
        final_chat_models = chat_models_override if chat_models_override is not None else list(self.chat_models); final_utility_models = utility_models_override if utility_models_override is not None else list(self.utility_models); final_embedding_model = embedding_model_override if embedding_model_override is not None else self.embedding_model_name; final_spec_desc = specialization_description_override if specialization_description_override is not None else self.specialization_description; final_directives = core_directives_override if core_directives_override is not None else list(self.core_directives); final_collection_name = dedicated_chroma_collection_name_override
        final_rag_results = rag_results_count_override if rag_results_count_override is not None else self.rag_results_count
        final_rag_max_len = rag_max_context_length_override if rag_max_context_length_override is not None else self.rag_max_context_length
        final_exp_results = experience_results_count_override if experience_results_count_override is not None else self.experience_results_count
        final_exp_max_len = experience_max_context_length_override if experience_max_context_length_override is not None else self.experience_max_context_length
        return Agent(agent_id=cloned_agent_id, ollama_host=self.ollama_client.host, persona_name=final_persona_name, chat_models=final_chat_models, utility_models=final_utility_models, embedding_model=final_embedding_model, chroma_service_path=self.chroma_service_path, specialization_description=final_spec_desc, core_directives=final_directives, dedicated_chroma_collection_name=final_collection_name, rag_results_count=final_rag_results, rag_max_context_length=final_rag_max_len, experience_results_count=final_exp_results, experience_max_context_length=final_exp_max_len)

    ```

    ```python
    # agent_zero/self_play/loop.py
    # (Ensure AgentState is imported: from .agent import Agent, AgentState)
    # ... (rest of imports and function signature) ...
    # (Pasted for context, the tool will only apply the diff to the existing loop.py)
    from .models import Objective, Status, Task
    from .task_manager import TaskListManager
    from .agent import Agent, AgentState # Import AgentState
    from typing import Optional, Callable, Dict, Any

    def self_play_loop(
        initial_objective_prompt: str,
        orchestrator_agent: Agent,
        task_list_manager: TaskListManager,
        max_interactions: int = 10,
        on_interaction_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        use_cloning_for_tasks: bool = True
    ):
        objective = Objective(description=initial_objective_prompt, initial_prompt=initial_objective_prompt)
        print(f"Starting self-play loop for objective: {objective.description[:100]}... (ID: {objective.objective_id}) by {orchestrator_agent.persona_name} ({orchestrator_agent.agent_id})")

        orchestrator_agent.current_state = AgentState.TASKED
        print(f"{orchestrator_agent.persona_name} ({orchestrator_agent.agent_id}) state: {orchestrator_agent.current_state.value}")
        orchestrator_agent.decompose_objective_into_tasks(objective, task_list_manager)

        interaction_count = 0

        while objective.status == Status.ACTIVE and interaction_count < max_interactions:
            orchestrator_agent.current_state = AgentState.TASKED
            # ... (current_loop_state_summary and callback)
            current_loop_state_summary = { "interaction_count": interaction_count, "objective_id": objective.objective_id,"objective_description": objective.description,"objective_status": objective.status.value,"task_summary": [(t.task_id, t.description[:60], t.status.value, t.priority) for t in task_list_manager.get_all_tasks()]}
            if on_interaction_callback: on_interaction_callback(current_loop_state_summary)

            if task_list_manager.is_empty():
                if orchestrator_agent.is_objective_complete(objective, task_list_manager):
                    objective.status = Status.COMPLETED
                    orchestrator_agent.current_state = AgentState.IDLE
                    print(f"Objective {objective.objective_id} COMPLETED. {orchestrator_agent.persona_name} state: {orchestrator_agent.current_state.value}.")
                    break
                else:
                    print(f"Task list empty, objective not complete. {orchestrator_agent.persona_name} generating next steps...")
                    new_tasks = orchestrator_agent.generate_next_steps(objective, task_list_manager)
                    if not new_tasks:
                        print(f"{orchestrator_agent.persona_name} could not determine next steps for objective {objective.objective_id}.")
                        # Attempt a simulated challenge if stuck
                        print(f"Transitioning {orchestrator_agent.persona_name} to attempt simulated challenge due to lack of next steps.")
                        challenge_summary = orchestrator_agent.attempt_simulated_challenge() # This method handles its own state changes internally
                        print(f"Simulated challenge outcome for {orchestrator_agent.persona_name}: {challenge_summary if challenge_summary else 'No challenge attempted or completed.'}")

                        objective.status = Status.REQUIRES_INTERVENTION
                        orchestrator_agent.current_state = AgentState.IDLE
                        print(f"Objective {objective.objective_id} requires intervention. {orchestrator_agent.persona_name} state: {orchestrator_agent.current_state.value}")
                        break
                    task_list_manager.add_tasks(new_tasks)

            current_task = task_list_manager.get_highest_priority_task()
            if not current_task:
                print("No pending tasks, objective not complete after attempt to generate. Loop may be stuck.")
                if not orchestrator_agent.is_objective_complete(objective, task_list_manager):
                     objective.status = Status.REQUIRES_INTERVENTION
                else:
                     objective.status = Status.COMPLETED
                orchestrator_agent.current_state = AgentState.IDLE # Set idle before breaking
                break

            print(f"\n--- Interaction {interaction_count + 1} / {max_interactions} ---")
            # Orchestrator is TASKED with managing this task
            # orchestrator_agent.current_state = AgentState.TASKED # Already set at loop start
            print(f"Orchestrator {orchestrator_agent.agent_id} ({orchestrator_agent.persona_name}, State: {orchestrator_agent.current_state.value}) picked task: {current_task.description[:70]}...")
            current_task.status = Status.IN_PROGRESS

            executor_agent = orchestrator_agent
            if use_cloning_for_tasks:
                executor_agent = orchestrator_agent.clone(agent_id_suffix=f"task_{current_task.task_id[:6]}", persona_name_override=f"Executor_{current_task.description[:10].replace(' ','_')}")
            current_task.assigned_to_agent_id = executor_agent.agent_id

            original_executor_state = executor_agent.current_state # Should be IDLE if clone
            executor_agent.current_state = AgentState.TASKED
            # print(f"Executor {executor_agent.agent_id} ({executor_agent.persona_name}, State: {executor_agent.current_state.value}) executing task.") # Less verbose
            task_result, new_sub_tasks = executor_agent.execute_task(current_task, objective)
            current_task.result = task_result

            if executor_agent is not orchestrator_agent:
                 executor_agent.current_state = AgentState.IDLE
            else: # Orchestrator executed the task itself
                 orchestrator_agent.current_state = AgentState.TASKED # Still tasked with objective

            if new_sub_tasks:
                task_list_manager.add_tasks(new_sub_tasks)

            if orchestrator_agent.chroma_service:
                 # print(f"Orchestrator {orchestrator_agent.agent_id} reflecting on task: {current_task.task_id[:8]}") # Less verbose
                 orchestrator_agent.reflect_and_learn_from_task(current_task)

            task_list_manager.reprioritize_tasks(objective.description)

            interaction_count += 1
            if interaction_count >= max_interactions:
                objective.status = Status.REQUIRES_INTERVENTION
                orchestrator_agent.current_state = AgentState.IDLE
                print(f"Max interactions reached. Objective requires intervention. {orchestrator_agent.persona_name} state: {orchestrator_agent.current_state.value}")
                break

        final_objective_status = objective.status.value
        if orchestrator_agent.current_state != AgentState.IDLE : # Ensure it's IDLE if loop ends for other reasons than explicit completion/intervention
            orchestrator_agent.current_state = AgentState.IDLE
        print(f"Self-play loop finished for objective {objective.objective_id}. Final status: {final_objective_status}. Orchestrator state: {orchestrator_agent.current_state.value}")

        final_status_data = { "objective_id": objective.objective_id, "objective_description": objective.description, "final_status": final_objective_status, "total_interactions": interaction_count, "tasks": [(t.task_id, t.description, t.status.value, str(t.result)[:100]) for t in task_list_manager.get_all_tasks()]}
        if on_interaction_callback: on_interaction_callback(final_status_data)
        return objective, task_list_manager

    # ... (if __name__ == '__main__' block)
    ```
