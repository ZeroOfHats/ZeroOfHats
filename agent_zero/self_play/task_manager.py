# agent_zero/self_play/task_manager.py
from typing import List, Optional
from .models import Task, Status # Relative import

class TaskListManager:
    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(self, task: Task):
        if not isinstance(task, Task):
            raise ValueError("Can only add Task objects to the task list.")
        self.tasks.append(task)
        print(f"Task added: {task.description[:50]}... (ID: {task.task_id})")

    def add_tasks(self, tasks: List[Task]):
        for task in tasks:
            self.add_task(task) # Use single add_task for validation

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_highest_priority_task(self) -> Optional[Task]:
        pending_tasks = [task for task in self.tasks if task.status == Status.PENDING]
        if not pending_tasks:
            return None

        # Sort by priority (descending) then by creation order (implicit by list stability)
        # Assuming higher number is higher priority.
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)
        return pending_tasks[0]

    def reprioritize_tasks(self, objective_description: Optional[str] = None):
        # Placeholder for reprioritization logic.
        # This could involve an LLM call or a defined heuristic.
        # For now, it does nothing but could be used to re-sort or adjust priorities.
        print(f"Task reprioritization requested. Objective: {objective_description[:50] if objective_description else 'N/A'}...")
        # Example: self.tasks.sort(key=lambda t: t.priority, reverse=True)
        pass

    def is_empty(self) -> bool:
        return not any(task.status == Status.PENDING for task in self.tasks)

    def get_all_tasks(self) -> List[Task]:
        return self.tasks

    def get_completed_tasks(self) -> List[Task]:
        return [task for task in self.tasks if task.status == Status.COMPLETED]
