# agent_zero/memory/chroma_service.py
import chromadb
from chromadb.utils import embedding_functions # For potential future use with default EFs
from typing import List, Dict, Optional, Any, Union
import datetime
import time # Added for default ID generation

# Default path for ChromaDB persistence, should match Docker volume mount
DEFAULT_CHROMA_PATH = "/agent_data/chroma"

class ChromaService:
    def __init__(self, path: str = DEFAULT_CHROMA_PATH, default_collection_name: str = "agent_zero_default_collection"):
        """
        Initializes the ChromaService.

        Args:
            path (str): Path to the directory where ChromaDB data will be persisted.
            default_collection_name (str): Default collection name to use if none is specified.
        """
        try:
            self.client = chromadb.PersistentClient(path=path)
            self.default_collection_name = default_collection_name
            print(f"ChromaDB PersistentClient initialized at path: {path}")
            # Ensure the default collection exists or create it.
            self.get_or_create_collection(self.default_collection_name)
        except Exception as e:
            print(f"Error initializing ChromaDB client at {path}: {e}")
            print("ChromaDB operations might fail. Ensure the path is writable and permissions are correct.")
            # Optionally re-raise or handle more gracefully depending on application needs
            raise

    def get_or_create_collection(self, collection_name: str, embedding_function_name: Optional[str] = None) -> Optional[chromadb.api.models.Collection.Collection]:
        """
        Gets an existing collection or creates it if it doesn't exist.

        Args:
            collection_name (str): The name of the collection.
            embedding_function_name (str, optional): Name of a default embedding function
                                                     provided by chromadb.utils.embedding_functions
                                                     e.g., "DefaultEmbeddingFunction", "OpenAIEmbeddingFunction".
                                                     If None, collection is created without a specific client-side EF,
                                                     expecting embeddings to be provided manually during add.
                                                     This is our primary use case as Agent Zero generates embeddings.

        Returns:
            Optional[chromadb.api.models.Collection.Collection]: The collection object, or None if error.
        """
        try:
            print(f"Attempting to get or create collection: {collection_name}")
            if embedding_function_name:
                # This is more for when ChromaDB calculates embeddings itself.
                # For Agent Zero, we provide embeddings, so an EF isn't strictly needed at collection level.
                # ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embedding_function_name) # Example, if using sentence-transformers
                # Or use ef = embedding_functions.DefaultEmbeddingFunction() if that's desired.
                # However, for our case, we often don't need to specify an EF if we always supply embeddings.
                # collection = self.client.get_or_create_collection(name=collection_name, embedding_function=ef)
                # For now, let's assume manual embedding provision, so no EF on collection:
                print(f"Warning: embedding_function_name '{embedding_function_name}' provided but Agent Zero typically supplies embeddings manually. Collection will be created without a client-side EF.")
                collection = self.client.get_or_create_collection(name=collection_name)

            else: # No embedding function specified - this is typical if embeddings are pre-calculated and supplied.
                collection = self.client.get_or_create_collection(name=collection_name)

            print(f"Collection '{collection_name}' ready.")
            return collection
        except Exception as e:
            print(f"Error getting or creating collection '{collection_name}': {e}")
            return None

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        Adds documents and their embeddings to the specified collection.

        Args:
            collection_name (str): Name of the collection.
            documents (List[str]): List of text documents/chunks.
            embeddings (List[List[float]]): List of embeddings, one for each document.
            metadatas (Optional[List[Dict[str, Any]]]): List of metadata dicts, one for each document.
            ids (Optional[List[str]]): List of unique IDs for each document. If None, ChromaDB generates them.

        Returns:
            bool: True if successful, False otherwise.
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False

        if not (len(documents) == len(embeddings)):
            print("Error: Number of documents and embeddings must be the same.")
            return False
        if metadatas and not (len(documents) == len(metadatas)):
            print("Error: If providing metadatas, it must match the number of documents.")
            return False
        if ids and not (len(documents) == len(ids)):
            print("Error: If providing IDs, it must match the number of documents.")
            return False

        if not ids:
            base_id = f"doc_{int(time.time())}"
            ids = [f"{base_id}_{i}" for i in range(len(documents))]

        processed_metadatas = []
        current_timestamp = datetime.datetime.utcnow().isoformat()
        for i in range(len(documents)):
            current_doc_metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            if 'source_timestamp' not in current_doc_metadata:
                current_doc_metadata['source_timestamp'] = current_timestamp
            processed_metadatas.append(current_doc_metadata)

        try:
            print(f"Adding {len(documents)} documents to collection '{collection_name}'. First ID: {ids[0] if ids else 'N/A'}")
            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=processed_metadatas,
                ids=ids
            )
            print("Documents added successfully.")
            return True
        except Exception as e:
            print(f"Error adding documents to collection '{collection_name}': {e}")
            return False

    def query_collection(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where_filter: Optional[Dict[str, Union[str, float, Dict]]] = None,
        include_fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Queries the specified collection using query embeddings.

        Args:
            collection_name (str): Name of the collection.
            query_embeddings (List[List[float]]): List of query embeddings.
            n_results (int): Number of results to retrieve.
            where_filter (Optional[Dict]): Metadata filter.
            include_fields (Optional[List[str]]): Fields to include in results. Default: ["metadatas", "documents", "distances"].

        Returns:
            Optional[Dict[str, Any]]: Query results, or None if error.
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return None

        if include_fields is None:
            include_fields = ["metadatas", "documents", "distances"]

        try:
            print(f"Querying collection '{collection_name}' with {len(query_embeddings)} embedding(s), n_results={n_results}.")
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where_filter,
                include=include_fields
            )
            return results
        except Exception as e:
            print(f"Error querying collection '{collection_name}': {e}")
            return None

    def list_collections(self) -> List[str]:
        """Lists all collections in the database."""
        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []

    def delete_collection(self, collection_name: str) -> bool:
        """Deletes a collection."""
        try:
            self.client.delete_collection(name=collection_name)
            print(f"Collection '{collection_name}' deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting collection '{collection_name}': {e}")
            return False

if __name__ == '__main__':
    # Example Usage (assumes ChromaDB can run and write to ./chroma_data_test relative to this script)
    test_db_path = "./chroma_data_test"
    print(f"ChromaService example using DB path: {test_db_path}")

    import shutil
    try:
        shutil.rmtree(test_db_path)
        print(f"Cleaned up previous test DB at {test_db_path}")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Could not clean up previous test DB: {e}")

    service = None
    try:
        service = ChromaService(path=test_db_path, default_collection_name="my_test_collection")

        print("\n--- Listing collections ---")
        collections = service.list_collections()
        print(f"Available collections: {collections}")
        assert "my_test_collection" in collections

        print("\n--- Adding documents ---")
        docs = ["This is document 1 about apples.", "Document 2 discusses bananas.", "The third document is about oranges and apples."]
        embeds = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        metas = [{"source": "doc_A", "type": "fruit"}, {"source": "doc_B", "type": "fruit"}, {"source": "doc_C", "type": "fruit"}]
        ids = ["id1", "id2", "id3"]

        success = service.add_documents("my_test_collection", docs, embeds, metas, ids)
        assert success

        success_extra = service.add_documents("my_test_collection", ["An extra document about berries."], [[0.2,0.3,0.4]], [{"source":"doc_D"}])
        assert success_extra

        print("\n--- Querying collection (apples) ---")
        query_embedding_apple = [[0.15, 0.25, 0.35]]
        results_apple = service.query_collection("my_test_collection", query_embeddings=query_embedding_apple, n_results=2)
        if results_apple and results_apple['documents']:
            print("Found documents for 'apples':")
            for i, doc_text in enumerate(results_apple['documents'][0]):
                print(f"  - {doc_text} (ID: {results_apple['ids'][0][i]}, Dist: {results_apple['distances'][0][i]})")
            assert "apples" in results_apple['documents'][0][0].lower()

        print("\n--- Querying collection (berries with filter) ---")
        query_embedding_berry = [[0.25,0.35,0.45]]
        results_berry_filtered = service.query_collection(
            "my_test_collection",
            query_embeddings=query_embedding_berry,
            n_results=1,
            where_filter={"source": "doc_D"}
        )
        if results_berry_filtered and results_berry_filtered['documents']:
            print("Found documents for 'berries' (filtered by source 'doc_D'):")
            for i, doc_text in enumerate(results_berry_filtered['documents'][0]):
                 print(f"  - {doc_text} (ID: {results_berry_filtered['ids'][0][i]})")
            assert "berries" in results_berry_filtered['documents'][0][0].lower()
        else:
            print("Filtered berry query didn't return expected results or an error occurred.")

        print("\n--- Testing another collection ---")
        service.get_or_create_collection("another_collection")
        print(f"Available collections: {service.list_collections()}")
        assert "another_collection" in service.list_collections()

        print("\n--- Deleting a collection ---")
        service.delete_collection("another_collection")
        print(f"Available collections after delete: {service.list_collections()}")
        assert "another_collection" not in service.list_collections()

        print("\nChromaService example completed successfully.")

    except Exception as e:
        print(f"An error occurred during ChromaService example: {e}")
    finally:
        if service and test_db_path:
            try:
                print(f"Cleaning up test DB at {test_db_path}")
                shutil.rmtree(test_db_path)
            except Exception as e:
                print(f"Error during cleanup of {test_db_path}: {e}")
