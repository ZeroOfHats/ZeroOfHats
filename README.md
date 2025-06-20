# RAG-Guided PostgreSQL State Management Web UI

This project is a Dockerized web-based user interface that interacts with a PostgreSQL database to manage:
- Specific chunks of RAG files (text content and metadata).
- Complex state data for a Labyrinth Builder game.

The system allows the web UI to "follow instructions" derived from specific RAG chunks to automate or guide the storage and structuring of this complex state data within PostgreSQL.

### Key Features
*   **Web-based UI**: Manage RAG Chunks and Game State data (Game Instances, Entity Definitions) through an intuitive web interface.
*   **CRUD Operations**: Full Create, Read, Update, Delete functionality for RAG Chunks and Game Instances. View functionality for Entity Definitions.
*   **RAG-Guided Data Management**: Process structured instructions embedded within RAG chunk text to automatically create game entities, level templates, and other game state data. See the [User Guide](docs/user_guide.md#rag-guided-instructions) and [Instruction Format](docs/rag_instruction_format.md) for details.
*   **Dockerized Setup**: Easy to set up and run using Docker and Docker Compose.
*   **PostgreSQL Database**: Utilizes a robust PostgreSQL database for data storage.
*   **Alembic Migrations**: Database schema changes managed with Alembic (for developers).

## Current Status

Currently in **Phase 2: Core Web UI & PostgreSQL Integration**. The focus is on setting up the basic Dockerized application, database schema, and initial UI for manual data entry.

## Running the Application

This application is fully Dockerized and uses `docker-compose` to manage services.

### Prerequisites

*   Docker: [Install Docker](https://docs.docker.com/get-docker/)
*   Docker Compose: Usually included with Docker Desktop. If not, [Install Docker Compose](https://docs.docker.com/compose/install/)

### Setup & Execution

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Environment Variables (Optional for default setup):**
    The application uses default credentials for PostgreSQL (`user:password`) and connects to `appdb` on the `postgres` service. These are defined in `docker-compose.yml`.
    If you need to customize these, you can create a `.env` file in the root directory and override the `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` variables. The `src/config.py` also looks for a `.env` file for `DATABASE_URL` if you wish to run the Python app outside Docker for development, but for Dockerized setup, `docker-compose.yml` settings are primary.

3.  **Build and run the services:**
    From the project root directory (where `docker-compose.yml` is located), run:
    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Forces Docker to rebuild the images if there are changes (e.g., in `Dockerfile` or application code).
    *   `-d`: Runs the containers in detached mode (in the background).

4.  **Accessing the Web UI:**
    Once the containers are up and running, the web application should be accessible at:
    [http://localhost:8000](http://localhost:8000)

5.  **Accessing the Database (Optional):**
    You can connect to the PostgreSQL database directly if needed:
    *   **Service name:** `postgres`
    *   **Port (on host):** `5432`
    *   **Username:** `user` (or as configured)
    *   **Password:** `password` (or as configured)
    *   **Database name:** `appdb` (or as configured)

    You can use a tool like `psql` via `docker exec`:
    ```bash
    docker-compose exec postgres psql -U user -d appdb
    # (Enter 'password' when prompted if psql requires it, though often not for local trust)
    ```

6.  **Viewing Logs:**
    To view the logs from the running containers:
    ```bash
    docker-compose logs -f
    # Or for a specific service:
    # docker-compose logs -f web
    # docker-compose logs -f postgres
    ```

7.  **Stopping the Application:**
    To stop the running services:
    ```bash
    docker-compose down
    ```
    *   This will stop and remove the containers.
    *   To also remove the named volume (`postgres_data`) and delete all database data, use:
        ```bash
        docker-compose down -v
        ```
        **Caution:** This is destructive to your database data.

### Alembic Migrations (For Developers)

If you make changes to the SQLAlchemy models in `src/models.py`, you'll need to generate a new database migration script using Alembic.

1.  **Ensure the `postgres` service is running:**
    ```bash
    docker-compose up -d postgres
    ```

2.  **Generate a new revision (run from within the `web` service container, or a local venv with access to models and Alembic):**
    To run from the `web` container:
    ```bash
    docker-compose exec web alembic revision -m "your_migration_message"
    ```
    This will create a new file in `src/migrations/versions/`. Review and edit this file as needed.

3.  **Apply the migrations:**
    Alembic migrations are not automatically applied by the current `startup_event` in `main.py` (which uses `Base.metadata.create_all` for dev convenience). For a production-like flow or to test migrations:
    ```bash
    docker-compose exec web alembic upgrade head
    ```
    Alternatively, the `Base.metadata.create_all` in `startup_event` will create tables if they don't exist, but won't handle alterations. For robust schema management, rely on Alembic.
