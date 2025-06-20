from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import json

from . import models
from .rag_parser import RAGInstructionError # For consistency, though not directly used for raising here

# Define expected structures for DATA_JSON for different types
EXPECTED_ENTITY_FIELDS = {"name", "type", "default_properties"}
EXPECTED_LEVEL_TEMPLATE_FIELDS = {"name", "structure"}


async def _handle_create_entity(db: AsyncSession, instruction_data: dict) -> str:
    data_json = instruction_data.get("DATA_JSON")
    if not isinstance(data_json, dict):
        return "Error: DATA_JSON is missing or not a dictionary for CREATE_ENTITY."

    # Validate required fields
    missing_fields = EXPECTED_ENTITY_FIELDS - data_json.keys()
    if missing_fields:
        return f"Error: Missing required fields in DATA_JSON for CREATE_ENTITY: {', '.join(sorted(list(missing_fields)))}."

    try:
        # Ensure required fields are not just present but also have meaningful content if necessary
        # For example, name and type should not be empty strings.
        if not data_json.get("name") or not isinstance(data_json.get("name"), str):
            return "Error: Field 'name' must be a non-empty string for CREATE_ENTITY."
        if not data_json.get("type") or not isinstance(data_json.get("type"), str):
            return "Error: Field 'type' must be a non-empty string for CREATE_ENTITY."
        if not isinstance(data_json.get("default_properties"), dict): # Must be a dict for JSONB
             return "Error: Field 'default_properties' must be a JSON object for CREATE_ENTITY."


        entity = models.EntityDefinition(
            name=str(data_json["name"]),
            type=str(data_json["type"]),
            default_properties=data_json["default_properties"],
            description=data_json.get("description") # Optional
        )
        db.add(entity)
        await db.commit()
        await db.refresh(entity)
        return f"Success: Created EntityDefinition '{entity.name}' (ID: {entity.id})."
    except IntegrityError as e:
        await db.rollback()
        # Attempt to provide a more user-friendly message for unique constraint violations
        if "unique constraint" in str(e.orig).lower() or "duplicate key" in str(e.orig).lower():
             return f"Error: Could not create EntityDefinition '{data_json.get('name')}'. The name already exists or another unique field conflicts. Details: {e.orig}"
        return f"Error: Database integrity error for EntityDefinition '{data_json.get('name')}'. Details: {e.orig}"
    except Exception as e:
        await db.rollback()
        return f"Error: An unexpected error occurred while creating EntityDefinition '{data_json.get('name')}': {type(e).__name__} - {e}"


async def _handle_create_level_template(db: AsyncSession, instruction_data: dict) -> str:
    data_json = instruction_data.get("DATA_JSON")
    if not isinstance(data_json, dict):
        return "Error: DATA_JSON is missing or not a dictionary for CREATE_LEVEL_TEMPLATE."

    missing_fields = EXPECTED_LEVEL_TEMPLATE_FIELDS - data_json.keys()
    if missing_fields:
        return f"Error: Missing required fields in DATA_JSON for CREATE_LEVEL_TEMPLATE: {', '.join(sorted(list(missing_fields)))}."

    try:
        if not data_json.get("name") or not isinstance(data_json.get("name"), str):
            return "Error: Field 'name' must be a non-empty string for CREATE_LEVEL_TEMPLATE."
        if not isinstance(data_json.get("structure"), dict): # Must be a dict for JSONB
             return "Error: Field 'structure' must be a JSON object for CREATE_LEVEL_TEMPLATE."
        if data_json.get("default_entities") is not None and not isinstance(data_json.get("default_entities"), dict):
             return "Error: Optional field 'default_entities' must be a JSON object if provided for CREATE_LEVEL_TEMPLATE."


        level_template = models.LevelTemplate(
            name=str(data_json["name"]),
            structure=data_json["structure"],
            description=data_json.get("description"), # Optional
            default_entities=data_json.get("default_entities") # Optional
        )
        db.add(level_template)
        await db.commit()
        await db.refresh(level_template)
        return f"Success: Created LevelTemplate '{level_template.name}' (ID: {level_template.id})."
    except IntegrityError as e:
        await db.rollback()
        if "unique constraint" in str(e.orig).lower() or "duplicate key" in str(e.orig).lower():
             return f"Error: Could not create LevelTemplate '{data_json.get('name')}'. The name already exists or another unique field conflicts. Details: {e.orig}"
        return f"Error: Database integrity error for LevelTemplate '{data_json.get('name')}'. Details: {e.orig}"
    except Exception as e:
        await db.rollback()
        return f"Error: An unexpected error occurred while creating LevelTemplate '{data_json.get('name')}': {type(e).__name__} - {e}"


async def execute_instructions(db: AsyncSession, parsed_instructions: list[dict]) -> list[str]:
    """
    Executes a list of parsed RAG instructions.
    Returns a list of status messages for each instruction.
    """
    results = []
    if not parsed_instructions:
        # This case might be handled before calling if it's considered an error or empty state
        # results.append("No instructions found to execute.")
        return results # Return empty list if no instructions

    for instruction in parsed_instructions:
        instruction_type = instruction.get("TYPE")
        # It's good practice to have a default message or log if a handler doesn't return one
        result_message = f"Instruction TYPE '{instruction_type}': "

        if not instruction_type:
            result_message += "Error: Instruction TYPE missing in parsed data."
        elif instruction_type == "CREATE_ENTITY":
            result_message += await _handle_create_entity(db, instruction)
        elif instruction_type == "CREATE_LEVEL_TEMPLATE":
            result_message += await _handle_create_level_template(db, instruction)
        # Add more handlers here for other instruction types
        # elif instruction_type == "UPDATE_ENTITY":
        #     result_message += await _handle_update_entity(db, instruction)
        # elif instruction_type == "CREATE_GAME_INSTANCE": # Example for a new type
        #     result_message += await _handle_create_game_instance(db, instruction)
        else:
            result_message += "Error: Unknown or unsupported instruction type."

        results.append(result_message)

    return results
