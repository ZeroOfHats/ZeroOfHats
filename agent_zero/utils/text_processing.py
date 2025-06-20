# agent_zero/utils/text_processing.py
import re
from typing import List

def clean_text(text: str) -> str:
    """
    Basic text cleaning:
    - Replaces multiple newlines with a single newline.
    - Removes leading/trailing whitespace from the whole text and from each line.
    - (Future: could add more specific cleaning rules, e.g., for unicode normalization or removing specific patterns)
    """
    if not text:
        return ""

    # Replace multiple newlines with a single one
    text = re.sub(r'\n+', '\n', text)

    # Strip whitespace from each line and rejoin, then strip whole text
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(filter(None, lines)) # Filter out empty lines that might result from stripping

    return text.strip()

def split_text_into_chunks(
    text: str,
    chunk_size: int = 512, # Approximate target size in characters (Ollama models often use token limits)
    chunk_overlap: int = 50, # Number of characters to overlap between chunks
    strategy: str = "character" # "character", "paragraph", "sentence" (sentence not implemented yet)
) -> List[str]:
    """
    Splits text into chunks.

    Args:
        text (str): The input text.
        chunk_size (int): The target size for each chunk (in characters for 'character' strategy).
        chunk_overlap (int): The overlap between chunks (in characters for 'character' strategy).
        strategy (str): Method for chunking ('character', 'paragraph').
                        'sentence' strategy is a TODO.

    Returns:
        List[str]: A list of text chunks.
    """
    if not text:
        return []

    cleaned_text = clean_text(text)
    if not cleaned_text:
        return []

    chunks: List[str] = []

    if strategy == "character":
        start_index = 0
        while start_index < len(cleaned_text):
            end_index = min(start_index + chunk_size, len(cleaned_text))
            chunks.append(cleaned_text[start_index:end_index])
            if end_index == len(cleaned_text):
                break
            start_index += (chunk_size - chunk_overlap)
            # Ensure start_index doesn't go negative if overlap is too large (edge case)
            if start_index < 0: start_index = 0


    elif strategy == "paragraph":
        # Split by one or more newlines (paragraphs)
        paragraphs = [p.strip() for p in cleaned_text.splitlines() if p.strip()]
        current_chunk = ""
        for para_idx, paragraph in enumerate(paragraphs):
            if not paragraph: continue

            if len(current_chunk) + len(paragraph) + (1 if current_chunk else 0) <= chunk_size:
                if current_chunk:
                    current_chunk += "\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                # Chunk is full, or paragraph itself is too large
                if current_chunk: # Add the chunk we've been building
                    chunks.append(current_chunk)

                # If the paragraph itself is larger than chunk_size, split it by character strategy
                if len(paragraph) > chunk_size:
                    print(f"Warning: Paragraph starting with '{paragraph[:50]}...' is larger than chunk_size. Splitting it by character.")
                    # Use character splitting for this oversized paragraph
                    # Ensure overlap is smaller than chunk_size to avoid infinite loops on tiny chunk_size
                    effective_overlap = min(chunk_overlap, chunk_size -1) if chunk_size > 0 else 0

                    para_chunks = split_text_into_chunks(paragraph, chunk_size, effective_overlap, strategy="character")
                    chunks.extend(para_chunks)
                    current_chunk = "" # Reset current_chunk as the large para is handled
                else:
                    current_chunk = paragraph # Start new chunk with current paragraph

        if current_chunk: # Add any remaining chunk
            chunks.append(current_chunk)

    # TODO: Implement "sentence" strategy using nltk or similar if more granularity is needed.
    # elif strategy == "sentence":
    #     try:
    #         import nltk
    #         nltk.download('punkt', quiet=True) # Ensure sentence tokenizer is available
    #         sentences = nltk.sent_tokenize(cleaned_text)
    #         # Then combine sentences into chunks respecting chunk_size and overlap
    #     except ImportError:
    #         print("NLTK not installed. Cannot use 'sentence' chunking strategy. Falling back to 'paragraph'.")
    #         return split_text_into_chunks(cleaned_text, chunk_size, chunk_overlap, strategy="paragraph")

    else:
        print(f"Warning: Unknown chunking strategy '{strategy}'. Defaulting to character split.")
        return split_text_into_chunks(cleaned_text, chunk_size, chunk_overlap, strategy="character")

    # Filter out any empty chunks that might have been created
    return [chunk for chunk in chunks if chunk.strip()]


if __name__ == '__main__':
    sample_text_long = """
    This is the first paragraph. It contains several sentences. We are testing the chunking mechanism.
    This is the second paragraph. It's a bit shorter.
    And a third one, very brief.
    A much longer fourth paragraph follows. This one is designed to be potentially larger than the chunk size, especially if the chunk size is small. We will see how the paragraph strategy handles it. It should ideally split this long paragraph using the character-based sub-splitting if it exceeds the defined character limit for a paragraph-based chunk. This ensures that no single chunk becomes excessively large due to a very long paragraph. The goal is to maintain manageable pieces of text for subsequent processing, such as embedding generation or language model context windows.
    Fifth paragraph. Back to normal length.
    """

    print("--- Testing clean_text ---")
    dirty_text = "  Line one.  \n\n  Line two. \n\n\n Line three with trailing spaces.   "
    cleaned = clean_text(dirty_text)
    print(f"Original: '{dirty_text}'")
    print(f"Cleaned: '{cleaned}'")
    assert cleaned == "Line one.\nLine two.\nLine three with trailing spaces."

    print("\n--- Testing character chunking ---")
    char_chunks = split_text_into_chunks(sample_text_long, chunk_size=100, chunk_overlap=20, strategy="character")
    for i, chunk in enumerate(char_chunks):
        print(f"Chunk {i+1} (len {len(chunk)}): '{chunk[:80]}...'")

    print("\n--- Testing paragraph chunking (small chunk_size to test splitting of large paragraph) ---")
    para_chunks_small_limit = split_text_into_chunks(sample_text_long, chunk_size=150, chunk_overlap=30, strategy="paragraph")
    for i, chunk in enumerate(para_chunks_small_limit):
        print(f"Chunk {i+1} (len {len(chunk)}):\n'{chunk}'\n---")

    print("\n--- Testing paragraph chunking (larger chunk_size) ---")
    para_chunks_large_limit = split_text_into_chunks(sample_text_long, chunk_size=500, chunk_overlap=50, strategy="paragraph")
    for i, chunk in enumerate(para_chunks_large_limit):
        print(f"Chunk {i+1} (len {len(chunk)}):\n'{chunk}'\n---")

    # Test case for a paragraph that is itself larger than the chunk size
    single_very_long_paragraph = "This is a single extremely long paragraph that definitely exceeds a small chunk size like 100 characters. It keeps going and going, on and on, because we need to test the logic that splits oversized paragraphs using the character-based method, ensuring that the system doesn't create chunks that are too big for downstream processes like embedding or LLM context windows. The overlap should also be respected in these sub-splits. Testing this thoroughly is important for robustness."
    print("\n--- Testing paragraph chunking with a single oversized paragraph ---")
    oversized_para_chunks = split_text_into_chunks(single_very_long_paragraph, chunk_size=100, chunk_overlap=20, strategy="paragraph")
    for i, chunk in enumerate(oversized_para_chunks):
        print(f"Chunk {i+1} (len {len(chunk)}): '{chunk[:80]}...'")
