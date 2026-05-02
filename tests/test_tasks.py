import pytest
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

@pytest.mark.asyncio
async def test_analyze_as_task():
    # Mocking analysis to avoid real repo clone
    # This requires some patching if we want a real E2E
    # For now, let's just verify the tool returns a taskId
    result = analyze_codebase(raw_files=[{"filename": "test.cpp", "content": "void f(){}"}], as_task=True)
    
    assert "taskId" in result
    task_id = result["taskId"]
    
    # Wait for background task to finish (it's very fast since it's raw_files)
    time.sleep(1) 
    
    task = services.task_registry.get_task(task_id)
    assert task is not None
    assert task.state in (TaskState.RUNNING, TaskState.COMPLETED)
