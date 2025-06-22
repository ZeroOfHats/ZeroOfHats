import unittest
from unittest.mock import patch, MagicMock, ANY
import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agent_zero.agent import Agent
from agent_zero.config_manager import ConfigManager
from agent_zero.llm_client import LLMClient
from agent_zero.memory.chroma_service import ChromaService
from agent_zero.self_play.models import Objective, Task, Status # For task processing tests
from agent_zero.self_play.task_manager import TaskListManager # For task processing tests

class TestAgent(unittest.TestCase):

    def setUp(self):
        # Basic config for tests
        self.config = ConfigManager(dotenv_path=".nonexistentenv_agenttest") # Use defaults

        # Mock LLMClient
        self.mock_llm_client = MagicMock(spec=LLMClient)
        self.mock_llm_client.default_model = self.config.ollama_default_model

        # Mock ChromaService
        self.mock_chroma_service = MagicMock(spec=ChromaService)
        self.mock_chroma_service.client = MagicMock() # Simulate connected client
        self.config.chromadb_default_collection_name = "test_default_collection"


    def test_agent_initialization_defaults(self):
        with patch('agent_zero.agent.ConfigManager') as MockCfg, \
             patch('agent_zero.agent.LLMClient') as MockLLM, \
             patch('agent_zero.agent.ChromaService') as MockChroma:

            mock_cfg_instance = MockCfg.return_value
            mock_llm_instance = MockLLM.return_value
            mock_chroma_instance = MockChroma.return_value
            mock_chroma_instance.client = MagicMock() # Ensure mocked Chroma has a client

            agent = Agent()

            self.assertEqual(agent.persona_name, "default_agent")
            self.assertListEqual(agent.core_directives, ["Be helpful and efficient."])
            self.assertIsNotNone(agent.agent_id)
            MockCfg.assert_called_once()
            MockLLM.assert_called_once()
            MockChroma.assert_called_once() # Called with config=mock_cfg_instance
            self.assertEqual(agent.config, mock_cfg_instance)
            self.assertEqual(agent.llm_client, mock_llm_instance)
            self.assertEqual(agent.chroma_service, mock_chroma_instance)

    def test_agent_initialization_with_params(self):
        directives = ["Test Directive 1"]
        agent = Agent(
            persona_name="TestAgent",
            core_directives=directives,
            config=self.config,
            llm_client=self.mock_llm_client,
            chroma_service=self.mock_chroma_service
        )
        self.assertEqual(agent.persona_name, "TestAgent")
        self.assertEqual(agent.core_directives, directives)
        self.assertEqual(agent.config, self.config)
        self.assertEqual(agent.llm_client, self.mock_llm_client)
        self.assertEqual(agent.chroma_service, self.mock_chroma_service)

    def test_agent_initialization_chroma_connection_error(self):
        with patch('agent_zero.agent.ConfigManager'), \
             patch('agent_zero.agent.LLMClient'), \
             patch('agent_zero.agent.ChromaService', side_effect=ConnectionError("Test Chroma connection failed")):

            agent = Agent() # ChromaService init should fail
            self.assertIsNone(agent.chroma_service, "ChromaService should be None if connection fails during Agent init")


    def test_think_success(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)

        mock_llm_response = {"response": "  LLM says hello!  ", "done": True}
        self.mock_llm_client.generate.return_value = mock_llm_response

        user_prompt = "Hello agent"
        response = agent.think(user_prompt)

        self.mock_llm_client.generate.assert_called_once()
        call_args = self.mock_llm_client.generate.call_args
        # Check that persona and directives are in the prompt
        # The exact prompt format can be complex, so check for key parts.
        self.assertIn(agent.persona_name, call_args[1]['prompt'])
        self.assertIn(agent.core_directives[0], call_args[1]['prompt'])
        self.assertIn(user_prompt, call_args[1]['prompt'])

        self.assertEqual(response, "LLM says hello!") # Check stripping of whitespace

    def test_think_with_history(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)
        self.mock_llm_client.generate.return_value = {"response": "Follow up.", "done": True}

        history = [{"role": "user", "content": "Previous q"}, {"role": "assistant", "content": "Previous a"}]
        agent.think("Current q", conversation_history=history)

        call_args = self.mock_llm_client.generate.call_args
        self.assertIn("Previous q", call_args[1]['prompt'])
        self.assertIn("Previous a", call_args[1]['prompt'])

    def test_think_llm_api_error(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)
        self.mock_llm_client.generate.return_value = {"error": "Model blew up"}

        response = agent.think("Test")
        self.assertEqual(response, "Error: Could not get a response from the LLM (Model blew up).")

    def test_think_llm_exception(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)
        self.mock_llm_client.generate.side_effect = Exception("Network failure")

        response = agent.think("Test")
        self.assertEqual(response, "Error: An exception occurred while communicating with the LLM: Network failure")

    def test_save_to_memory_success(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)
        self.mock_chroma_service.add_documents.return_value = True

        doc_text = "This is a test document."
        metadata = {"source": "test"}
        doc_id = "test_doc_001"

        success = agent.save_to_memory(doc_text, metadata=metadata, doc_id=doc_id, collection_name="custom_coll")

        self.assertTrue(success)
        self.mock_chroma_service.add_documents.assert_called_once_with(
            collection_name="custom_coll",
            documents=[doc_text],
            metadatas=[metadata],
            ids=[doc_id]
        )

    def test_save_to_memory_default_collection(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)
        self.mock_chroma_service.add_documents.return_value = True

        agent.save_to_memory("Test doc")
        self.mock_chroma_service.add_documents.assert_called_once()
        call_args = self.mock_chroma_service.add_documents.call_args
        self.assertEqual(call_args[1]['collection_name'], self.config.chromadb_default_collection_name)


    def test_save_to_memory_chroma_unavailable(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=None) # Simulate unavailable
        success = agent.save_to_memory("Test")
        self.assertFalse(success)
        self.mock_chroma_service.add_documents.assert_not_called() # Original mock shouldn't be called if service is None

    def test_retrieve_from_memory_success(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)

        mock_query_results = {
            "ids": [["id1", "id2"]],
            "documents": [["doc text 1", "doc text 2"]],
            "metadatas": [[{"s": "m1"}, {"s": "m2"}]],
            "distances": [[0.1, 0.2]]
        }
        self.mock_chroma_service.query_collection.return_value = mock_query_results

        query = "find related info"
        results = agent.retrieve_from_memory(query, collection_name="custom_coll", n_results=2)

        self.mock_chroma_service.query_collection.assert_called_once_with(
            collection_name="custom_coll",
            query_texts=[query],
            n_results=2,
            where_filter=None, # Default
            include=["documents", "metadatas", "distances", "ids"]
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["document"], "doc text 1")
        self.assertEqual(results[0]["metadata"], {"s": "m1"})
        self.assertEqual(results[0]["distance"], 0.1)
        self.assertEqual(results[0]["id"], "id1")

    def test_retrieve_from_memory_no_results(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)
        self.mock_chroma_service.query_collection.return_value = {"documents": [[]], "ids": [[]], "metadatas": [[]], "distances": [[]]} # Empty results for query

        results = agent.retrieve_from_memory("query for nothing")
        self.assertEqual(len(results), 0)

    def test_retrieve_from_memory_chroma_unavailable(self):
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=None)
        results = agent.retrieve_from_memory("Test")
        self.assertEqual(len(results), 0)
        self.mock_chroma_service.query_collection.assert_not_called()

    # --- Tests for Task Processing Methods ---

    @patch('agent_zero.agent.TaskListManager')
    def test_decompose_objective_into_tasks_success(self, MockTaskListManager):
        mock_tm_instance = MockTaskListManager.return_value
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)

        objective_prompt = "Create a new app."
        llm_generated_tasks_str = "Design UI\nDevelop backend\nWrite tests"
        self.mock_llm_client.generate.return_value = {"response": llm_generated_tasks_str, "done": True}

        # Mock add_objective and add_task on the TaskListManager instance
        mock_tm_instance.add_objective = MagicMock()
        mock_tm_instance.add_task = MagicMock()

        created_objective = agent.decompose_objective_into_tasks(objective_prompt, mock_tm_instance)

        self.assertIsNotNone(created_objective)
        self.assertEqual(created_objective.description, objective_prompt)
        # Objective status should become ACTIVE after successful decomposition with tasks
        self.assertEqual(created_objective.status, Status.ACTIVE)

        self.mock_llm_client.generate.assert_called_once()
        llm_call_args = self.mock_llm_client.generate.call_args[1]
        self.assertIn(objective_prompt, llm_call_args['prompt'])

        mock_tm_instance.add_objective.assert_called_once_with(created_objective)
        self.assertEqual(mock_tm_instance.add_task.call_count, 3)
        # Check one of the calls to add_task
        first_task_call_args = mock_tm_instance.add_task.call_args_list[0][0][0] # Gets the first Task object
        self.assertIsInstance(first_task_call_args, Task)
        self.assertEqual(first_task_call_args.description, "Design UI")
        self.assertEqual(first_task_call_args.objective_id, created_objective.id)


    @patch('agent_zero.agent.TaskListManager')
    def test_decompose_objective_llm_fails(self, MockTaskListManager):
        mock_tm_instance = MockTaskListManager.return_value
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)

        objective_prompt = "Another app."
        self.mock_llm_client.generate.return_value = {"error": "LLM is tired"}
        mock_tm_instance.add_objective = MagicMock() # Still need to mock this

        failed_objective = agent.decompose_objective_into_tasks(objective_prompt, mock_tm_instance)

        self.assertIsNotNone(failed_objective)
        self.assertEqual(failed_objective.status, Status.FAILED)
        self.assertIn("LLM is tired", failed_objective.result)
        mock_tm_instance.add_task.assert_not_called() # Should not add tasks if LLM fails

    @patch('agent_zero.agent.TaskListManager')
    def test_decompose_objective_llm_returns_empty_tasks(self, MockTaskListManager):
        mock_tm_instance = MockTaskListManager.return_value
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)

        objective_prompt = "Simple objective."
        self.mock_llm_client.generate.return_value = {"response": "  \n  ", "done": True} # Empty/whitespace tasks
        mock_tm_instance.add_objective = MagicMock()

        failed_objective = agent.decompose_objective_into_tasks(objective_prompt, mock_tm_instance)

        self.assertIsNotNone(failed_objective)
        self.assertEqual(failed_objective.status, Status.FAILED)
        self.assertIn("LLM returned no actionable tasks", failed_objective.result)
        mock_tm_instance.add_task.assert_not_called()


    @patch('agent_zero.agent.TaskListManager')
    def test_execute_task(self, MockTaskListManager):
        mock_tm_instance = MockTaskListManager.return_value
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)

        test_task = Task(description="Test this execution", objective_id="obj123", id="task_exec_test")

        # Mock update_task_status on the TaskListManager instance
        mock_tm_instance.update_task_status = MagicMock()

        agent.execute_task(test_task, mock_tm_instance)

        # Check that update_task_status was called to set ACTIVE, then COMPLETED
        self.assertEqual(mock_tm_instance.update_task_status.call_count, 2)

        # First call: set to ACTIVE
        active_call = mock_tm_instance.update_task_status.call_args_list[0]
        self.assertEqual(active_call.args[0], test_task.id)
        self.assertEqual(active_call.args[1], Status.ACTIVE)

        # Second call: set to COMPLETED with a result
        completed_call = mock_tm_instance.update_task_status.call_args_list[1]
        self.assertEqual(completed_call.args[0], test_task.id)
        self.assertEqual(completed_call.args[1], Status.COMPLETED)
        self.assertIn("Successfully completed task", completed_call.kwargs['result']) # Check result in kwargs

    @patch('agent_zero.agent.TaskListManager')
    def test_is_objective_complete(self, MockTaskListManager):
        mock_tm_instance = MockTaskListManager.return_value
        agent = Agent(config=self.config, llm_client=self.mock_llm_client, chroma_service=self.mock_chroma_service)

        obj_complete = Objective(description="Done", status=Status.COMPLETED, id="obj_done")
        obj_active = Objective(description="Doing", status=Status.ACTIVE, id="obj_doing")

        mock_tm_instance.get_objective.side_effect = lambda oid: obj_complete if oid == "obj_done" else (obj_active if oid == "obj_doing" else None)

        self.assertTrue(agent.is_objective_complete("obj_done", mock_tm_instance))
        self.assertFalse(agent.is_objective_complete("obj_doing", mock_tm_instance))
        self.assertFalse(agent.is_objective_complete("obj_nonexistent", mock_tm_instance))


if __name__ == '__main__':
    unittest.main()
