import logging
from typing import Dict, List, Optional, Union
from agent_zero.self_play.models import Objective, Task, Status

logger = logging.getLogger(f"AgentZero.TaskListManager")

class TaskListManager:
    """
    Manages objectives and their associated tasks in memory.
    Provides functionalities to add, retrieve, and update objectives and tasks.
    """
    def __init__(self):
        self.objectives: Dict[str, Objective] = {}
        self.tasks: Dict[str, Task] = {} # All tasks, keyed by task_id
        logger.info("TaskListManager initialized.")

    # --- Objective Management ---
    def add_objective(self, objective: Objective) -> None:
        """Adds a new objective to the manager."""
        if not isinstance(objective, Objective):
            logger.error(f"Attempted to add non-Objective type: {type(objective)}")
            return
        if objective.id in self.objectives:
            logger.warning(f"Objective with ID {objective.id} already exists. Not adding again.")
            return
        self.objectives[objective.id] = objective
        logger.info(f"Objective added: {objective.id} - '{objective.description[:50]}...'")

    def get_objective(self, objective_id: str) -> Optional[Objective]:
        """Retrieves an objective by its ID."""
        return self.objectives.get(objective_id)

    def list_objectives(self, status: Optional[Status] = None) -> List[Objective]:
        """Lists objectives, optionally filtered by status."""
        if status:
            return [obj for obj in self.objectives.values() if obj.status == status]
        return list(self.objectives.values())

    def update_objective_status(self, objective_id: str, new_status: Status) -> bool:
        """Updates the status of an objective."""
        objective = self.get_objective(objective_id)
        if objective:
            objective.update_status(new_status)
            return True
        logger.warning(f"Objective {objective_id} not found for status update.")
        return False

    # --- Task Management ---
    def add_task(self, task: Task) -> None:
        """Adds a new task and associates it with its objective."""
        if not isinstance(task, Task):
            logger.error(f"Attempted to add non-Task type: {type(task)}")
            return
        if task.id in self.tasks:
            logger.warning(f"Task with ID {task.id} already exists. Not adding again.")
            return

        objective = self.get_objective(task.objective_id)
        if not objective:
            logger.error(f"Cannot add task {task.id}: Objective {task.objective_id} not found.")
            return

        self.tasks[task.id] = task
        if task.id not in objective.task_ids: # Ensure association
            objective.task_ids.append(task.id)
        logger.info(f"Task added: {task.id} for Objective {objective.id} - '{task.description[:50]}...'")

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieves a task by its ID."""
        return self.tasks.get(task_id)

    def get_tasks_for_objective(self, objective_id: str, status: Optional[Status] = None) -> List[Task]:
        """Retrieves all tasks associated with a given objective, optionally filtered by status."""
        objective = self.get_objective(objective_id)
        if not objective:
            logger.warning(f"Objective {objective_id} not found when trying to get its tasks.")
            return []

        relevant_tasks = [self.tasks[task_id] for task_id in objective.task_ids if task_id in self.tasks]
        if status:
            return [task for task in relevant_tasks if task.status == status]
        return relevant_tasks

    def update_task_status(self, task_id: str, new_status: Status, result: Optional[str] = None) -> bool:
        """Updates the status of a task and optionally its result."""
        task = self.get_task(task_id)
        if task:
            task.update_status(new_status)
            if result is not None:
                task.result = result

            # Always re-evaluate objective status if a task's status has been updated.
            # The task.update_status() method itself ensures it only logs/acts if the status is new.
            self._check_and_update_objective_status_from_tasks(task.objective_id)
            return True
        logger.warning(f"Task {task_id} not found for status update.")
        return False

    def _check_and_update_objective_status_from_tasks(self, objective_id: str):
        """
        Checks the status of all tasks for an objective and updates the objective's status accordingly.
        - If all tasks are COMPLETED, objective is COMPLETED.
        - If any task is FAILED, objective is FAILED (simple rule, could be more complex).
        - If any task is ACTIVE, objective is ACTIVE.
        - If all tasks are PENDING (or COMPLETED/CANCELLED but none ACTIVE/FAILED), objective is PENDING (or reflects completion).
        """
        objective = self.get_objective(objective_id)
        if not objective:
            return

        tasks_for_objective = self.get_tasks_for_objective(objective_id)
        if not tasks_for_objective: # No tasks for this objective
            if objective.status == Status.PENDING and not objective.task_ids:
                 # Objective was just created, has no tasks yet. It remains PENDING.
                pass
            elif objective.status != Status.COMPLETED and objective.status != Status.CANCELLED : # If it had tasks and now has none, and wasn't already terminal
                logger.info(f"Objective {objective_id} has no tasks. Setting to COMPLETED (or requires re-evaluation).")
                # This case is tricky. If tasks were deleted, or an objective has no tasks by design.
                # For now, let's assume an objective with no tasks that isn't already completed can be considered done.
                # A more robust system might require explicit objective completion.
                # objective.update_status(Status.COMPLETED) # Or perhaps it should be re-decomposed.
            return

        num_tasks = len(tasks_for_objective)
        completed_tasks = sum(1 for t in tasks_for_objective if t.status == Status.COMPLETED)
        failed_tasks = sum(1 for t in tasks_for_objective if t.status == Status.FAILED)
        cancelled_tasks = sum(1 for t in tasks_for_objective if t.status == Status.CANCELLED)
        active_tasks = sum(1 for t in tasks_for_objective if t.status == Status.ACTIVE)

        current_objective_status = objective.status

        if failed_tasks > 0 and current_objective_status not in [Status.FAILED, Status.CANCELLED]:
            logger.info(f"At least one task failed for Objective {objective_id}. Setting objective to FAILED.")
            objective.update_status(Status.FAILED)
        elif completed_tasks + cancelled_tasks == num_tasks and current_objective_status not in [Status.COMPLETED, Status.CANCELLED, Status.FAILED]:
            # All tasks are either completed or cancelled, none are pending/active/failed
            logger.info(f"All tasks for Objective {objective_id} are completed or cancelled. Setting objective to COMPLETED.")
            objective.update_status(Status.COMPLETED)
        elif active_tasks > 0 and current_objective_status == Status.PENDING :
            logger.info(f"Objective {objective_id} has active tasks. Setting objective to ACTIVE.")
            objective.update_status(Status.ACTIVE)
        # Other transitions (e.g. from ACTIVE to COMPLETED) are covered by the above.
        # If an objective is PAUSED, its tasks might also be PAUSED or PENDING. Manual intervention might be needed to resume.


    def get_highest_priority_task(self, objective_id: Optional[str] = None, status: Status = Status.PENDING) -> Optional[Task]:
        """
        Gets the highest priority task that is ready to be worked on (PENDING and dependencies met).
        If objective_id is provided, searches within that objective. Otherwise, searches across all objectives.

        Note: Dependency checking is simplified here. A full check would trace all dependencies.
              For now, it checks if tasks listed in `dependencies` are COMPLETED.
        """
        candidate_tasks: List[Task] = []
        if objective_id:
            tasks_to_check = self.get_tasks_for_objective(objective_id, status=status)
            candidate_tasks.extend(tasks_to_check)
        else: # Search across all PENDING tasks from any ACTIVE or PENDING objective
            active_or_pending_objectives = self.list_objectives(Status.ACTIVE) + self.list_objectives(Status.PENDING)
            for obj in active_or_pending_objectives:
                candidate_tasks.extend(self.get_tasks_for_objective(obj.id, status=status))

        if not candidate_tasks:
            return None

        # Filter by dependencies met
        ready_tasks = []
        for task in candidate_tasks:
            if not task.dependencies:
                ready_tasks.append(task)
            else:
                deps_met = True
                for dep_id in task.dependencies:
                    dep_task = self.get_task(dep_id)
                    if not dep_task or dep_task.status != Status.COMPLETED:
                        deps_met = False
                        break
                if deps_met:
                    ready_tasks.append(task)

        if not ready_tasks:
            return None

        # Sort by priority (higher number first), then by creation time (earlier first)
        ready_tasks.sort(key=lambda t: (t.priority, -t.created_at), reverse=True)

        logger.debug(f"Highest priority task found: {ready_tasks[0].id if ready_tasks else 'None'}")
        return ready_tasks[0] if ready_tasks else None

    def clear_all(self):
        """Clears all objectives and tasks. Useful for testing or reset."""
        self.objectives.clear()
        self.tasks.clear()
        logger.info("TaskListManager cleared all objectives and tasks.")


if __name__ == '__main__':
    from agent_zero.task_logger import setup_logging
    try:
        setup_logging()
    except Exception:
        logging.basicConfig(level=logging.DEBUG)
        logger.warning("Failed to use task_logger.setup_logging(). Using basicConfig for TaskListManager test.")

    logger.info("--- Testing TaskListManager ---")
    manager = TaskListManager()

    # 1. Objectives
    obj1 = Objective(description="Objective 1: Conquer the world")
    manager.add_objective(obj1)
    assert manager.get_objective(obj1.id) == obj1
    assert len(manager.list_objectives()) == 1

    manager.update_objective_status(obj1.id, Status.ACTIVE)
    assert obj1.status == Status.ACTIVE

    # 2. Tasks
    task1_obj1 = Task(description="Task 1.1: Research world leaders", objective_id=obj1.id, priority=10)
    manager.add_task(task1_obj1)
    assert manager.get_task(task1_obj1.id) == task1_obj1
    assert task1_obj1.id in obj1.task_ids
    assert len(manager.get_tasks_for_objective(obj1.id)) == 1

    # Objective should become active if a task is added and it was PENDING (or if task becomes active)
    # Current logic in _check_and_update_objective_status_from_tasks updates obj to ACTIVE if a task becomes ACTIVE
    # Adding a PENDING task to a PENDING objective doesn't change objective status by itself.

    task2_obj1 = Task(description="Task 1.2: Acquire funding", objective_id=obj1.id, priority=20)
    manager.add_task(task2_obj1)
    assert len(manager.get_tasks_for_objective(obj1.id)) == 2

    # 3. Highest Priority Task
    # Both tasks are PENDING, task2 has higher priority
    hp_task = manager.get_highest_priority_task(objective_id=obj1.id)
    assert hp_task is not None
    assert hp_task.id == task2_obj1.id
    logger.info(f"Highest priority task for {obj1.id}: {hp_task.id} - '{hp_task.description}'")

    # Update task status and see objective status change
    manager.update_task_status(task2_obj1.id, Status.ACTIVE) # Task 2 becomes active
    assert task2_obj1.status == Status.ACTIVE
    # Objective obj1 should now be ACTIVE (if it wasn't already from manual update)
    # The _check_and_update is triggered by task status change.
    assert obj1.status == Status.ACTIVE, f"Objective status was {obj1.status}, expected ACTIVE"


    manager.update_task_status(task2_obj1.id, Status.COMPLETED, result="Funding acquired!")
    assert task2_obj1.status == Status.COMPLETED
    logger.info(f"Task {task2_obj1.id} completed.")

    # Now task1 should be highest priority
    hp_task = manager.get_highest_priority_task(objective_id=obj1.id)
    assert hp_task is not None
    assert hp_task.id == task1_obj1.id
    logger.info(f"Next highest priority task for {obj1.id}: {hp_task.id} - '{hp_task.description}'")

    manager.update_task_status(task1_obj1.id, Status.COMPLETED, result="Leaders researched.")
    assert task1_obj1.status == Status.COMPLETED
    logger.info(f"Task {task1_obj1.id} completed.")

    # Objective should now be COMPLETED
    assert obj1.status == Status.COMPLETED, f"Objective status was {obj1.status}, expected COMPLETED"
    logger.info(f"Objective {obj1.id} status: {obj1.status}")

    # 4. Task with Dependencies
    obj2 = Objective(description="Objective 2: Bake a Cake")
    manager.add_objective(obj2)

    task_A_obj2 = Task(description="Task A: Buy ingredients", objective_id=obj2.id, priority=10)
    manager.add_task(task_A_obj2)
    task_B_obj2 = Task(description="Task B: Mix ingredients", objective_id=obj2.id, priority=5, dependencies=[task_A_obj2.id])
    manager.add_task(task_B_obj2)
    task_C_obj2 = Task(description="Task C: Bake cake", objective_id=obj2.id, priority=1, dependencies=[task_B_obj2.id])
    manager.add_task(task_C_obj2)

    # Initially, only Task A should be available (no dependencies)
    hp_task_obj2 = manager.get_highest_priority_task(objective_id=obj2.id)
    assert hp_task_obj2 is not None
    assert hp_task_obj2.id == task_A_obj2.id
    logger.info(f"Highest priority for {obj2.id} (deps): {hp_task_obj2.id}")

    manager.update_task_status(task_A_obj2.id, Status.COMPLETED)
    # Now Task B should be available
    hp_task_obj2 = manager.get_highest_priority_task(objective_id=obj2.id)
    assert hp_task_obj2 is not None
    assert hp_task_obj2.id == task_B_obj2.id
    logger.info(f"Next highest priority for {obj2.id} (deps): {hp_task_obj2.id}")

    manager.update_task_status(task_B_obj2.id, Status.FAILED, result="Ran out of eggs mid-mix.")
    assert obj2.status == Status.FAILED # Objective should fail if a task fails
    logger.info(f"Objective {obj2.id} status after task failure: {obj2.status}")

    # Task C should not become highest priority as its dependency B failed (and objective is failed)
    # get_highest_priority_task only looks for PENDING tasks. If B failed, C remains PENDING.
    # And if obj2 is FAILED, get_highest_priority_task might not even consider its tasks if it only checks ACTIVE/PENDING objectives.
    # Current implementation of get_highest_priority_task checks PENDING tasks from ACTIVE or PENDING objectives.
    # So, if obj2 is FAILED, its tasks won't be considered by get_highest_priority_task(objective_id=None).
    # If we query specifically for obj2 (even if FAILED), it would still list task_C as PENDING.
    # Let's test get_highest_priority_task for obj2:
    hp_task_obj2_after_fail = manager.get_highest_priority_task(objective_id=obj2.id)
    assert hp_task_obj2_after_fail is not None # Task C is still PENDING
    assert hp_task_obj2_after_fail.id == task_C_obj2.id # Its dependency B is not COMPLETED. So C is not ready.
                                                      # Ah, the test logic for ready_tasks was:
                                                      # if not dep_task or dep_task.status != Status.COMPLETED:
                                                      # So if B is FAILED, C is not ready.
    # Thus, after B fails, there are no "ready" PENDING tasks for obj2.
    assert manager.get_highest_priority_task(objective_id=obj2.id) is None, "No ready tasks expected after dependency failed."


    manager.clear_all()
    assert len(manager.objectives) == 0
    assert len(manager.tasks) == 0
    logger.info("Cleared all tasks and objectives.")

    logger.info("--- TaskListManager Test Completed ---")
