import logging
import os # For os.urandom in add_documents and __main__
import chromadb
from chromadb.utils import embedding_functions
from chromadb.api.models.Collection import Collection
from typing import List, Optional, Dict, Any

from agent_zero.config_manager import ConfigManager

logger = logging.getLogger(f"AgentZero.ChromaService")

class ChromaService:
    """
    Manages interactions with a ChromaDB vector database for persistent memory.
    Handles document storage, retrieval, and collection management.
    """
    def __init__(self, config: ConfigManager = None, ollama_ef_config: Optional[Dict[str, Any]] = None):
        """
        Initializes the ChromaService.

        Args:
            config (ConfigManager, optional): Configuration manager instance.
                                              If None, a default one is created.
            ollama_ef_config (Optional[Dict[str, Any]], optional):
                Configuration for OllamaEmbeddingFunction. Example:
                {
                    "model_name": "mxbai-embed-large",  // or "nomic-embed-text", "llama2", etc.
                    "ollama_base_url": "http://localhost:11434" // if different from default
                }
                If None, will try to use a default Ollama embedding function based on ConfigManager.
        """
        if config is None:
            logger.info("No ConfigManager provided to ChromaService, creating a new one.")
            self.config = ConfigManager()
        else:
            self.config = config

        try:
            # Using HttpClient to connect to a remote ChromaDB instance (as per docker-compose setup)
            self.client = chromadb.HttpClient(
                host=self.config.chromadb_host,
                port=self.config.chromadb_port,
                # More settings like headers, ssl, etc., can be added if needed.
                # settings=chromadb.Settings(...) # For more granular control if required
            )
            logger.info(f"ChromaService connected to ChromaDB at {self.config.chromadb_host}:{self.config.chromadb_port}")
            self.client.heartbeat() # Check if connection is alive
            logger.info("ChromaDB connection confirmed with heartbeat.")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB at {self.config.chromadb_host}:{self.config.chromadb_port}. Error: {e}", exc_info=True)
            # Depending on desired behavior, could raise the exception or operate in a "disabled" mode.
            # For now, let's make the client None so other methods can check.
            self.client = None
            raise ConnectionError(f"ChromaDB connection failed: {e}") from e

        # Setup default embedding function (Ollama based)
        if ollama_ef_config:
            _ef_model = ollama_ef_config.get("model_name", "mxbai-embed-large") # A common embedding model
            _ef_url = ollama_ef_config.get("ollama_base_url", self.config.ollama_url)
        else:
            _ef_model = self.config.ollama_default_model # Fallback, user should configure a proper embed model
            logger.warning(f"No specific Ollama embedding model configured for ChromaService, "
                           f"defaulting to ollama_default_model ('{_ef_model}') from ConfigManager. "
                           f"Ensure this model is suitable for embeddings or specify one via ollama_ef_config or AGENT_OLLAMA_EMBEDDING_MODEL env var.")
            _ef_url = self.config.ollama_url

        # Check if an environment variable for embedding model is set
        _env_ef_model = os.getenv("AGENT_OLLAMA_EMBEDDING_MODEL")
        if _env_ef_model:
            _ef_model = _env_ef_model
            logger.info(f"Using Ollama embedding model from AGENT_OLLAMA_EMBEDDING_MODEL env var: {_ef_model}")


        self.default_embedding_function = embedding_functions.OllamaEmbeddingFunction(
            model_name=_ef_model,
            url=_ef_url, # Ensure your LLMClient's host/port matches what Ollama server expects
        )
        logger.info(f"ChromaService default embedding function set to Ollama model: '{_ef_model}' via '{_ef_url}'")


    def get_or_create_collection(self, collection_name: str, embedding_function: Optional[Any] = None) -> Optional[Collection]:
        """
        Retrieves an existing collection or creates it if it doesn't exist.

        Args:
            collection_name (str): The name of the collection.
            embedding_function (Optional[Any]): The embedding function to use for this collection.
                                                Defaults to self.default_embedding_function.

        Returns:
            Optional[Collection]: The ChromaDB collection object, or None if client is not available.
        """
        if not self.client:
            logger.error("ChromaDB client is not available. Cannot get or create collection.")
            return None

        ef_to_use = embedding_function if embedding_function is not None else self.default_embedding_function

        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=ef_to_use
                # metadata={"hnsw:space": "cosine"} # Example: configure distance metric
            )
            logger.info(f"Successfully retrieved or created collection: '{collection_name}'")
            return collection
        except Exception as e:
            logger.error(f"Error getting or creating collection '{collection_name}': {e}", exc_info=True)
            return None

    def add_documents(self,
                      collection_name: str,
                      documents: List[str],
                      metadatas: Optional[List[dict]] = None,
                      ids: Optional[List[str]] = None) -> bool:
        """
        Adds documents to the specified collection. Embeddings are generated automatically.

        Args:
            collection_name (str): The name of the collection.
            documents (List[str]): A list of document texts to add.
            metadatas (Optional[List[dict]], optional): A list of metadata dicts, one for each document.
            ids (Optional[List[str]], optional): A list of unique IDs, one for each document.
                                                If None, ChromaDB will generate them.

        Returns:
            bool: True if documents were added successfully, False otherwise.
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            logger.error(f"Cannot add documents, collection '{collection_name}' could not be accessed.")
            return False

        try:
            # Basic validation for list lengths if metadatas or ids are provided
            if metadatas and len(documents) != len(metadatas):
                logger.error("Number of documents and metadatas must match.")
                return False
            if ids and len(documents) != len(ids):
                logger.error("Number of documents and IDs must match.")
                return False

            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids if ids else [f"doc_{os.urandom(8).hex()}_{i}" for i in range(len(documents))] # Ensure unique IDs
            )
            logger.info(f"Successfully added {len(documents)} documents to collection '{collection_name}'.")
            return True
        except Exception as e:
            logger.error(f"Error adding documents to collection '{collection_name}': {e}", exc_info=True)
            return False

    def query_collection(self,
                         collection_name: str,
                         query_texts: List[str],
                         n_results: int = 5,
                         where_filter: Optional[dict] = None,
                         include: Optional[List[str]] = None) -> Optional[dict]:
        """
        Queries the specified collection for documents similar to the query texts.

        Args:
            collection_name (str): The name of the collection.
            query_texts (List[str]): A list of query texts.
            n_results (int, optional): The number of results to return for each query. Defaults to 5.
            where_filter (Optional[dict], optional): A metadata filter. Example: {"source": "website"}.
            include (Optional[List[str]], optional): List of fields to include in results (e.g., ["metadatas", "documents", "distances"]).
                                                     Defaults to ["metadatas", "documents", "distances"].

        Returns:
            Optional[dict]: A dictionary containing query results (documents, metadatas, distances, etc.),
                            or None if an error occurs or collection not found.
                            Structure example:
                            {
                                'ids': [['id1', 'id2']],
                                'distances': [[0.1, 0.2]],
                                'metadatas': [[{'source': 'docA'}, {'source': 'docB'}]],
                                'embeddings': None, (unless requested and supported)
                                'documents': [['text of doc1', 'text of doc2']]
                            }
        """
        collection = self.get_or_create_collection(collection_name) # Use default EF for querying too
        if not collection:
            logger.error(f"Cannot query, collection '{collection_name}' could not be accessed.")
            return None

        if include is None:
            include = ["metadatas", "documents", "distances"]

        try:
            results = collection.query(
                query_texts=query_texts,
                n_results=min(n_results, collection.count()), # Ensure n_results <= items in collection
                where=where_filter,
                include=include
            )
            logger.info(f"Query to collection '{collection_name}' returned {len(results.get('documents', [[]])[0]) if results.get('documents') else 0} results for the first query text.")
            return results
        except Exception as e:
            # ChromaDB might raise specific errors for empty collections or other query issues.
            logger.error(f"Error querying collection '{collection_name}': {e}", exc_info=True)
            return None

    def delete_collection(self, collection_name: str) -> bool:
        """Deletes a collection."""
        if not self.client:
            logger.error("ChromaDB client is not available. Cannot delete collection.")
            return False
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Successfully deleted collection: '{collection_name}'")
            return True
        except Exception as e: # Catches if collection doesn't exist, etc.
            logger.error(f"Error deleting collection '{collection_name}': {e}", exc_info=True)
            return False

    def list_collections(self) -> List[Collection]:
        """Lists all collections in the database."""
        if not self.client:
            logger.error("ChromaDB client is not available. Cannot list collections.")
            return []
        try:
            return self.client.list_collections()
        except Exception as e:
            logger.error(f"Error listing collections: {e}", exc_info=True)
            return []

    def count_documents(self, collection_name: str) -> Optional[int]:
        """Counts documents in a collection."""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return None
        try:
            return collection.count()
        except Exception as e:
            logger.error(f"Error counting documents in collection '{collection_name}': {e}", exc_info=True)
            return None

if __name__ == '__main__':
    import os # For os.urandom for IDs
    from agent_zero.task_logger import setup_logging

    # Setup basic logging for the test run
    try:
        initial_config = ConfigManager() # Load .env if present
        setup_logging(config=initial_config)
        # Set a specific environment variable for testing embedding model if not already set
        if not os.getenv("AGENT_OLLAMA_EMBEDDING_MODEL"):
            os.environ["AGENT_OLLAMA_EMBEDDING_MODEL"] = "mxbai-embed-large" # Use a known good one
            logger.info(f"Temporarily set AGENT_OLLAMA_EMBEDDING_MODEL for test: {os.getenv('AGENT_OLLAMA_EMBEDDING_MODEL')}")
            # Re-init config if it cached old values or ChromaService needs to see new env var
            initial_config = ConfigManager()
    except Exception as e:
        logging.basicConfig(level=logging.DEBUG)
        logger.error(f"Error setting up logging or config for ChromaService test: {e}", exc_info=True)

    logger.info("--- Testing ChromaService ---")

    chroma_service_instance = None
    try:
        # Ensure ChromaDB and Ollama (with an embedding model like mxbai-embed-large or nomic-embed-text)
        # are running as per docker-compose.yml for this test to fully pass.
        chroma_service_instance = ChromaService(config=initial_config)
    except ConnectionError as ce:
        logger.error(f"Failed to initialize ChromaService due to connection error: {ce}")
        logger.error("Please ensure ChromaDB is running and accessible at the configured host/port.")
        chroma_service_instance = None # Ensure it's None if init failed

    if chroma_service_instance and chroma_service_instance.client:
        test_collection_name = f"test_collection_{os.urandom(4).hex()}"
        logger.info(f"Using test collection: {test_collection_name}")

        # 1. Get or create collection
        collection = chroma_service_instance.get_or_create_collection(test_collection_name)
        assert collection is not None
        assert collection.name == test_collection_name
        initial_count = chroma_service_instance.count_documents(test_collection_name)
        assert initial_count == 0

        # 2. Add documents
        docs_to_add = [
            "The quick brown fox jumps over the lazy dog.",
            "Agent Zero is an autonomous AI system.",
            "Large language models are powerful tools for text generation.",
            "Vector databases store embeddings for semantic search."
        ]
        metadatas_to_add = [
            {"source": "classic_phrase", "topic": "animals"},
            {"source": "project_doc", "topic": "ai_agents"},
            {"source": "tech_article", "topic": "llm"},
            {"source": "tech_article", "topic": "databases"}
        ]
        ids_to_add = [f"doc{i+1}" for i in range(len(docs_to_add))]

        # This step requires Ollama to be running with the embedding model
        logger.info(f"Attempting to add documents. This requires Ollama with model "
                    f"'{os.getenv('AGENT_OLLAMA_EMBEDDING_MODEL', chroma_service_instance.default_embedding_function.model_name)}' "
                    f"to be running at '{chroma_service_instance.default_embedding_function._url}'.")
        try:
            add_success = chroma_service_instance.add_documents(test_collection_name, docs_to_add, metadatas_to_add, ids_to_add)
            if not add_success:
                 logger.warning("Adding documents reported failure. Subsequent tests might fail or be inaccurate.")
                 # It might fail if Ollama is not running or the embedding model isn't available.
            assert add_success, "Failed to add documents. Check Ollama & embedding model."

            count_after_add = chroma_service_instance.count_documents(test_collection_name)
            assert count_after_add == len(docs_to_add)
            logger.info(f"Document count after add: {count_after_add}")

            # 3. Query documents
            query1 = "What is Agent Zero?"
            query_results = chroma_service_instance.query_collection(test_collection_name, query_texts=[query1], n_results=2)

            assert query_results is not None
            if query_results and query_results.get("documents"):
                logger.info(f"Query results for '{query1}':")
                for i, doc_list in enumerate(query_results["documents"]):
                    for j, doc in enumerate(doc_list):
                        dist = query_results["distances"][i][j] if query_results.get("distances") else "N/A"
                        meta = query_results["metadatas"][i][j] if query_results.get("metadatas") else {}
                        logger.info(f"  - Result {j+1}: '{doc[:50]}...' (Dist: {dist:.4f}, Meta: {meta})")
                # Check if one of the relevant docs was returned
                assert any("Agent Zero" in doc for doc_list in query_results["documents"] for doc in doc_list)
            else:
                logger.warning(f"Query for '{query1}' returned no documents or an unexpected result format: {query_results}")
                logger.warning("This might happen if adding documents failed due to embedding model issues.")


            # 4. List collections
            collections_list = chroma_service_instance.list_collections()
            assert any(c.name == test_collection_name for c in collections_list)
            logger.info(f"Available collections: {[c.name for c in collections_list]}")

        except Exception as e:
            logger.error(f"An error occurred during ChromaService operations (add/query): {e}", exc_info=True)
            logger.error("This likely means Ollama is not running or the specified embedding model "
                         f"('{os.getenv('AGENT_OLLAMA_EMBEDDING_MODEL', chroma_service_instance.default_embedding_function.model_name)}') is not available in Ollama.")
            logger.error("Please ensure Ollama is running with the required embedding model for full test.")


        # 5. Delete collection
        delete_success = chroma_service_instance.delete_collection(test_collection_name)
        assert delete_success
        collections_list_after_delete = chroma_service_instance.list_collections()
        assert not any(c.name == test_collection_name for c in collections_list_after_delete)
        logger.info(f"Test collection '{test_collection_name}' deleted successfully.")

    else:
        logger.warning("ChromaService instance could not be initialized or client is not available. Skipping functional tests.")
        logger.warning("Ensure ChromaDB is running and accessible.")

    # Clean up env var if it was set by this test script
    if os.getenv("AGENT_OLLAMA_EMBEDDING_MODEL_TEMP_SET_BY_TEST"): # A more robust way to track
        del os.environ["AGENT_OLLAMA_EMBEDDING_MODEL"]
        del os.environ["AGENT_OLLAMA_EMBEDDING_MODEL_TEMP_SET_BY_TEST"]
        logger.info("Cleaned up temporary AGENT_OLLAMA_EMBEDDING_MODEL env var.")

    logger.info("--- ChromaService Test Completed ---")
