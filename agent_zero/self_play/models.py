# agent_zero/self_play/models.py
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Any, Optional

class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DEFERRED = "deferred"
    REQUIRES_INTERVENTION = "requires_intervention"

@dataclass
class Objective:
    description: str
    initial_prompt: str
    objective_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: Status = Status.ACTIVE
    # tasks: List['Task'] = field(default_factory=list) # Removed to enforce TaskListManager as single source of truth. Tasks have objective_id.

@dataclass
class Task:
    description: str
    objective_id: str # Parent objective
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: Status = Status.PENDING
    priority: int = 1 # Higher number = higher priority
    result: Optional[Any] = None
    dependencies: List[str] = field(default_factory=list) # List of task_ids
    sub_tasks: List['Task'] = field(default_factory=list) # Child tasks
    created_by_agent_id: Optional[str] = None
    assigned_to_agent_id: Optional[str] = None

    def __lt__(self, other): # For priority queue if needed, or sorting
        return self.priority < other.priority
