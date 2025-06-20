from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime # Removed JSON as it's not used directly
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class RagChunk(Base):
    __tablename__ = "rag_chunks"
    id = Column(Integer, primary_key=True, index=True)
    chunk_content = Column(Text, nullable=False)
    source_file = Column(String)
    chunk_index = Column(Integer)
    metadata = Column(JSONB)
    # Using ARRAY(String) as a placeholder for NUMERIC[] or VECTOR.
    # For actual numeric arrays or pgvector, a custom type or a library like sqlalchemy-pgvector would be better.
    embedding = Column(ARRAY(String))

class LevelTemplate(Base):
    __tablename__ = "level_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    structure = Column(JSONB, nullable=False)
    default_entities = Column(JSONB)

    game_instances = relationship("GameInstance", back_populates="level_template")

class EntityDefinition(Base):
    __tablename__ = "entity_definitions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    type = Column(String, nullable=False) # e.g., 'monster', 'item', 'player_character', 'trap'
    default_properties = Column(JSONB, nullable=False) # e.g., { "stats": {"hp": 10, "atk": 3}, "sprite": "goblin.png", "abilities": [] }
    description = Column(Text)

class GameInstance(Base):
    __tablename__ = "game_instances"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    level_template_id = Column(Integer, ForeignKey("level_templates.id"), nullable=True) # Can be NULL if not based on a template
    current_state = Column(JSONB, nullable=False) # e.g., { "player_location": {"x":1, "y":2}, "active_entities": [...]}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    level_template = relationship("LevelTemplate", back_populates="game_instances")
