import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import requests

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agent_zero.llm_client import LLMClient

class TestLLMClient(unittest.TestCase):

    def setUp(self):
        self.client = LLMClient(host="http://mockhost", port=12345, default_model="mock-model")

    @patch('requests.post')
    def test_generate_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Ollama's /api/generate when stream=False returns a single JSON object
        # with the full response, not a stream of JSON lines.
        mock_response_data = {
            "model": "mock-model:latest",
            "created_at": "2024-01-01T00:00:00Z",
            "response": "This is a mocked response.",
            "done": True,
            "context": [1, 2, 3],
            "total_duration": 1000000,
            "prompt_eval_count": 10,
            "eval_count": 20,
            "eval_duration": 500000
        }
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        prompt = "Tell me a joke."
        result = self.client.generate(prompt=prompt, model="mock-model", temperature=0.5, num_predict=50)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://mockhost:12345/api/generate")

        expected_payload = {
            "model": "mock-model",
            "prompt": prompt,
            "stream": False,
            "raw": False,
            "options": {
                "temperature": 0.5,
                "num_predict": 50
            }
        }
        self.assertEqual(kwargs['json'], expected_payload)
        self.assertEqual(result, mock_response_data)
        self.assertEqual(result["response"], "This is a mocked response.")

    @patch('requests.post')
    def test_generate_default_model(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Default model response", "done": True}
        mock_post.return_value = mock_response

        self.client.generate(prompt="Test prompt")

        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['model'], "mock-model") # Default model from client init

    @patch('requests.post')
    def test_generate_ollama_api_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200 # Ollama might return 200 OK but with an error in JSON
        mock_response.json.return_value = {"error": "Model not found"}
        mock_post.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            self.client.generate(prompt="Test", model="nonexistent-model")
        self.assertTrue("Ollama API error: Model not found" in str(context.exception))

    @patch('requests.post')
    def test_generate_http_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error")
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.generate(prompt="Test")

    @patch('requests.post')
    def test_generate_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.client.generate(prompt="Test")

    @patch('requests.post')
    def test_generate_raw_mode(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Raw response", "done": True}
        mock_post.return_value = mock_response

        self.client.generate(prompt="Raw test prompt", raw=True)

        args, kwargs = mock_post.call_args
        self.assertTrue(kwargs['json']['raw'])

    @patch('requests.post')
    def test_generate_custom_options(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "WithOptions response", "done": True}
        mock_post.return_value = mock_response

        custom_opts = {"top_k": 40, "top_p": 0.9, "seed": 123}
        # These should override the individual params if also provided in options
        expected_merged_options = {
            "temperature": 0.7, # default from method signature if not in custom_opts
            "num_predict": 512, # default from method signature if not in custom_opts
            "top_k": 40,
            "top_p": 0.9,
            "seed": 123
        }

        self.client.generate(prompt="Test", options=custom_opts)

        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['options'], expected_merged_options)

        # Test that options override temperature and num_predict from method args
        custom_opts_override = {"temperature": 0.2, "num_predict": 100, "seed": 456}
        self.client.generate(prompt="Test", temperature=0.9, num_predict=10, options=custom_opts_override)
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['options']['temperature'], 0.2)
        self.assertEqual(kwargs['json']['options']['num_predict'], 100)
        self.assertEqual(kwargs['json']['options']['seed'], 456)


    @patch('requests.get')
    def test_list_models_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_models_data = {
            "models": [
                {"name": "mock-model:latest", "modified_at": "2024-01-01T00:00:00Z", "size": 12345},
                {"name": "another-model:latest", "modified_at": "2024-01-02T00:00:00Z", "size": 67890}
            ]
        }
        mock_response.json.return_value = mock_models_data
        mock_get.return_value = mock_response

        models = self.client.list_models()

        mock_get.assert_called_once_with("http://mockhost:12345/api/tags")
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]['name'], "mock-model:latest")
        self.assertEqual(models, mock_models_data['models'])

    @patch('requests.get')
    def test_list_models_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Service Unavailable")
        mock_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.list_models()

    @patch('requests.get')
    def test_list_models_empty(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []} # Empty list
        mock_get.return_value = mock_response

        models = self.client.list_models()
        self.assertEqual(models, [])

        mock_response.json.return_value = {} # No 'models' key
        mock_get.return_value = mock_response
        models = self.client.list_models()
        self.assertEqual(models, [])


if __name__ == '__main__':
    unittest.main()
