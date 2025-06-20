import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from instruction_executor import execute_instructions, _handle_create_entity, _handle_create_level_template
from sqlalchemy.exc import IntegrityError # For simulating DB errors

# Since models are used like `models.EntityDefinition`, we need to mock them where `instruction_executor` can find them.
# This typically means patching them in the module where they are *used*.
MODULE_PATH = 'instruction_executor.models'

class TestInstructionExecutor(unittest.IsolatedAsyncioTestCase):

    async def test_execute_no_instructions_empty_list_returned(self):
        mock_db_session = AsyncMock()
        results = await execute_instructions(mock_db_session, [])
        self.assertEqual(results, []) # Expecting an empty list now

    async def test_execute_instruction_missing_type(self):
        mock_db_session = AsyncMock()
        instructions = [{"DATA_JSON": {}}] # TYPE is missing
        results = await execute_instructions(mock_db_session, instructions)
        self.assertIn("Error: Instruction TYPE missing", results[0])

    async def test_execute_unknown_instruction_type(self):
        mock_db_session = AsyncMock()
        instructions = [{"TYPE": "UNKNOWN_TYPE", "DATA_JSON": {}}]
        results = await execute_instructions(mock_db_session, instructions)
        self.assertIn("Error: Unknown or unsupported instruction type.", results[0])

    @patch(f'{MODULE_PATH}.EntityDefinition')
    async def test_handle_create_entity_success(self, MockEntityDefinition):
        mock_db_session = AsyncMock()
        # Configure the mock instance returned by EntityDefinition()
        mock_entity_instance = MockEntityDefinition.return_value
        mock_entity_instance.name = "Test Goblin" # Simulate attributes set on the model instance
        mock_entity_instance.id = 1

        instruction = {
            "TYPE": "CREATE_ENTITY",
            "DATA_JSON": {
                "name": "Test Goblin",
                "type": "monster",
                "default_properties": {"hp": 10},
                "description": "A small goblin."
            }
        }
        result = await _handle_create_entity(mock_db_session, instruction)

        MockEntityDefinition.assert_called_once_with(
            name="Test Goblin",
            type="monster",
            default_properties={"hp": 10},
            description="A small goblin."
        )
        mock_db_session.add.assert_called_once_with(mock_entity_instance)
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(mock_entity_instance)
        self.assertIn("Success: Created EntityDefinition 'Test Goblin' (ID: 1).", result)

    async def test_handle_create_entity_missing_data_json(self):
        mock_db_session = AsyncMock()
        instruction = {"TYPE": "CREATE_ENTITY"} # No DATA_JSON
        result = await _handle_create_entity(mock_db_session, instruction)
        self.assertEqual(result, "Error: DATA_JSON is missing or not a dictionary for CREATE_ENTITY.")
        mock_db_session.add.assert_not_called()

    async def test_handle_create_entity_missing_required_fields(self):
        mock_db_session = AsyncMock()
        instruction = {
            "TYPE": "CREATE_ENTITY",
            "DATA_JSON": {"name": "Test Only Name"} # Missing type, default_properties
        }
        result = await _handle_create_entity(mock_db_session, instruction)
        self.assertIn("Error: Missing required fields in DATA_JSON for CREATE_ENTITY: default_properties, type", result)
        mock_db_session.add.assert_not_called()

    async def test_handle_create_entity_empty_name(self):
        mock_db_session = AsyncMock()
        instruction = {
            "TYPE": "CREATE_ENTITY",
            "DATA_JSON": {"name": "", "type": "monster", "default_properties": {}}
        }
        result = await _handle_create_entity(mock_db_session, instruction)
        self.assertEqual(result, "Error: Field 'name' must be a non-empty string for CREATE_ENTITY.")

    async def test_handle_create_entity_invalid_default_properties(self):
        mock_db_session = AsyncMock()
        instruction = {
            "TYPE": "CREATE_ENTITY",
            "DATA_JSON": {"name": "Goblin", "type": "monster", "default_properties": "not_a_dict"}
        }
        result = await _handle_create_entity(mock_db_session, instruction)
        self.assertEqual(result, "Error: Field 'default_properties' must be a JSON object for CREATE_ENTITY.")

    @patch(f'{MODULE_PATH}.EntityDefinition')
    async def test_handle_create_entity_integrity_error(self, MockEntityDefinition):
        mock_db_session = AsyncMock()
        mock_db_session.commit.side_effect = IntegrityError("Mocked IntegrityError", params={}, orig=MagicMock(pgcode="23505")) # Simulate unique constraint

        instruction = {
            "TYPE": "CREATE_ENTITY",
            "DATA_JSON": {"name": "Existing Goblin", "type": "monster", "default_properties": {"hp": 5}}
        }
        result = await _handle_create_entity(mock_db_session, instruction)
        self.assertIn("Error: Could not create EntityDefinition 'Existing Goblin'. The name already exists", result)
        mock_db_session.rollback.assert_called_once()

    @patch(f'{MODULE_PATH}.LevelTemplate')
    async def test_handle_create_level_template_success(self, MockLevelTemplate):
        mock_db_session = AsyncMock()
        mock_lt_instance = MockLevelTemplate.return_value
        mock_lt_instance.name = "Test Forest"
        mock_lt_instance.id = 1

        instruction = {
            "TYPE": "CREATE_LEVEL_TEMPLATE",
            "DATA_JSON": {
                "name": "Test Forest",
                "structure": {"size": "10x10"},
                "description": "A lush forest."
            }
        }
        result = await _handle_create_level_template(mock_db_session, instruction)

        MockLevelTemplate.assert_called_once_with(
            name="Test Forest",
            structure={"size": "10x10"},
            description="A lush forest.",
            default_entities=None # As it's optional and not provided
        )
        mock_db_session.add.assert_called_once_with(mock_lt_instance)
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(mock_lt_instance)
        self.assertIn("Success: Created LevelTemplate 'Test Forest' (ID: 1).", result)

    async def test_handle_create_level_template_missing_data_json(self):
        mock_db_session = AsyncMock()
        instruction = {"TYPE": "CREATE_LEVEL_TEMPLATE"}
        result = await _handle_create_level_template(mock_db_session, instruction)
        self.assertEqual(result, "Error: DATA_JSON is missing or not a dictionary for CREATE_LEVEL_TEMPLATE.")

    async def test_handle_create_level_template_missing_required_fields(self):
        mock_db_session = AsyncMock()
        instruction = {
            "TYPE": "CREATE_LEVEL_TEMPLATE",
            "DATA_JSON": {"name": "Test Only Name"} # Missing structure
        }
        result = await _handle_create_level_template(mock_db_session, instruction)
        self.assertIn("Error: Missing required fields in DATA_JSON for CREATE_LEVEL_TEMPLATE: structure", result)

    @patch('instruction_executor._handle_create_entity')
    @patch('instruction_executor._handle_create_level_template')
    async def test_execute_instructions_dispatch(self, mock_handle_lt, mock_handle_entity):
        mock_db_session = AsyncMock()
        # Configure return values for the mocked handlers
        mock_handle_entity.return_value = "Success: Created EntityDefinition 'e1' (ID: 1)."
        mock_handle_lt.return_value = "Success: Created LevelTemplate 'lt1' (ID: 1)."

        instructions = [
            {"TYPE": "CREATE_ENTITY", "DATA_JSON": {"name": "e1", "type": "t1", "default_properties": {}}},
            {"TYPE": "CREATE_LEVEL_TEMPLATE", "DATA_JSON": {"name": "lt1", "structure": {}}},
            {"TYPE": "UNKNOWN_TYPE"}
        ]

        results = await execute_instructions(mock_db_session, instructions)

        # Check that the respective handlers were called with the correct arguments
        mock_handle_entity.assert_called_once_with(mock_db_session, instructions[0])
        mock_handle_lt.assert_called_once_with(mock_db_session, instructions[1])

        # Check that the results from the handlers are included in the final results list
        self.assertIn("Instruction TYPE 'CREATE_ENTITY': Success: Created EntityDefinition 'e1' (ID: 1).", results[0])
        self.assertIn("Instruction TYPE 'CREATE_LEVEL_TEMPLATE': Success: Created LevelTemplate 'lt1' (ID: 1).", results[1])
        self.assertIn("Instruction TYPE 'UNKNOWN_TYPE': Error: Unknown or unsupported instruction type.", results[2])

if __name__ == '__main__':
    unittest.main()
