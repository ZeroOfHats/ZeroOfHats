import requests
import json
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    """
    A client for interacting with a local LLM service like Ollama.
    """
    def __init__(self, host: str = "http://localhost", port: int = 11434, default_model: str = "llama2"):
        """
        Initializes the LLMClient.

        Args:
            host (str): The host of the LLM service.
            port (int): The port of the LLM service.
            default_model (str): The default model to use if none is specified.
        """
        self.base_url = f"{host}:{port}"
        self.api_generate_url = f"{self.base_url}/api/generate"
        self.api_tags_url = f"{self.base_url}/api/tags" # For listing models
        self.default_model = default_model
        logger.info(f"LLMClient initialized for {self.base_url}, default model: {self.default_model}")

    def generate(self,
                 prompt: str,
                 model: str = None,
                 temperature: float = 0.7,
                 # num_predict is Ollama's equivalent for max_tokens for the /api/generate endpoint
                 num_predict: int = 512,
                 raw: bool = False, # For certain models, raw mode can be useful
                 options: dict = None) -> dict:
        """
        Generates text using the LLM service.

        Args:
            prompt (str): The prompt to send to the LLM.
            model (str, optional): The model to use. Defaults to self.default_model.
            temperature (float, optional): The temperature for generation. Defaults to 0.7.
            num_predict (int, optional): The maximum number of tokens to generate. Defaults to 512.
                                         Corresponds to Ollama's 'num_predict' in options.
            raw (bool, optional): Whether to use raw mode (for some models). Defaults to False.
            options (dict, optional): Additional Ollama-specific options.
                                      Overrides temperature and num_predict if they are set within options.
                                      See https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values

        Returns:
            dict: The JSON response from the LLM service, typically including the generated text and other metadata.
                  Example (for non-streaming):
                  {
                    "model": "llama2:latest",
                    "created_at": "2023-12-12T14:02:56.860019Z",
                    "response": "The sky is blue because of Rayleigh scattering.",
                    "done": true,
                    "context": [1, 2, 3...], (optional, if a context window is maintained)
                    "total_duration": 1234567890,
                    ...
                  }

        Raises:
            requests.exceptions.RequestException: If there's an issue with the HTTP request.
            ValueError: If the response from the server is not valid JSON or indicates an error.
        """
        if model is None:
            model = self.default_model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False, # For this client, we'll handle non-streaming responses first
            "raw": raw
        }

        # Ollama specific options. Temperature and num_predict are common.
        # If an 'options' dict is passed, it takes precedence for these values.
        generation_options = {
            "temperature": temperature,
            "num_predict": num_predict,
            # Add other common options here if needed, e.g., top_k, top_p
        }
        if options:
            generation_options.update(options)

        payload["options"] = generation_options

        logger.debug(f"Sending generation request to {self.api_generate_url} with payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(self.api_generate_url, json=payload)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            response_data = response.json()
            logger.debug(f"Received response: {json.dumps(response_data, indent=2)}")

            if response_data.get("error"):
                logger.error(f"Ollama API returned an error: {response_data['error']}")
                raise ValueError(f"Ollama API error: {response_data['error']}")

            # Ensure 'response' key exists for successful generation
            if "response" not in response_data and not response_data.get("done", False):
                logger.warning(f"Response from Ollama did not contain 'response' key but no explicit error. Full response: {response_data}")
                # Depending on strictness, could raise ValueError here.
                # For now, return as is, user might inspect.

            return response_data

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            raise
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred: {conn_err}. Is Ollama running at {self.base_url}?")
            raise
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error occurred: {timeout_err}")
            raise
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An unexpected error occurred with the request: {req_err}")
            raise
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to decode JSON response: {json_err}. Response text: {response.text}")
            raise ValueError(f"Invalid JSON response from server: {json_err}")

    def list_models(self) -> list[dict]:
        """
        Lists the models available in the Ollama service.

        Returns:
            list[dict]: A list of model details. Example:
            {
              "models": [
                {
                  "name": "llama2:latest",
                  "modified_at": "2023-11-06T15:08:01.744719-08:00",
                  "size": 3825819519,
                  "digest": "fe938a131f40e6f6d40083c9f0f424d4e1970993a825d025e1a310fed76700d9"
                },
                ...
              ]
            }

        Raises:
            requests.exceptions.RequestException: If there's an issue with the HTTP request.
        """
        logger.debug(f"Requesting model list from {self.api_tags_url}")
        try:
            response = requests.get(self.api_tags_url)
            response.raise_for_status()
            models_data = response.json()
            logger.debug(f"Received models: {models_data.get('models')}")
            return models_data.get("models", [])
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred while listing models: {http_err} - Response: {response.text}")
            raise
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred while listing models: {conn_err}. Is Ollama running?")
            raise
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An unexpected error occurred with the request while listing models: {req_err}")
            raise
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to decode JSON response for models list: {json_err}. Response text: {response.text}")
            raise ValueError(f"Invalid JSON response from server for models list: {json_err}")

if __name__ == '__main__':
    # Basic example usage and test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Assuming Ollama is running locally and has a model like 'phi3' or 'llama2'
    # Ensure you have a model downloaded, e.g., by running `ollama pull phi3` in your terminal
    TEST_MODEL = "phi3:mini" # Change this to a model you have, e.g., "llama2"

    client = LLMClient(default_model=TEST_MODEL)

    try:
        logger.info("Attempting to list available models...")
        available_models = client.list_models()
        if not available_models:
            logger.warning(f"No models found or Ollama not accessible. Make sure Ollama is running and you have pulled models (e.g., `ollama pull {TEST_MODEL}`).")
        else:
            logger.info(f"Available models: {[m['name'] for m in available_models]}")
            # Check if default model is available
            if not any(m['name'].startswith(TEST_MODEL.split(':')[0]) for m in available_models): # Check base model name
                logger.warning(f"Default model {TEST_MODEL} not found in available models. Generation test might fail or use another model if Ollama has a fallback.")
                # Fallback to the first available model if TEST_MODEL is not present
                if available_models:
                    TEST_MODEL = available_models[0]['name']
                    logger.info(f"Using first available model for test: {TEST_MODEL}")
                else:
                    logger.error("No models available to test generation.")
                    exit(1)


        logger.info(f"\nAttempting to generate text with model: {TEST_MODEL}...")
        prompt_text = "Why is the sky blue?"
        generation_result = client.generate(prompt=prompt_text, model=TEST_MODEL, num_predict=50)

        if generation_result and "response" in generation_result:
            logger.info(f"Prompt: {prompt_text}")
            logger.info(f"Response from {generation_result.get('model', 'unknown model')}:")
            logger.info(generation_result["response"])
        elif generation_result and "error" in generation_result:
            logger.error(f"Generation failed with error: {generation_result['error']}")
        else:
            logger.error(f"Generation failed or returned an unexpected response format: {generation_result}")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Could not connect to Ollama at {client.base_url}. Please ensure Ollama is running. Details: {e}")
    except Exception as e:
        logger.error(f"An error occurred during LLMClient test: {e}", exc_info=True)

    # Example with options
    try:
        logger.info(f"\nAttempting to generate text with model: {TEST_MODEL} and custom options...")
        prompt_text = "Tell me a short joke."
        custom_options = {"temperature": 0.2, "num_predict": 30, "top_p": 0.9, "seed": 42}
        generation_result = client.generate(prompt=prompt_text, model=TEST_MODEL, options=custom_options)

        if generation_result and "response" in generation_result:
            logger.info(f"Prompt: {prompt_text}")
            logger.info(f"Response from {generation_result.get('model', 'unknown model')} (with custom options):")
            logger.info(generation_result["response"])
        elif generation_result and "error" in generation_result:
            logger.error(f"Generation with custom options failed with error: {generation_result['error']}")
        else:
            logger.error(f"Generation with custom options failed or returned an unexpected response format: {generation_result}")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Could not connect to Ollama at {client.base_url}. Please ensure Ollama is running. Details: {e}")
    except Exception as e:
        logger.error(f"An error occurred during LLMClient custom options test: {e}", exc_info=True)
