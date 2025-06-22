import unittest
import time
import sys
import os

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agent_zero.self_play.models import Objective, Task, Status
from agent_zero.self_play.task_manager import TaskListManager

class TestTaskListManager(unittest.TestCase):

    def setUp(self):
        self.manager = TaskListManager()
        # Create some initial objectives and tasks for reuse in tests
        self.obj1 = Objective(description="Objective 1")
        self.manager.add_objective(self.obj1)

        self.task1_obj1 = Task(description="Task 1.1 for Obj1", objective_id=self.obj1.id, priority=10)
        self.manager.add_task(self.task1_obj1)

        self.task2_obj1 = Task(description="Task 1.2 for Obj1", objective_id=self.obj1.id, priority=5)
        self.manager.add_task(self.task2_obj1)

        self.obj2 = Objective(description="Objective 2")
        self.manager.add_objective(self.obj2)
        # obj2 has no tasks initially

    def test_add_and_get_objective(self):
        self.assertEqual(self.manager.get_objective(self.obj1.id), self.obj1)
        self.assertIsNone(self.manager.get_objective("non_existent_obj_id"))

    def test_list_objectives(self):
        objectives = self.manager.list_objectives()
        self.assertEqual(len(objectives), 2)
        self.assertIn(self.obj1, objectives)
        self.assertIn(self.obj2, objectives)

        self.obj1.update_status(Status.ACTIVE) # manager.update_objective_status also works
        active_objectives = self.manager.list_objectives(status=Status.ACTIVE)
        self.assertEqual(len(active_objectives), 1)
        self.assertEqual(active_objectives[0], self.obj1)

        pending_objectives = self.manager.list_objectives(status=Status.PENDING)
        self.assertEqual(len(pending_objectives), 1)
        self.assertEqual(pending_objectives[0], self.obj2)


    def test_update_objective_status(self):
        self.manager.update_objective_status(self.obj1.id, Status.COMPLETED)
        self.assertEqual(self.obj1.status, Status.COMPLETED)
        self.assertFalse(self.manager.update_objective_status("non_existent_obj", Status.ACTIVE))

    def test_add_and_get_task(self):
        self.assertEqual(self.manager.get_task(self.task1_obj1.id), self.task1_obj1)
        self.assertIsNone(self.manager.get_task("non_existent_task_id"))
        # Ensure task is associated with objective
        self.assertIn(self.task1_obj1.id, self.obj1.task_ids)

    def test_add_task_to_non_existent_objective(self):
        task_bad_obj = Task(description="Task for bad obj", objective_id="bad_obj_id")
        # Current behavior: logs error, doesn't add. Check tasks dict not modified.
        initial_task_count = len(self.manager.tasks)
        self.manager.add_task(task_bad_obj)
        self.assertEqual(len(self.manager.tasks), initial_task_count)


    def test_get_tasks_for_objective(self):
        tasks_obj1 = self.manager.get_tasks_for_objective(self.obj1.id)
        self.assertEqual(len(tasks_obj1), 2)
        self.assertIn(self.task1_obj1, tasks_obj1)
        self.assertIn(self.task2_obj1, tasks_obj1)

        self.task1_obj1.update_status(Status.ACTIVE)
        active_tasks_obj1 = self.manager.get_tasks_for_objective(self.obj1.id, status=Status.ACTIVE)
        self.assertEqual(len(active_tasks_obj1), 1)
        self.assertEqual(active_tasks_obj1[0], self.task1_obj1)

        self.assertEqual(self.manager.get_tasks_for_objective("non_existent_obj"), [])

    def test_update_task_status(self):
        self.manager.update_task_status(self.task1_obj1.id, Status.COMPLETED, result="Done by test")
        self.assertEqual(self.task1_obj1.status, Status.COMPLETED)
        self.assertEqual(self.task1_obj1.result, "Done by test")
        self.assertFalse(self.manager.update_task_status("non_existent_task", Status.ACTIVE))

    def test_objective_status_updates_based_on_tasks(self):
        # Obj1 is PENDING (default), Task1 and Task2 are PENDING
        self.assertEqual(self.obj1.status, Status.PENDING)

        # Make one task ACTIVE -> Objective should become ACTIVE
        self.manager.update_task_status(self.task1_obj1.id, Status.ACTIVE)
        self.assertEqual(self.obj1.status, Status.ACTIVE)

        # Complete Task1
        self.manager.update_task_status(self.task1_obj1.id, Status.COMPLETED)
        self.assertEqual(self.obj1.status, Status.ACTIVE) # Still active as Task2 is PENDING

        # Complete Task2 -> Objective should become COMPLETED
        self.manager.update_task_status(self.task2_obj1.id, Status.COMPLETED)
        self.assertEqual(self.obj1.status, Status.COMPLETED)

        # Test FAILED state propagation
        self.manager.update_objective_status(self.obj2.id, Status.ACTIVE) # Start obj2
        task1_obj2 = Task(description="T1 for Obj2", objective_id=self.obj2.id)
        self.manager.add_task(task1_obj2)
        task2_obj2 = Task(description="T2 for Obj2", objective_id=self.obj2.id)
        self.manager.add_task(task2_obj2)

        self.manager.update_task_status(task1_obj2.id, Status.COMPLETED)
        self.manager.update_task_status(task2_obj2.id, Status.FAILED)
        self.assertEqual(self.obj2.status, Status.FAILED)


    def test_get_highest_priority_task_no_deps(self):
        # task1_obj1 (prio 10), task2_obj1 (prio 5) - both PENDING
        hp_task = self.manager.get_highest_priority_task(objective_id=self.obj1.id)
        self.assertEqual(hp_task, self.task1_obj1) # Higher priority number is better

        # Test across all objectives (obj2 has no PENDING tasks yet)
        hp_task_all = self.manager.get_highest_priority_task()
        self.assertEqual(hp_task_all, self.task1_obj1)


    def test_get_highest_priority_task_with_deps(self):
        dep_task = Task(description="Dependency Task", objective_id=self.obj2.id, priority=100)
        self.manager.add_task(dep_task)

        main_task = Task(description="Main Task with Dep", objective_id=self.obj2.id, priority=50, dependencies=[dep_task.id])
        self.manager.add_task(main_task)

        # Initially, dep_task should be highest priority as main_task depends on it
        hp_task = self.manager.get_highest_priority_task(objective_id=self.obj2.id)
        self.assertEqual(hp_task, dep_task)

        # Complete dep_task
        self.manager.update_task_status(dep_task.id, Status.COMPLETED)

        # Now, main_task should be highest priority
        hp_task = self.manager.get_highest_priority_task(objective_id=self.obj2.id)
        self.assertEqual(hp_task, main_task)

    def test_get_highest_priority_task_dep_not_met(self):
        dep_task_not_done = Task(description="Dep Not Done", objective_id=self.obj2.id, priority=100)
        self.manager.add_task(dep_task_not_done)

        main_task_waiting = Task(description="Waiting Task", objective_id=self.obj2.id, priority=50, dependencies=[dep_task_not_done.id])
        self.manager.add_task(main_task_waiting)

        # dep_task_not_done is PENDING, so main_task_waiting is not ready
        # hp_task should be dep_task_not_done
        hp_task = self.manager.get_highest_priority_task(objective_id=self.obj2.id)
        self.assertEqual(hp_task, dep_task_not_done)

        # If dep_task_not_done is FAILED
        self.manager.update_task_status(dep_task_not_done.id, Status.FAILED)
        # main_task_waiting should still not be chosen as its dependency is not COMPLETED
        hp_task_after_fail = self.manager.get_highest_priority_task(objective_id=self.obj2.id)
        self.assertIsNone(hp_task_after_fail, "No ready task expected if dependency failed.")

    def test_get_highest_priority_task_tie_break_by_creation_time(self):
        # Tasks with same priority, earlier created should come first
        # Note: default_factory for created_at uses time.time()
        # To ensure different creation times for testing, we add them sequentially with a small delay

        task_early = Task(description="Early Task", objective_id=self.obj2.id, priority=7)
        self.manager.add_task(task_early)
        time.sleep(0.01) # Ensure time difference
        task_late = Task(description="Late Task", objective_id=self.obj2.id, priority=7)
        self.manager.add_task(task_late)

        # task_early.created_at should be less than task_late.created_at
        # Sorting key is (priority, -created_at), reverse=True means higher prio first.
        # For same prio, higher -created_at (so lower created_at) comes first.
        hp_task = self.manager.get_highest_priority_task(objective_id=self.obj2.id)
        self.assertEqual(hp_task, task_early)


    def test_clear_all(self):
        self.manager.clear_all()
        self.assertEqual(len(self.manager.objectives), 0)
        self.assertEqual(len(self.manager.tasks), 0)

if __name__ == '__main__':
    unittest.main()
