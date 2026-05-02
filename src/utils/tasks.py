from enum import Enum
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
import uuid
import time

class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.PENDING
    progress: int = 0  # 0 to 100
    status_text: str = "Initialising..."
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update(self, state: Optional[TaskState] = None, progress: Optional[int] = None, status_text: Optional[str] = None):
        if state:
            self.state = state
        if progress is not None:
            self.progress = progress
        if status_text:
            self.status_text = status_text
        self.updated_at = time.time()

class TaskRegistry:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def create_task(self, metadata: Optional[Dict[str, Any]] = None) -> Task:
        # Periodic cleanup on new task creation
        self.cleanup_completed_tasks()
        task = Task(metadata=metadata or {})
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        """Remove tasks that completed/failed more than an hour ago."""
        now = time.time()
        to_delete = [
            tid for tid, t in self._tasks.items()
            if t.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
            and (now - t.updated_at) > max_age_seconds
        ]
        for tid in to_delete:
            del self._tasks[tid]
