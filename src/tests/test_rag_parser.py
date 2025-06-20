import unittest
import sys
import os
import json # For expected values in tests

# Add src directory to Python path to import rag_parser
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_parser import parse_rag_chunk, RAGInstructionError

class TestRAGParser(unittest.TestCase):

    def test_empty_content(self):
        self.assertEqual(parse_rag_chunk(""), [])

    def test_no_instructions(self):
        content = "This is some normal text without any instructions."
        self.assertEqual(parse_rag_chunk(content), [])

    def test_single_simple_instruction(self):
        content = """
        Some text before.
        %%% BEGIN_INSTRUCTION %%%
        TYPE: SIMPLE_ACTION
        TARGET_ID: 123
        %%% END_INSTRUCTION %%%
        Some text after.
        """
        expected = [{"TYPE": "SIMPLE_ACTION", "TARGET_ID": "123"}]
        self.assertEqual(parse_rag_chunk(content), expected)

    def test_instruction_with_data_json(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        TYPE: CREATE_ENTITY
        NAME: Goblin
        DATA_JSON: {"hp": 10, "atk": 3, "abilities": ["charge", "bite"]}
        %%% END_INSTRUCTION %%%
        """
        expected = [{
            "TYPE": "CREATE_ENTITY",
            "NAME": "Goblin",
            "DATA_JSON": {"hp": 10, "atk": 3, "abilities": ["charge", "bite"]}
        }]
        self.assertEqual(parse_rag_chunk(content), expected)

    def test_instruction_with_multiline_data_json(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        TYPE: CREATE_ITEM
        NAME: Health Potion
        DATA_JSON: {
            "value": 50,
            "effect": "heal",
            "targets": ["player"]
        }
        %%% END_INSTRUCTION %%%
        """
        expected = [{
            "TYPE": "CREATE_ITEM",
            "NAME": "Health Potion",
            "DATA_JSON": {
                "value": 50,
                "effect": "heal",
                "targets": ["player"]
            }
        }]
        self.assertEqual(parse_rag_chunk(content), expected)


    def test_multiple_instructions(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        TYPE: INSTRUCTION_ONE
        DETAIL: First
        %%% END_INSTRUCTION %%%
        Some intermediate text.
        %%% BEGIN_INSTRUCTION %%%
        TYPE: INSTRUCTION_TWO
        DATA_JSON: {"key": "value"}
        %%% END_INSTRUCTION %%%
        """
        expected = [
            {"TYPE": "INSTRUCTION_ONE", "DETAIL": "First"},
            {"TYPE": "INSTRUCTION_TWO", "DATA_JSON": {"key": "value"}}
        ]
        self.assertEqual(parse_rag_chunk(content), expected)

    def test_malformed_json(self):
        # JSON with unquoted key 'abilities'
        content = """
        %%% BEGIN_INSTRUCTION %%%
        TYPE: BAD_JSON_TEST
        DATA_JSON: {"hp": 10, "atk": 3, abilities: ["charge", "bite"]}
        %%% END_INSTRUCTION %%%
        """
        with self.assertRaisesRegex(RAGInstructionError, "Malformed JSON in DATA_JSON.*BAD_JSON_TEST.*Content: '{.*abilities:.*}'"):
            parse_rag_chunk(content)

    def test_malformed_json_unterminated_string(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        TYPE: BAD_JSON_TEST_STR
        DATA_JSON: {"description": "This is an unterminated string}
        %%% END_INSTRUCTION %%%
        """
        with self.assertRaisesRegex(RAGInstructionError, "Malformed JSON in DATA_JSON.*BAD_JSON_TEST_STR"):
            parse_rag_chunk(content)


    def test_instruction_without_type(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        NAME: Missing Type Goblin
        DATA_JSON: {"hp": 5}
        %%% END_INSTRUCTION %%%
        """
        # Current implementation skips instructions without TYPE
        self.assertEqual(parse_rag_chunk(content), [])

    def test_instruction_block_is_empty(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        %%% END_INSTRUCTION %%%
        """
        self.assertEqual(parse_rag_chunk(content), [])

    def test_instruction_block_has_only_whitespace(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%

        %%% END_INSTRUCTION %%%
        """
        self.assertEqual(parse_rag_chunk(content), [])

    def test_keys_are_case_insensitive_and_normalized_to_upper(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        type: LowercaseKeyAction
        data_json: {"value": 1}
        another_key: testValue
        %%% END_INSTRUCTION %%%
        """
        # Keys are normalized to UPPERCASE
        expected = [{"TYPE": "LOWERCASEKEYACTION", "DATA_JSON": {"value": 1}, "ANOTHER_KEY": "testValue"}]
        self.assertEqual(parse_rag_chunk(content), expected)

    def test_mixed_content_and_instructions(self):
        content = """
        This is the first part of the RAG chunk.
        It contains some general information.

        %%% BEGIN_INSTRUCTION %%%
        TYPE: SETUP_LEVEL
        LEVEL_NAME: "The Dark Caves"
        DATA_JSON: {
            "size": "20x20",
            "monsters": ["goblin", "orc"],
            "boss": "Dragon"
        }
        %%% END_INSTRUCTION %%%

        Following the setup, we need to define entities.

        %%% BEGIN_INSTRUCTION %%%
        TYPE: DEFINE_MONSTER
        MONSTER_NAME: Goblin
        DATA_JSON: {"hp": 10, "attack": 2, "loot": ["gold", "dagger"]}
        %%% END_INSTRUCTION %%%

        This concludes the RAG chunk.
        """
        expected = [
            {
                "TYPE": "SETUP_LEVEL",
                "LEVEL_NAME": "\"The Dark Caves\"", # Value remains as is, including quotes if present
                "DATA_JSON": {
                    "size": "20x20",
                    "monsters": ["goblin", "orc"],
                    "boss": "Dragon"
                }
            },
            {
                "TYPE": "DEFINE_MONSTER",
                "MONSTER_NAME": "Goblin",
                "DATA_JSON": {"hp": 10, "attack": 2, "loot": ["gold", "dagger"]}
            }
        ]
        self.assertEqual(parse_rag_chunk(content), expected)

    def test_instruction_with_no_other_fields_than_type(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        TYPE: TRIGGER_EVENT_X
        %%% END_INSTRUCTION %%%
        """
        expected = [{"TYPE": "TRIGGER_EVENT_X"}]
        self.assertEqual(parse_rag_chunk(content), expected)

    def test_empty_data_json(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        TYPE: EMPTY_JSON
        DATA_JSON: {}
        %%% END_INSTRUCTION %%%
        """
        expected = [{"TYPE": "EMPTY_JSON", "DATA_JSON": {}}]
        self.assertEqual(parse_rag_chunk(content), expected)

    def test_data_json_with_various_types(self):
        content = """
        %%% BEGIN_INSTRUCTION %%%
        TYPE: COMPLEX_JSON
        DATA_JSON: {
            "string_val": "hello",
            "int_val": 123,
            "float_val": 45.67,
            "bool_true": true,
            "bool_false": false,
            "null_val": null,
            "array_val": [1, "two", 3.0, true]
        }
        %%% END_INSTRUCTION %%%
        """
        expected_json = {
            "string_val": "hello",
            "int_val": 123,
            "float_val": 45.67,
            "bool_true": True, # Python bool
            "bool_false": False, # Python bool
            "null_val": None, # Python None
            "array_val": [1, "two", 3.0, True]
        }
        expected = [{"TYPE": "COMPLEX_JSON", "DATA_JSON": expected_json}]
        self.assertEqual(parse_rag_chunk(content), expected)

if __name__ == '__main__':
    unittest.main()
