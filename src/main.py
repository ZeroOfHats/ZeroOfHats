from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # For SQLAlchemy 2.0 style select
from sqlalchemy.sql import func # For func.count
from pydantic import BaseModel # Not strictly needed for Form, but good for other models
import json
from fastapi import HTTPException # For 404 errors

from . import models
from .rag_parser import parse_rag_chunk, RAGInstructionError
from .instruction_executor import execute_instructions
from .database import engine, get_db, Base
from sqlalchemy import delete # Add this import


# Create tables on startup (for development only, use Alembic in production)
async def create_db_and_tables():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment to drop tables on each startup
        await conn.run_sync(Base.metadata.create_all)

app = FastAPI(title="RAG & Game State Manager API")

# Configure Jinja2Templates
templates = Jinja2Templates(directory="src/templates")

@app.on_event("startup")
async def startup_event():
    print("Application startup...")
    await create_db_and_tables()
    print("Database tables checked/created.")
    print("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    print("Application shutdown.")
    await engine.dispose()
    print("Database connection pool closed.")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: AsyncSession = Depends(get_db)):
    rag_result = await db.execute(select(func.count(models.RagChunk.id)))
    rag_chunk_count = rag_result.scalar_one_or_none()

    instance_result = await db.execute(select(func.count(models.GameInstance.id)))
    game_instance_count = instance_result.scalar_one_or_none()

    entity_def_result = await db.execute(select(func.count(models.EntityDefinition.id))) # New
    entity_definition_count = entity_def_result.scalar_one_or_none() # New

    return templates.TemplateResponse("home.html", {
        "request": request,
        "title": "Home",
        "rag_chunk_count": rag_chunk_count,
        "game_instance_count": game_instance_count,
        "entity_definition_count": entity_definition_count # New
    })

@app.get("/rag_chunks/add", response_class=HTMLResponse)
async def show_add_rag_chunk_form(request: Request):
    return templates.TemplateResponse("add_rag_chunk.html", {"request": request})

@app.post("/rag_chunks/add", response_class=RedirectResponse)
async def handle_add_rag_chunk(
    # Removed request: Request as it's not used here
    db: AsyncSession = Depends(get_db),
    chunk_content: str = Form(...),
    source_file: str = Form(None), # Using Form(None) for optional fields
    chunk_index: int = Form(None),
    metadata_json: str = Form(None)
):
    metadata_obj = None
    if metadata_json:
        try:
            metadata_obj = json.loads(metadata_json)
        except json.JSONDecodeError:
            # Basic error handling: log or pass an error message to the user
            # For now, invalid JSON means metadata will be None
            print(f"Warning: Could not parse metadata JSON: {metadata_json}")
            pass

    new_chunk = models.RagChunk(
        chunk_content=chunk_content,
        source_file=source_file,
        chunk_index=chunk_index,
        metadata=metadata_obj
        # embedding field is not handled in this form
    )
    db.add(new_chunk)
    await db.commit()
    await db.refresh(new_chunk)
    # Redirect to the list of chunks, using 303 "See Other" for POST-redirect-GET
    return RedirectResponse(url="/rag_chunks/", status_code=303)

@app.get("/rag_chunks/", response_class=HTMLResponse)
async def list_rag_chunks(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.RagChunk).order_by(models.RagChunk.id))
    chunks = result.scalars().all()
    return templates.TemplateResponse("list_rag_chunks.html", {"request": request, "chunks": chunks})

@app.get("/game_instances/add", response_class=HTMLResponse)
async def show_add_game_instance_form(request: Request):
    return templates.TemplateResponse("add_game_instance.html", {"request": request})

@app.post("/game_instances/add", response_class=RedirectResponse)
async def handle_add_game_instance(
    request: Request,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    current_state_json: str = Form(...),
    level_template_id: int = Form(None)
):
    current_state_obj = None
    try:
        current_state_obj = json.loads(current_state_json)
    except json.JSONDecodeError:
        return templates.TemplateResponse("add_game_instance.html", {
            "request": request,
            "error": "Invalid JSON format for Current State.",
            "name": name,
            "current_state_json": current_state_json,
            "level_template_id": level_template_id
        }, status_code=400)

    new_instance = models.GameInstance(
        name=name,
        current_state=current_state_obj,
        level_template_id=level_template_id
    )
    db.add(new_instance)
    await db.commit()
    await db.refresh(new_instance)
    return RedirectResponse(url="/game_instances/", status_code=303)

@app.get("/game_instances/", response_class=HTMLResponse)
async def list_game_instances(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.GameInstance).order_by(models.GameInstance.id))
    instances = result.scalars().all()
    return templates.TemplateResponse("list_game_instances.html", {"request": request, "instances": instances})

@app.post("/rag_chunks/{chunk_id}/process", response_class=HTMLResponse)
async def process_rag_chunk_instructions(
    request: Request,
    chunk_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Fetch the RAG chunk
    chunk_result = await db.execute(select(models.RagChunk).where(models.RagChunk.id == chunk_id))
    chunk = chunk_result.scalar_one_or_none()

    if not chunk:
        raise HTTPException(status_code=404, detail=f"RAG Chunk with ID {chunk_id} not found.")

    processing_results = []

    try:
        parsed_instructions = parse_rag_chunk(chunk.chunk_content)
        if not parsed_instructions:
            # Check if there was content but no instructions, vs empty content
            if not chunk.chunk_content.strip():
                 processing_results.append("Chunk content is empty. No instructions to process.")
            elif "%%% BEGIN_INSTRUCTION %%%" not in chunk.chunk_content:
                 processing_results.append("No instruction blocks (%%% BEGIN_INSTRUCTION %%%) found in chunk.")
            else:
                 processing_results.append("No valid RAG instructions parsed from the chunk. Check block format or for empty blocks.")
        else:
            # Call the instruction executor
            execution_statuses = await execute_instructions(db, parsed_instructions)
            processing_results.extend(execution_statuses)

    except RAGInstructionError as e:
        processing_results.append(f"Parser Error: {str(e)}")
    except Exception as e:
        # Catch any other unexpected errors during parsing or execution setup
        processing_results.append(f"An unexpected error occurred: {str(e)}")
        # Potentially log the full traceback here for debugging
        print(f"Unexpected error processing chunk {chunk_id}: {e.__class__.__name__} - {e}")
        import traceback
        traceback.print_exc()


    return templates.TemplateResponse("process_results.html", {
        "request": request,
        "chunk_id": chunk.id,
        "source_file": chunk.source_file,
        "results": processing_results
    })

@app.get("/entity_definitions/", response_class=HTMLResponse)
async def list_entity_definitions(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.EntityDefinition).order_by(models.EntityDefinition.id))
    entities = result.scalars().all()
    return templates.TemplateResponse("list_entity_definitions.html", {
        "request": request,
        "entities": entities
    })

@app.get("/rag_chunks/{chunk_id}/edit", response_class=HTMLResponse)
async def show_edit_rag_chunk_form(request: Request, chunk_id: int, db: AsyncSession = Depends(get_db)):
    chunk_result = await db.execute(select(models.RagChunk).where(models.RagChunk.id == chunk_id))
    chunk = chunk_result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail=f"RAG Chunk with ID {chunk_id} not found.")
    return templates.TemplateResponse("edit_rag_chunk.html", {"request": request, "chunk": chunk})

@app.post("/rag_chunks/{chunk_id}/edit", response_class=RedirectResponse)
async def handle_edit_rag_chunk(
    chunk_id: int,
    db: AsyncSession = Depends(get_db),
    # request: Request, # To return form with errors, if implemented
    chunk_content: str = Form(...),
    source_file: str = Form(None),
    chunk_index: int = Form(None),
    metadata_json: str = Form(None)
):
    chunk_result = await db.execute(select(models.RagChunk).where(models.RagChunk.id == chunk_id))
    chunk_to_update = chunk_result.scalar_one_or_none()
    if not chunk_to_update:
        raise HTTPException(status_code=404, detail=f"RAG Chunk with ID {chunk_id} not found to update.")

    chunk_to_update.chunk_content = chunk_content
    chunk_to_update.source_file = source_file
    # Handle potential empty string from form for integer field
    chunk_to_update.chunk_index = chunk_index if chunk_index is not None else None

    metadata_obj = None
    if metadata_json:
        try:
            metadata_obj = json.loads(metadata_json)
        except json.JSONDecodeError:
            # Basic error handling: Here, we'll let it be None if JSON is invalid.
            # A more robust solution would return to the form with an error message.
            # For example, by not redirecting and rendering edit_rag_chunk.html with an error.
            # This would require passing 'request' to this handler.
            print(f"Invalid JSON provided for metadata for chunk {chunk_id}. Storing as null/keeping old.")
            # To keep old value if new JSON is bad and old value exists:
            # metadata_obj = chunk_to_update.metadata
            pass
    chunk_to_update.metadata = metadata_obj

    await db.commit()
    await db.refresh(chunk_to_update)
    return RedirectResponse(url="/rag_chunks/", status_code=303)

@app.post("/rag_chunks/{chunk_id}/delete", response_class=RedirectResponse)
async def handle_delete_rag_chunk(chunk_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch the chunk to ensure it exists before attempting delete, for a clear 404
    chunk_result = await db.execute(select(models.RagChunk).where(models.RagChunk.id == chunk_id))
    chunk_to_delete = chunk_result.scalar_one_or_none()

    if not chunk_to_delete:
        raise HTTPException(status_code=404, detail=f"RAG Chunk with ID {chunk_id} not found to delete.")

    # Using the instance to delete
    await db.delete(chunk_to_delete)
    # Alternatively, can use a delete statement directly if not needing the instance:
    # await db.execute(delete(models.RagChunk).where(models.RagChunk.id == chunk_id))
    await db.commit()
    return RedirectResponse(url="/rag_chunks/", status_code=303)

@app.get("/game_instances/{instance_id}/edit", response_class=HTMLResponse)
async def show_edit_game_instance_form(request: Request, instance_id: int, db: AsyncSession = Depends(get_db)):
    instance_result = await db.execute(select(models.GameInstance).where(models.GameInstance.id == instance_id))
    instance = instance_result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=404, detail=f"Game Instance with ID {instance_id} not found.")
    return templates.TemplateResponse("edit_game_instance.html", {"request": request, "instance": instance})

@app.post("/game_instances/{instance_id}/edit", response_class=HTMLResponse) # Return HTMLResponse to show errors on form
async def handle_edit_game_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    current_state_json: str = Form(...),
    level_template_id: int = Form(None)
):
    instance_to_update_result = await db.execute(select(models.GameInstance).where(models.GameInstance.id == instance_id))
    instance_to_update = instance_to_update_result.scalar_one_or_none()

    if not instance_to_update:
        # This case should ideally not be reached if the user came from a valid link,
        # but good for robustness if ID is manually changed in URL.
        raise HTTPException(status_code=404, detail=f"Game Instance with ID {instance_id} not found to update.")

    current_state_obj = None
    try:
        current_state_obj = json.loads(current_state_json)
    except json.JSONDecodeError as e:
        # Return to form with error message and existing data
        # Create a dictionary that mimics the instance structure for the template
        form_data_for_template = {
            "id": instance_id,
            "name": name,
            "current_state": current_state_json, # Show the invalid JSON back to user
            "level_template_id": level_template_id if level_template_id is not None else ''
        }
        return templates.TemplateResponse("edit_game_instance.html", {
            "request": request,
            "instance": form_data_for_template,
            "error": f"Invalid JSON format for Current State: {e}"
        }, status_code=400)

    instance_to_update.name = name
    instance_to_update.current_state = current_state_obj
    instance_to_update.level_template_id = level_template_id # SQLAlchemy handles None correctly
    # The 'updated_at' field should update automatically due to onupdate=func.now() in the model

    await db.commit()
    await db.refresh(instance_to_update)
    # Successful update, redirect to list
    return RedirectResponse(url="/game_instances/", status_code=303)

@app.post("/game_instances/{instance_id}/delete", response_class=RedirectResponse)
async def handle_delete_game_instance(instance_id: int, db: AsyncSession = Depends(get_db)):
    instance_to_delete_result = await db.execute(select(models.GameInstance).where(models.GameInstance.id == instance_id))
    instance_to_delete = instance_to_delete_result.scalar_one_or_none()

    if not instance_to_delete:
        raise HTTPException(status_code=404, detail=f"Game Instance with ID {instance_id} not found to delete.")

    await db.delete(instance_to_delete)
    await db.commit()
    return RedirectResponse(url="/game_instances/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
