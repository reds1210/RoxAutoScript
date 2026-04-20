from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.models import TaskSpec
from roxauto.core.queue import QueuedTask, TaskQueue


class TaskQueueTests(unittest.TestCase):
    @staticmethod
    def _spec(task_id: str) -> TaskSpec:
        return TaskSpec(
            task_id=task_id,
            name=task_id,
            version="0.1.0",
            entry_state="ready",
            steps=[],
        )

    def test_queue_prefers_higher_priority(self) -> None:
        queue = TaskQueue()
        low = QueuedTask(instance_id="mumu-0", spec=self._spec("low"), priority=10)
        high = QueuedTask(instance_id="mumu-0", spec=self._spec("high"), priority=200)

        queue.enqueue(low)
        queue.enqueue(high)

        dequeued = queue.dequeue()
        self.assertIsNotNone(dequeued)
        self.assertEqual(dequeued.task_id, "high")

    def test_queue_can_dequeue_per_instance(self) -> None:
        queue = TaskQueue()
        queue.extend(
            [
                QueuedTask(instance_id="mumu-0", spec=self._spec("task-a"), priority=100),
                QueuedTask(instance_id="mumu-1", spec=self._spec("task-b"), priority=100),
            ]
        )

        dequeued = queue.dequeue(instance_id="mumu-1")
        remaining = queue.list_items()

        self.assertIsNotNone(dequeued)
        self.assertEqual(dequeued.instance_id, "mumu-1")
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].instance_id, "mumu-0")
