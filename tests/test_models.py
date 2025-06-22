import unittest
import time
import sys
import os

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agent_zero.self_play.models import Status, Objective, Task

class TestModels(unittest.TestCase):

    def test_status_enum(self):
        self.assertEqual(Status.PENDING.name, "PENDING")
        self.assertEqual(str(Status.ACTIVE), "ACTIVE")
        self.assertIsInstance(Status.COMPLETED, Status)
        # Check all expected statuses exist
        expected_statuses = ["PENDING", "ACTIVE", "COMPLETED", "FAILED", "PAUSED", "CANCELLED"]
        for s_name in expected_statuses:
            self.assertTrue(hasattr(Status, s_name))

    def test_objective_creation_defaults(self):
        desc = "Test objective default values"
        obj = Objective(description=desc)
        self.assertEqual(obj.description, desc)
        self.assertTrue(obj.id.startswith("obj_"))
        self.assertEqual(obj.status, Status.PENDING)
        self.assertEqual(obj.task_ids, [])
        self.assertAlmostEqual(obj.created_at, time.time(), delta=0.1)
        self.assertAlmostEqual(obj.updated_at, time.time(), delta=0.1)

    def test_objective_creation_custom(self):
        desc = "Custom Objective"
        obj_id = "custom_obj_123"
        obj_status = Status.ACTIVE
        task_ids = ["task_abc", "task_def"]

        obj = Objective(description=desc, id=obj_id, status=obj_status, task_ids=task_ids)
        self.assertEqual(obj.description, desc)
        self.assertEqual(obj.id, obj_id)
        self.assertEqual(obj.status, Status.ACTIVE)
        self.assertEqual(obj.task_ids, task_ids)

    def test_objective_update_status(self):
        obj = Objective(description="Status update test")
        original_updated_at = obj.updated_at
        time.sleep(0.01) # Ensure time difference
        obj.update_status(Status.COMPLETED)
        self.assertEqual(obj.status, Status.COMPLETED)
        self.assertGreater(obj.updated_at, original_updated_at)

        # Test updating with same status (should not change updated_at significantly)
        current_updated_at = obj.updated_at
        obj.update_status(Status.COMPLETED) # Update to same status
        self.assertEqual(obj.status, Status.COMPLETED)
        self.assertAlmostEqual(obj.updated_at, current_updated_at, delta=0.001) # Should be very close

    def test_objective_invalid_status_at_init(self):
        # __post_init__ handles string status that maps to Enum name
        obj_str_status = Objective(description="Str status", status="ACTIVE")
        self.assertEqual(obj_str_status.status, Status.ACTIVE)

        # __post_init__ handles invalid string status by defaulting to PENDING
        obj_invalid_str = Objective(description="Invalid str status", status="NON_EXISTENT_STATUS")
        self.assertEqual(obj_invalid_str.status, Status.PENDING)

        # __post_init__ also handles if completely wrong type is passed (though type hints should prevent this)
        obj_wrong_type = Objective(description="Wrong type status", status=123)
        self.assertEqual(obj_wrong_type.status, Status.PENDING)


    def test_task_creation_defaults(self):
        desc = "Test task default values"
        obj_id = "obj_for_task_defaults"
        task = Task(description=desc, objective_id=obj_id)

        self.assertEqual(task.description, desc)
        self.assertEqual(task.objective_id, obj_id)
        self.assertTrue(task.id.startswith("task_"))
        self.assertEqual(task.status, Status.PENDING)
        self.assertEqual(task.priority, 0)
        self.assertEqual(task.dependencies, [])
        self.assertIsNone(task.result)
        self.assertAlmostEqual(task.created_at, time.time(), delta=0.1)
        self.assertAlmostEqual(task.updated_at, time.time(), delta=0.1)

    def test_task_creation_custom(self):
        desc = "Custom Task"
        obj_id = "obj_for_custom_task"
        task_id = "custom_task_456"
        task_status = Status.ACTIVE
        priority = 100
        dependencies = ["task_dep1", "task_dep2"]
        result = "Initial partial result"

        task = Task(
            description=desc, objective_id=obj_id, id=task_id, status=task_status,
            priority=priority, dependencies=dependencies, result=result
        )
        self.assertEqual(task.description, desc)
        self.assertEqual(task.objective_id, obj_id)
        self.assertEqual(task.id, task_id)
        self.assertEqual(task.status, Status.ACTIVE)
        self.assertEqual(task.priority, priority)
        self.assertEqual(task.dependencies, dependencies)
        self.assertEqual(task.result, result)

    def test_task_update_status(self):
        task = Task(description="Task status update", objective_id="obj_task_status")
        original_updated_at = task.updated_at
        time.sleep(0.01) # Ensure time difference

        task.update_status(Status.FAILED)
        self.assertEqual(task.status, Status.FAILED)
        self.assertGreater(task.updated_at, original_updated_at)

        current_updated_at = task.updated_at
        task.update_status(Status.FAILED) # Update to same status
        self.assertEqual(task.status, Status.FAILED)
        self.assertAlmostEqual(task.updated_at, current_updated_at, delta=0.001)


    def test_task_invalid_status_at_init(self):
        task_str_status = Task(description="Str status task", objective_id="obj_x", status="COMPLETED")
        self.assertEqual(task_str_status.status, Status.COMPLETED)

        task_invalid_str = Task(description="Invalid str status task", objective_id="obj_y", status="NON_EXISTENT_TASK_STATUS")
        self.assertEqual(task_invalid_str.status, Status.PENDING)

        task_wrong_type = Task(description="Wrong type status task", objective_id="obj_z", status=None) # None is not a Status
        self.assertEqual(task_wrong_type.status, Status.PENDING)


if __name__ == '__main__':
    unittest.main()
