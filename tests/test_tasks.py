import time
from datetime import datetime, timedelta
from src.utils.tasks import TaskRegistry, TaskState
from src.tools.analysis import analyze_codebase
import src.utils.services as services

def test_task_registry():
    registry = TaskRegistry()
    task = registry.create_task(metadata={"test": True})
    
    assert task.id is not None
    assert task.state == TaskState.PENDING
    assert task.metadata["test"] is True
    
    task.update(state=TaskState.RUNNING, progress=50)
    assert task.state == TaskState.RUNNING
    assert task.progress == 50
    
    retrieved = registry.get_task(task.id)
    assert retrieved == task

def test_task_cleanup():
    registry = TaskRegistry()
    task = registry.create_task()
    task.update(state=TaskState.COMPLETED)
    
    # Update updated_at to be old
    task.updated_at = datetime.now() - timedelta(seconds=4000)
    
    registry.cleanup_completed_tasks(max_age_seconds=3600)
    assert registry.get_task(task.id) is None

def test_analyze_as_task():
    # The background work runs in a daemon thread, so a plain synchronous
    # poll is sufficient — no event loop involved.
    result = analyze_codebase(raw_files=[{"filename": "test.cpp", "content": "void f(){}"}], as_task=True)

    assert "taskId" in result
    task_id = result["taskId"]

    # Poll until the background task reaches a terminal state (with a timeout)
    terminal_states = (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
    deadline = time.monotonic() + 10
    task = None
    while time.monotonic() < deadline:
        task = services.task_registry.get_task(task_id)
        if task is not None and task.state in terminal_states:
            break
        time.sleep(0.1)

    assert task is not None
    assert task.state in terminal_states
