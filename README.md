# Labyrinth2D - A Code-Powered, Procedurally Generated Dungeon Builder

Labyrinth2D is a web-based simulator game where users build complex "machines" (dungeon elements, systems) from "scrap code" they collect or harvest. The game features a 2D top-down grid view (50x50 characters) and a low-bit pixel art style.

The core gameplay revolves around players using in-game Python code to:
*   Procedurally generate the grid maps of dungeon rooms.
*   Create automated scripts for entities within those rooms.
*   Harvest code from the environment and other machines.
*   Interact within a dynamic world with potential faction play and varied game modes.

An integrated RAG (Retrieval Augmented Generation) system guides players in crafting and understanding these scripts, fostering an "elegant experiential education process." A separate "Level Creator" allows users to chain multiple rooms into complex labyrinths.

## Design Document

The comprehensive design for Labyrinth2D can be found in [docs/Labyrinth2D_DESIGN.md](docs/Labyrinth2D_DESIGN.md).

## Project Status

*   **Phase 1 (Game & System Design):** Complete.
*   **Phase 2 (Core Game Loop & Basic Procedural Room Generation):** In Progress.

## Setup & Running (Placeholder - To be updated as implementation progresses)

This project is designed to be run using Docker.

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd Labyrinth2D
    ```
2.  **Build and run the Docker container:**
    ```bash
    docker-compose up --build
    ```
3.  Open your web browser and navigate to `http://localhost:8000` (or the configured port).

**Note:** Detailed setup instructions, dependencies, and configuration will be updated as the project advances.
