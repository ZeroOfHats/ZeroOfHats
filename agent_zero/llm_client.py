import ollama
from typing import Optional, Dict, List

class LLMClient:
    """
    A client for interacting with an Ollama Large Language Model.
    """
    def __init__(self, host: str = 'http://localhost:11434'):
        """
        Initializes the LLMClient.

        Args:
            host (str): The host address for the Ollama service.
        """
        self.client = ollama.Client(host=host)
        self.host = host
        print(f"LLMClient initialized for host: {self.host}")

    def call_llm(self,
                 prompt: str,
                 system_message: Optional[str] = None,
                 model: str = "mistral:7b-instruct-q5_K_M",
                 temperature: float = 0.7,
                 raw: bool = False) -> str:
        """
        Sends a prompt to the specified Ollama model and returns the response.

        Args:
            prompt (str): The user's prompt.
            system_message (Optional[str]): An optional system message to guide the LLM's behavior.
            model (str): The Ollama model to use (e.g., "mistral:7b-instruct-q5_K_M").
            temperature (float): The temperature for the LLM response generation.
            raw (bool): If True, sends the prompt as raw text (useful for certain models/modes).

        Returns:
            str: The LLM's response content, or an error message if the call fails.
        """
        messages: List[Dict[str, str]] = []
        if system_message:
            messages.append({'role': 'system', 'content': system_message})
        messages.append({'role': 'user', 'content': prompt})

        try:
            # print(f"LLMClient: Calling model '{model}' at host '{self.host}' with prompt: '{prompt[:100]}...'") # Debug
            if raw:
                response = self.client.generate(
                    model=model,
                    prompt=prompt, # For raw, system message might be implicitly part of prompt or not supported
                    stream=False,
                    options={"temperature": temperature}
                )
                return response.get('response', "Error: Raw response key not found.")
            else:
                response = self.client.chat(
                    model=model,
                    messages=messages,
                    stream=False,
                    options={"temperature": temperature}
                )
                return response['message']['content']
        except ollama.ResponseError as e:
            error_message = f"Error: LLM call to model '{model}' failed. Status: {e.status_code}. Response: {e.error}"
            if "model not found" in e.error.lower():
                error_message += f" The model '{model}' may not be pulled or available. Try `ollama pull {model}`."
            print(error_message)
            return error_message
        except ollama.RequestError as e:
            error_message = f"Error: Could not connect to Ollama at {self.host}. Is Ollama running? Detail: {e}"
            print(error_message)
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred during LLM call to model '{model}': {e}"
            print(error_message)
            return error_message

    def generate_embedding(self,
                           text_to_embed: str,
                           model: str = "nomic-embed-text:latest") -> Optional[List[float]]:
        """
        Generates embeddings for the given text using the specified Ollama embedding model.

        Args:
            text_to_embed (str): The text to embed.
            model (str): The embedding model to use (e.g., "nomic-embed-text:latest").

        Returns:
            Optional[List[float]]: The generated embedding, or None if an error occurs.
        """
        try:
            # print(f"LLMClient: Generating embedding with model '{model}' for text: '{text_to_embed[:100]}...'") # Debug
            response = self.client.embeddings(model=model, prompt=text_to_embed)
            return response.get("embedding")
        except ollama.ResponseError as e:
            error_message = f"Error: Embedding generation with model '{model}' failed. Status: {e.status_code}. Response: {e.error}"
            if "model not found" in e.error.lower():
                error_message += f" The model '{model}' may not be pulled or available. Try `ollama pull {model}`."
            print(error_message)
            return None
        except ollama.RequestError as e:
            error_message = f"Error: Could not connect to Ollama at {self.host} for embedding. Is Ollama running? Detail: {e}"
            print(error_message)
            return None
        except Exception as e:
            error_message = f"An unexpected error occurred during embedding generation with model '{model}': {e}"
            print(error_message)
            return None

if __name__ == '__main__':
    print("Running LLMClient test...")
    # This assumes Ollama is running and the specified models are pulled.
    # You might need to run `ollama serve &` and `ollama pull mistral:7b-instruct-q5_K_M`
    # and `ollama pull nomic-embed-text:latest` in your terminal if not already done.

    client = LLMClient() # Default host http://localhost:11434

    # Test chat model
    print("\n--- Testing Chat Model ---")
    chat_model_name = "mistral:7b-instruct-q5_K_M" # Make sure this model is pulled
    # A more robust test would be to check if the model exists first via client.list()
    # but for this basic test, we assume it's available or rely on the error message.

    prompt1 = "What is the capital of France?"
    response1 = client.call_llm(prompt1, model=chat_model_name)
    print(f"Prompt: {prompt1}\nResponse: {response1}")

    prompt2 = "Explain the concept of recursion in one sentence."
    system_prompt2 = "You are a concise computer science tutor."
    response2 = client.call_llm(prompt2, system_message=system_prompt2, model=chat_model_name)
    print(f"\nPrompt: {prompt2}\nSystem: {system_prompt2}\nResponse: {response2}")

    # Test embedding model
    print("\n--- Testing Embedding Model ---")
    embed_model_name = "nomic-embed-text:latest" # Make sure this model is pulled
    text_to_embed = "Hello world, this is a test sentence."
    embedding = client.generate_embedding(text_to_embed, model=embed_model_name)
    if embedding:
        print(f"Text: {text_to_embed}\nEmbedding (first 5 dimensions): {embedding[:5]}... (Length: {len(embedding)})")
    else:
        print(f"Failed to generate embedding for: {text_to_embed}")

    # Test with a model that might not exist (to check error handling)
    print("\n--- Testing Non-Existent Model ---")
    non_existent_model = "this-model-does-not-exist:latest"
    response_error = client.call_llm("Hello?", model=non_existent_model)
    print(f"Prompt: Hello?\nResponse (should be error): {response_error}")

    embedding_error = client.generate_embedding("Test error", model=non_existent_model)
    if embedding_error is None:
        print(f"Correctly failed to generate embedding for non-existent model.")
    else:
        print(f"Unexpectedly got embedding for non-existent model: {embedding_error}")

    print("\nLLMClient test finished.")
