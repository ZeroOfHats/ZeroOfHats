import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Any
import time
import uuid # For generating unique IDs

logger = logging.getLogger(f"AgentZero.Models")

class Status(Enum):
    """
    Represents the status of an Objective or a Task.
    """
    PENDING = auto()    # Not yet started
    ACTIVE = auto()     # Currently in progress or selected for work
    COMPLETED = auto()  # Successfully finished
    FAILED = auto()     # Attempted but could not be completed successfully
    PAUSED = auto()     # Temporarily suspended
    CANCELLED = auto()  # Intentionally stopped before completion

    def __str__(self):
        return self.name

@dataclass
class Objective:
    """
    Represents a high-level objective or goal for the agent.
    """
    description: str
    id: str = field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:8]}")
    status: Status = Status.PENDING
    task_ids: List[str] = field(default_factory=list) # List of Task IDs associated with this objective
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    # result: Optional[Any] = None # Optional field to store the outcome or result of the objective
    # metadata: Dict[str, Any] = field(default_factory=dict) # For any other relevant info

    def __post_init__(self):
        if not isinstance(self.status, Status):
            try:
                self.status = Status[str(self.status).upper()]
            except (KeyError, AttributeError):
                logger.warning(f"Invalid status '{self.status}' for Objective {self.id}. Defaulting to PENDING.")
                self.status = Status.PENDING
        logger.debug(f"Objective initialized: {self.id} - '{self.description[:50]}...' ({self.status})")

    def update_status(self, new_status: Status):
        if not isinstance(new_status, Status):
            logger.error(f"Attempted to update Objective {self.id} with invalid status type: {type(new_status)}")
            return
        if self.status != new_status:
            logger.info(f"Task {self.id} status changing from {self.status} to {new_status}") # Corrected from Objective to Task
            self.status = new_status
            self.updated_at = time.time()
        else:
            logger.debug(f"Objective {self.id} status already {new_status}. No change.")

@dataclass
class Task:
    """
    Represents an individual task that is part of an Objective.
    """
    description: str
    objective_id: str # ID of the parent Objective
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    status: Status = Status.PENDING
    priority: int = 0  # Higher number means higher priority
    dependencies: List[str] = field(default_factory=list) # List of Task IDs this task depends on
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: Optional[Any] = None # To store the outcome of the task
    # sub_tasks: List['Task'] = field(default_factory=list) # For hierarchical tasks, if needed later
    # metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.status, Status):
            try:
                self.status = Status[str(self.status).upper()]
            except (KeyError, AttributeError):
                logger.warning(f"Invalid status '{self.status}' for Task {self.id}. Defaulting to PENDING.")
                self.status = Status.PENDING
        logger.debug(f"Task initialized: {self.id} for Objective {self.objective_id} - '{self.description[:50]}...' ({self.status})")

    def update_status(self, new_status: Status):
        if not isinstance(new_status, Status):
            logger.error(f"Attempted to update Task {self.id} with invalid status type: {type(new_status)}")
            return
        if self.status != new_status:
            logger.info(f"Objective {self.id} status changing from {self.status} to {new_status}")
            self.status = new_status
            self.updated_at = time.time()
        else:
            logger.debug(f"Task {self.id} status already {new_status}. No change.")


if __name__ == '__main__':
    from agent_zero.task_logger import setup_logging # Assuming this sets up root logger

    try:
        # Basic logging setup for __main__ execution
        # If task_logger.setup_logging() is not available or fails, use basicConfig
        setup_logging()
    except Exception:
        logging.basicConfig(level=logging.DEBUG)
        logger.warning("Failed to use task_logger.setup_logging(). Using basicConfig for models.py test.")

    logger.info("--- Testing Data Models ---")

    # Test Status Enum
    logger.info(f"Available statuses: {[s.name for s in Status]}")
    assert Status.PENDING.name == "PENDING"
    assert str(Status.ACTIVE) == "ACTIVE"

    # Test Objective Creation
    obj1_desc = "Develop a comprehensive marketing strategy for Q4."
    obj1 = Objective(description=obj1_desc)
    logger.info(f"Created Objective: ID={obj1.id}, Desc='{obj1.description}', Status={obj1.status}, Tasks={obj1.task_ids}")
    assert obj1.description == obj1_desc
    assert obj1.status == Status.PENDING
    assert isinstance(obj1.id, str) and obj1.id.startswith("obj_")
    assert isinstance(obj1.task_ids, list) and not obj1.task_ids # Empty list by default

    obj1.update_status(Status.ACTIVE)
    assert obj1.status == Status.ACTIVE
    logger.info(f"Objective {obj1.id} status updated to {obj1.status}")

    # Test Objective with non-enum status at init (should default)
    obj_invalid_status = Objective(description="Test invalid status", status="NONEXISTENT")
    assert obj_invalid_status.status == Status.PENDING
    logger.info(f"Objective with invalid init status defaulted to: {obj_invalid_status.status}")


    # Test Task Creation
    task1_desc = "Conduct market research and competitor analysis."
    task1 = Task(description=task1_desc, objective_id=obj1.id, priority=10)
    obj1.task_ids.append(task1.id) # Manually associate for this test

    logger.info(f"Created Task: ID={task1.id}, ObjID={task1.objective_id}, Desc='{task1.description}', Status={task1.status}, Prio={task1.priority}")
    assert task1.description == task1_desc
    assert task1.objective_id == obj1.id
    assert task1.status == Status.PENDING
    assert task1.priority == 10
    assert isinstance(task1.id, str) and task1.id.startswith("task_")
    assert isinstance(task1.dependencies, list) and not task1.dependencies

    task1.update_status(Status.ACTIVE)
    assert task1.status == Status.ACTIVE
    logger.info(f"Task {task1.id} status updated to {task1.status}")

    task1.result = "Market research summary document generated."
    task1.update_status(Status.COMPLETED)
    assert task1.status == Status.COMPLETED
    assert task1.result == "Market research summary document generated."
    logger.info(f"Task {task1.id} completed with result: {task1.result}")

    task2_desc = "Draft initial marketing copy based on research."
    task2 = Task(description=task2_desc, objective_id=obj1.id, priority=5, dependencies=[task1.id])
    obj1.task_ids.append(task2.id)
    logger.info(f"Created Task 2: ID={task2.id} with dependency on {task1.id}")
    assert task2.dependencies == [task1.id]

    logger.info("--- Data Models Test Completed ---")
