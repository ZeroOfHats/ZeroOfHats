import re
import json

class RAGInstructionError(Exception):
    """Custom exception for RAG instruction parsing errors."""
    pass

def parse_rag_chunk(chunk_content: str) -> list[dict]:
    """
    Parses RAG chunk content to extract structured instructions.

    Instruction format:
    %%% BEGIN_INSTRUCTION %%%
    TYPE: <INSTRUCTION_TYPE>
    KEY1: VALUE1
    KEY2: VALUE2
    DATA_JSON: {"json_key": "json_value"}
    %%% END_INSTRUCTION %%%

    Returns:
        A list of parsed instruction dictionaries. Each dictionary contains
        parsed key-value pairs, with DATA_JSON parsed into a sub-dictionary.
    Raises:
        RAGInstructionError: If DATA_JSON is malformed.
    """
    if not chunk_content:
        return []

    instructions = []
    # Regex to find instruction blocks
    # re.DOTALL (via (?s) in some regex flavors, or flag in Python) makes . match newlines
    pattern = re.compile(r"%%% BEGIN_INSTRUCTION %%%(?P<block_content>.+?)%%% END_INSTRUCTION %%%", re.DOTALL)

    for match in pattern.finditer(chunk_content):
        block_content = match.group("block_content").strip()
        if not block_content:
            continue

        parsed_instruction = {}
        data_json_str = None
        # Handles multiline values for DATA_JSON by finding its start and concatenating if needed
        # However, simpler line-by-line parsing is used below, assuming DATA_JSON is on one line or handled by JSON structure

        lines = block_content.splitlines()

        # Temp storage for multi-line DATA_JSON (if we were to support it that way)
        # current_key_for_multiline = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if ":" not in line:
                # If we were supporting multi-line values for keys other than DATA_JSON, logic would go here.
                # For now, lines without colons are ignored or could be logged.
                # Example: if current_key_for_multiline and current_key_for_multiline != "DATA_JSON":
                #    parsed_instruction[current_key_for_multiline] += " " + line
                continue

            key, value = line.split(":", 1)
            key = key.strip().upper() # Normalize key
            value = value.strip()

            if key == "DATA_JSON":
                # If DATA_JSON is found, we assume its value might be multi-line if it starts with { or [
                # and subsequent lines are part of it until it forms valid JSON.
                # For simplicity here, we assume the JSON string itself is correctly formatted on one or more lines
                # and json.loads will handle it if the string is valid.
                # A more robust parser might concatenate lines if a value starts with { or [ and doesn't end with } or ].
                data_json_str = value
                # If value is just '{' or '[', then subsequent lines should be appended to data_json_str
                # This simple version assumes json.loads can handle newlines within the string values if the JSON is structured that way.
            else:
                parsed_instruction[key] = value
                # current_key_for_multiline = key # For general multiline support

        if "TYPE" not in parsed_instruction:
            # Or raise RAGInstructionError("Instruction TYPE missing")
            # For now, skipping blocks without a TYPE
            # print(f"Skipping instruction block due to missing TYPE: {block_content[:100]}")
            continue

        if data_json_str:
            try:
                # Attempt to parse the accumulated DATA_JSON string
                parsed_instruction["DATA_JSON"] = json.loads(data_json_str)
            except json.JSONDecodeError as e:
                error_message = (
                    f"Malformed JSON in DATA_JSON for instruction type "
                    f"{parsed_instruction.get('TYPE', 'Unknown')}: {e}. "
                    f"Content: '{data_json_str[:200]}...'" # Log snippet of problematic JSON
                )
                raise RAGInstructionError(error_message)

        instructions.append(parsed_instruction)

    return instructions
