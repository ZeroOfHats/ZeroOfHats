# Using a specific version of ChromaDB for consistency
FROM chromadb/chroma:0.4.22

# Default Chroma port is 8000
EXPOSE 8000

# The default command for the chromadb/chroma image is to run the server.
# We can specify it explicitly if needed, or add persistence arguments.
# For basic persistent storage, the volume mount in docker-compose.yml is key.
# CMD ["uvicorn", "chromadb.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-config", "chromadb/log_config.yml", "--timeout-keep-alive", "30"]
# The above CMD is often the default. Relying on the base image's default CMD is fine.
# For persistence, ensure the data path used by ChromaDB inside the container is mounted.
# The default path is /chroma/.chroma (or similar, check ChromaDB docs for the version).
# The docker-compose.yml mounts to /chroma_data, so ChromaDB would need to be configured
# to use this path if its default isn't already covered or configurable via environment variables.

# For the chromadb/chroma image, it's often configured to persist to a path specified by
# the `CHROMA_SERVER_PERSIST_PATH` environment variable, or defaults to `./chroma-data` if not set.
# Let's set it to the path we are mounting as a volume.
ENV CHROMA_SERVER_PERSIST_PATH /chroma_data
CMD ["uvicorn", "chromadb.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-config", "/usr/local/lib/python3.11/site-packages/chromadb/log_config.yml"]

# Note: The exact CMD and ENV VAR for persistence path can vary slightly between ChromaDB versions.
# It's good practice to check the documentation for the specific ChromaDB version being used.
# The chromadb/chroma:0.4.22 image should use something like the above.
