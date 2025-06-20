# agent_zero/self_play/agent.py
import uuid
import ollama
from typing import List, Tuple, Optional, Dict, Any
import re
import time

from .models import Objective, Task, Status
from ..tools.web_scraper import get_text_from_url
from ..utils.text_processing import split_text_into_chunks
from ..memory.chroma_service import ChromaService

DEFAULT_CHAT_MODELS = ["mistral:7b-instruct-q5_K_M", "llama2:7b-chat-q5_K_M"]
DEFAULT_UTILITY_MODELS = ["tinydolphin:1.1b-q4_K_M", "orca-mini:3b-q4_K_M", "phi:2.7b-chat-q4_K_M"]
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text:latest"
FALLBACK_MODEL = "orca-mini:3b-q4_K_M"

class Agent:
    def __init__(self,
                 agent_id: Optional[str] = None,
                 ollama_host='http://localhost:11434',
                 persona_name: str = "GenericAgent",
                 chat_models: Optional[List[str]] = None,
                 utility_models: Optional[List[str]] = None,
                 embedding_model: Optional[str] = None,
                 chroma_service_path: str = "/agent_data/chroma",
                 default_memory_collection: str = "agent_default_memory"):

        self.agent_id = agent_id if agent_id else str(uuid.uuid4())
        self.ollama_client = ollama.Client(host=ollama_host)
        self.persona_name = persona_name

        self.chat_models = chat_models if chat_models is not None else list(DEFAULT_CHAT_MODELS)
        self.utility_models = utility_models if utility_models is not None else list(DEFAULT_UTILITY_MODELS)
        self.embedding_model_name = embedding_model if embedding_model is not None else DEFAULT_EMBEDDING_MODEL
        self.primary_model = self.chat_models[0] if self.chat_models else FALLBACK_MODEL

        self.chroma_service_path = chroma_service_path
        self.default_memory_collection = default_memory_collection

        print(f"Agent {self.agent_id} ({self.persona_name}) initializing...")
        print(f"  Default Chat Model (Primary Fallback): {self.primary_model}")
        print(f"  Available Chat Models: {self.chat_models}")
        print(f"  Available Utility Models: {self.utility_models}")
        print(f"  Embedding Model: {self.embedding_model_name}")

        try:
            self.chroma_service = ChromaService(path=self.chroma_service_path)
            self.chroma_service.get_or_create_collection(self.default_memory_collection)
            print(f"Agent {self.agent_id} ({self.persona_name}) connected to ChromaDB at '{self.chroma_service_path}', default collection: '{self.default_memory_collection}'.")
        except Exception as e:
            print(f"CRITICAL: Agent {self.agent_id} ({self.persona_name}) failed to initialize ChromaService at {self.chroma_service_path}: {e}")
            self.chroma_service = None
        print(f"Agent {self.agent_id} ({self.persona_name}) initialization complete.")

    def _get_model_from_list(self, model_list: List[str], requested_model: Optional[str] = None) -> str:
        if requested_model: return requested_model
        if model_list: return model_list[0]
        print(f"Warning: Model list was empty for {self.persona_name} ({self.agent_id}). Falling back to {FALLBACK_MODEL}")
        return FALLBACK_MODEL

    def _llm_call(self, prompt: str, model_category: str = "chat", requested_model: Optional[str] = None) -> str:
        target_model_name = FALLBACK_MODEL
        if requested_model: target_model_name = requested_model
        elif model_category == "chat": target_model_name = self._get_model_from_list(self.chat_models)
        elif model_category == "utility": target_model_name = self._get_model_from_list(self.utility_models)
        elif model_category == "embedding":
            print(f"Warning: _llm_call used for 'embedding' category by agent {self.agent_id} ({self.persona_name}). This is not standard. Using chat mode.")
            target_model_name = self._get_model_from_list(self.chat_models)
        else:
            print(f"Treating model_category '{model_category}' as specific model name for {self.agent_id} ({self.persona_name}).")
            target_model_name = model_category

        # print(f"Agent {self.agent_id} ({self.persona_name}) using model '{target_model_name}' for prompt: '{prompt[:100]}...'") # Verbose, consider reducing for RAG prompts
        try:
            response = self.ollama_client.chat(model=target_model_name, messages=[{'role': 'user', 'content': prompt}])
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
                except ValueError: pass
            return error_message

    def generate_embedding(self, text_to_embed: str, requested_embedding_model: Optional[str] = None) -> Optional[List[float]]:
        embed_model_to_use = requested_embedding_model if requested_embedding_model else self.embedding_model_name
        if "embed" not in embed_model_to_use.lower() and embed_model_to_use not in DEFAULT_UTILITY_MODELS and embed_model_to_use not in DEFAULT_CHAT_MODELS: # Basic check
            print(f"Warning: Agent {self.agent_id} ({self.persona_name}) attempting to use potentially non-embedding model '{embed_model_to_use}' for embeddings.")
        # print(f"Agent {self.agent_id} ({self.persona_name}) generating embedding using model '{embed_model_to_use}' for text: '{text_to_embed[:100]}...'") # Reduced verbosity
        try:
            response = self.ollama_client.embeddings(model=embed_model_to_use, prompt=text_to_embed)
            return response.get("embedding")
        except Exception as e:
            print(f"Error during embedding generation for agent {self.agent_id} ({self.persona_name}) with model {embed_model_to_use}: {e}")
            error_detail_str = str(e).lower()
            if "model not found" in error_detail_str or "pull model" in error_detail_str or "models are not available" in error_detail_str:
                 print(f"Embedding model '{embed_model_to_use}' may not be pulled or available. Try `ollama pull {embed_model_to_use}`.")
            return None

    def process_and_store_text_in_memory(
        self,
        text_content: str,
        source_metadata: Dict[str, Any],
        collection_name: Optional[str] = None,
        chunk_strategy: str = "paragraph",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> Tuple[int, int]:
        if not self.chroma_service:
            print(f"Agent {self.agent_id} ({self.persona_name}): ChromaService not available. Cannot store text.")
            return 0, 0
        if not text_content:
            print(f"Agent {self.agent_id} ({self.persona_name}): No text content provided to process and store.")
            return 0, 0

        target_collection = collection_name if collection_name else self.default_memory_collection
        source_identifier = source_metadata.get('url', source_metadata.get('source_type', 'Unknown'))
        print(f"Agent {self.agent_id} ({self.persona_name}): Processing text for storage in Chroma collection '{target_collection}'. Source: {source_identifier}")

        chunks = split_text_into_chunks(text_content, chunk_size=chunk_size, chunk_overlap=chunk_overlap, strategy=chunk_strategy)
        if not chunks:
            print(f"Agent {self.agent_id} ({self.persona_name}): Text content from '{source_identifier}' resulted in no processable chunks.")
            return 0, 0

        # print(f"Agent {self.agent_id} ({self.persona_name}): Generated {len(chunks)} chunks from '{source_identifier}'. Now generating embeddings...") # Reduced verbosity

        embeddings_to_store: List[List[float]] = []
        documents_to_store: List[str] = []
        metadatas_to_store: List[Dict[str, Any]] = []
        ids_to_store: List[str] = []

        processed_chunks_count = 0
        for i, chunk_text in enumerate(chunks):
            processed_chunks_count += 1
            embedding = self.generate_embedding(chunk_text)
            if embedding:
                embeddings_to_store.append(embedding)
                documents_to_store.append(chunk_text)

                chunk_metadata = source_metadata.copy()
                chunk_metadata['chunk_index'] = i
                chunk_metadata['chunk_length_chars'] = len(chunk_text)
                metadatas_to_store.append(chunk_metadata)

                raw_id_part = f"{source_metadata.get('task_id', 'unk_task')}_{source_identifier}_chunk{i}"
                sanitized_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', raw_id_part)
                sanitized_id = re.sub(r'_{2,}', '_', sanitized_id)
                sanitized_id = re.sub(r'\.{2,}', '.', sanitized_id)
                if sanitized_id.startswith('.'): sanitized_id = '_' + sanitized_id[1:]
                if sanitized_id.endswith('.'): sanitized_id = sanitized_id[:-1] + '_'
                if len(sanitized_id) > 63: sanitized_id = sanitized_id[:63]
                if not sanitized_id : sanitized_id = f"default_id_{uuid.uuid4().hex[:8]}"
                ids_to_store.append(sanitized_id)
            else:
                print(f"Agent {self.agent_id} ({self.persona_name}): Failed to generate embedding for chunk {i} from '{source_identifier}'. Skipping.")

        if not documents_to_store:
            print(f"Agent {self.agent_id} ({self.persona_name}): No embeddings generated for content from '{source_identifier}'. Nothing to store.")
            return processed_chunks_count, 0

        print(f"Agent {self.agent_id} ({self.persona_name}): Storing {len(documents_to_store)} chunks with embeddings from '{source_identifier}' into collection '{target_collection}'.")
        success = self.chroma_service.add_documents(
            collection_name=target_collection,
            documents=documents_to_store,
            embeddings=embeddings_to_store,
            metadatas=metadatas_to_store,
            ids=ids_to_store
        )

        stored_count = len(documents_to_store) if success else 0
        if success:
            print(f"Agent {self.agent_id} ({self.persona_name}): Successfully stored {stored_count} chunks from '{source_identifier}'.")
        else:
            print(f"Agent {self.agent_id} ({self.persona_name}): Failed to store chunks from '{source_identifier}' in ChromaDB.")

        return processed_chunks_count, stored_count

    def retrieve_relevant_info_from_memory(
        self,
        query_text: str,
        collection_name: Optional[str] = None,
        n_results: int = 3,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        if not self.chroma_service:
            print(f"Agent {self.agent_id} ({self.persona_name}): ChromaService not available. Cannot retrieve info.")
            return []
        if not query_text:
            print(f"Agent {self.agent_id} ({self.persona_name}): No query text provided for retrieval.")
            return []

        target_collection = collection_name if collection_name else self.default_memory_collection

        # print(f"Agent {self.agent_id} ({self.persona_name}): Generating embedding for query: '{query_text[:100]}...'") # Reduced verbosity
        query_embedding = self.generate_embedding(query_text)

        if not query_embedding:
            print(f"Agent {self.agent_id} ({self.persona_name}): Failed to generate embedding for query. Cannot retrieve.")
            return []

        print(f"Agent {self.agent_id} ({self.persona_name}): Querying collection '{target_collection}' for relevant info (n_results={n_results}) related to: '{query_text[:50]}...'")
        query_results = self.chroma_service.query_collection(
            collection_name=target_collection,
            query_embeddings=[query_embedding],
            n_results=n_results,
            where_filter=where_filter,
            include_fields=["documents", "metadatas", "distances"]
        )

        retrieved_docs: List[str] = []
        if query_results and query_results.get('documents') and query_results['documents'][0]:
            retrieved_docs = [doc_text for doc_text in query_results['documents'][0]]
            print(f"Agent {self.agent_id} ({self.persona_name}): Retrieved {len(retrieved_docs)} document chunks.")
        else:
            print(f"Agent {self.agent_id} ({self.persona_name}): No relevant documents found in collection '{target_collection}' for the query.")

        return retrieved_docs

    def _augment_prompt_with_rag_context(
        self,
        original_prompt: str,
        query_for_rag: str,
        collection_name: Optional[str] = None,
        n_rag_results: int = 3,
        max_context_length: int = 3000
    ) -> str:
        if not self.chroma_service:
            return original_prompt

        print(f"Agent {self.agent_id} ({self.persona_name}): Attempting RAG retrieval for query: '{query_for_rag[:100]}...'")
        retrieved_chunks = self.retrieve_relevant_info_from_memory(
            query_text=query_for_rag,
            collection_name=collection_name,
            n_results=n_rag_results
        )

        if not retrieved_chunks:
            print(f"Agent {self.agent_id} ({self.persona_name}): No relevant context found in memory for RAG for query '{query_for_rag[:50]}...'.")
            return original_prompt

        context_str = "\n\n---\n\n".join(retrieved_chunks)

        if len(context_str) > max_context_length:
            print(f"Agent {self.agent_id} ({self.persona_name}): RAG context length ({len(context_str)}) exceeds max ({max_context_length}). Truncating.")
            context_str = context_str[:max_context_length] + "... (truncated)"

        augmented_prompt = (
            f"You have the following relevant context from memory to help you answer the user's request:\n"
            f"--- CONTEXT START ---\n"
            f"{context_str}\n"
            f"--- CONTEXT END ---\n\n"
            f"Based on this context (if relevant and helpful) and your general knowledge, please respond to the following:\n"
            f"{original_prompt}"
        )
        print(f"Agent {self.agent_id} ({self.persona_name}): Prompt augmented with RAG context for query '{query_for_rag[:50]}...'.")
        return augmented_prompt

    def scrape_website(self, url: str, load_wait_time: int = 5) -> Optional[str]:
        print(f"Agent {self.agent_id} ({self.persona_name}) attempting to scrape website: {url}")
        try:
            text_content = get_text_from_url(url, load_wait_time=load_wait_time)
            if text_content:
                print(f"Agent {self.agent_id} ({self.persona_name}) successfully scraped and extracted text from {url}. Length: {len(text_content)}")
            else:
                print(f"Agent {self.agent_id} ({self.persona_name}) reported: No content extracted from {url} or scraping failed.")
            return text_content
        except Exception as e:
            print(f"Agent {self.agent_id} ({self.persona_name}) encountered an error during scraping {url}: {e}")
            return None

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
                    task_obj = Task(description=task_desc, objective_id=objective.objective_id, priority=i + 1, created_by_agent_id=self.agent_id)
                    new_tasks.append(task_obj)
                    if task_list_manager: task_list_manager.add_task(task_obj)
        if not new_tasks and not ("LLM call failed" in response_text):
             task_desc = f"Address the objective: {objective.description}"
             fallback_task = Task(description=task_desc, objective_id=objective.objective_id, priority=1, created_by_agent_id=self.agent_id)
             new_tasks.append(fallback_task)
             if task_list_manager: task_list_manager.add_task(fallback_task)
        print(f"Agent {self.agent_id} ({self.persona_name}) decomposed objective into {len(new_tasks)} tasks.")
        return new_tasks

    def execute_task(self, task: Task, objective: Objective, requested_model_for_execution: Optional[str] = None) -> Tuple[str, List[Task]]:
        task_description_lower = task.description.lower()
        is_scraping_task = task_description_lower.startswith("scrape ") or \
                           task_description_lower.startswith("fetch website ") or \
                           task_description_lower.startswith("get content of url ") or \
                           "scrape url" in task_description_lower or \
                           "fetch content from" in task_description_lower

        if is_scraping_task:
            url_to_scrape = ""
            parts = task_description_lower.split(" ", 1)
            if len(parts) > 1:
                command_removed = parts[1]
                url_parts = command_removed.split(" ")
                for part_url in url_parts:
                    if part_url.startswith("http://") or part_url.startswith("https://"):
                        url_to_scrape = part_url
                        break
                if not url_to_scrape and url_parts:
                    if '.' in url_parts[0] and len(url_parts[0]) > 3:
                         url_to_scrape = url_parts[0]

            if not url_to_scrape:
                url_match = re.search(r'(https?://[^\s]+)', task.description)
                if not url_match:
                    url_match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+(?:/[^\s]*)?)', task.description)

                if url_match:
                    url_to_scrape = url_match.group(0)
                else:
                    msg = f"Agent {self.agent_id} ({self.persona_name}) identified scraping task but could not parse URL from: '{task.description}'."
                    print(msg)
                    task.status = Status.FAILED
                    return msg, []

            if not (url_to_scrape.startswith("http://") or url_to_scrape.startswith("https://")):
                print(f"Warning: URL '{url_to_scrape}' from task '{task.description}' missing scheme, prepending http://")
                url_to_scrape = "http://" + url_to_scrape

            print(f"Agent {self.agent_id} ({self.persona_name}) executing scraping sub-task for URL: {url_to_scrape}")
            scraped_content = self.scrape_website(url_to_scrape)

            if scraped_content:
                source_meta = {'url': url_to_scrape, 'task_id': task.task_id, 'objective_id': objective.objective_id, 'source_type': 'web_scrape', 'scraped_timestamp': time.time()}
                processed, stored = self.process_and_store_text_in_memory(scraped_content, source_meta)
                storage_report = f"Processed {processed} text chunks from {url_to_scrape}. Successfully stored {stored} chunks in memory."
                print(f"Agent {self.agent_id} ({self.persona_name}): {storage_report}")

                summary_prompt = f"Summarize the key information from the following text (max 2-3 sentences). The text was scraped from {url_to_scrape}. If it's very short or seems like an error page, note that.\n\n{scraped_content[:2500]}"
                summary_result = self._llm_call(summary_prompt, model_category="utility")

                final_result = summary_result
                if "LLM call failed" in summary_result:
                    final_result = f"Scraped content from {url_to_scrape} (length: {len(scraped_content)}), but summarization failed. " + storage_report
                else:
                    final_result = f"Summary of {url_to_scrape}: {summary_result}. " + storage_report

                task.status = Status.COMPLETED
                return final_result, []
            else:
                task.status = Status.FAILED
                return f"Failed to scrape content from {url_to_scrape}.", []

        # Default execution path (LLM-based simulation, now with RAG)
        execution_model_category = "chat"
        model_to_use = requested_model_for_execution

        base_execution_prompt = (
            f"Execute the task: '{task.description}'. "
            f"The overall objective is: '{objective.description}'. "
            f"Provide a concise result or summary of the execution. "
            f"If new, smaller, specific sub-tasks are identified as necessary *during* this execution, "
            f"list them as a numbered list AFTER your result, starting with 'New sub-tasks:'."
        )

        final_execution_prompt = self._augment_prompt_with_rag_context(
            original_prompt=base_execution_prompt,
            query_for_rag=task.description
        )

        print(f"Agent {self.agent_id} ({self.persona_name}) executing non-scraping RAG-enhanced task (model category '{execution_model_category}', specific request: {model_to_use if model_to_use else 'None'}): {task.description[:50]}...")

        response_text = self._llm_call(final_execution_prompt, model_category=execution_model_category, requested_model=model_to_use)

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
                    new_task_obj = Task(description=f"(Sub-task of {task.task_id[:8]}): {task_desc}", objective_id=task.objective_id, priority=task.priority, created_by_agent_id=self.agent_id,dependencies=[task.task_id] )
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

        base_prompt = (
            f"Objective: '{objective.description}'.\n"
            f"Summary of current tasks:\n{tasks_summary}\n\n"
            f"Based on this, what are the next specific, actionable tasks to achieve the objective? "
            f"If the objective seems complete, say 'OBJECTIVE LOOKS COMPLETE'. "
            f"Otherwise, list new tasks as a numbered list. Focus on what's missing or needs to be done next."
        )
        # Augment with RAG context, using the objective description as the query
        final_prompt = self._augment_prompt_with_rag_context(
            original_prompt=base_prompt,
            query_for_rag=objective.description
        )

        response_text = self._llm_call(final_prompt, model_category="chat")
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

    def clone(self, agent_id_suffix: str = "clone", persona_name_override: Optional[str] = None,
              chat_models_override: Optional[List[str]] = None,
              utility_models_override: Optional[List[str]] = None,
              embedding_model_override: Optional[str] = None):
        cloned_agent_id = f"{self.agent_id}_{agent_id_suffix}"
        new_persona_name = persona_name_override if persona_name_override is not None else f"{self.persona_name}Clone"
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
            embedding_model=final_embedding_model,
            chroma_service_path=self.chroma_service_path,
            default_memory_collection=self.default_memory_collection + f"_{agent_id_suffix}"
        )
