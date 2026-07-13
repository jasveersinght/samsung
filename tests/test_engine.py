import pytest
import asyncio
from backend.memory.memory import RoboticsMemory
from backend.agents.llm_layer import LLMLayer
from backend.ros2_bridge.mock_bridge import MockROS2Bridge
from backend.perception.perception import MockPerceptionSystem
from backend.planner.planner import SymbolicPlanner
from backend.execution.engine import ExecutionEngine
from backend.planner.models import TaskPlan, TaskNode, TaskStatus

@pytest.mark.asyncio
async def test_engine_single_task_success():
    mem = RoboticsMemory()
    bridge = MockROS2Bridge()
    # Speed up mock movement for testing
    bridge.navigate_to = lambda x, y, th: True
    bridge.manipulate_arm = lambda act: True
    
    perc = MockPerceptionSystem(mem)
    llm = LLMLayer()
    
    task = TaskNode(
        id="t0",
        name="Locate kitchen",
        action="Locate",
        parameters={"target": "kitchen"}
    )
    plan = TaskPlan(goal="test_goal", tasks=[task])
    
    engine = ExecutionEngine(bridge, perc, mem, llm)
    engine.start_plan(plan)
    
    # Wait for execution loop to finalize
    for _ in range(10):
        if not engine.is_running:
            break
        await asyncio.sleep(0.05)
        
    assert task.status == TaskStatus.SUCCESS
    assert not engine.is_running

@pytest.mark.asyncio
async def test_engine_replanning_trigger():
    mem = RoboticsMemory()
    bridge = MockROS2Bridge()
    # Configure bridge navigation to work immediately
    bridge.navigate_to = lambda x, y, th: True
    bridge.manipulate_arm = lambda act: True
    
    perc = MockPerceptionSystem(mem)
    llm = LLMLayer()
    
    # Force mock detection of "glass" to fail to trigger replanning
    # In mem.object_locations, we set glass detected=False, which is the default.
    # The first task is Detect glass, which should fail.
    task_detect = TaskNode(
        id="task_detect",
        name="Detect glass",
        action="Detect",
        parameters={"object": "glass"},
        max_retries=0  # Fail immediately to speed up test
    )
    plan = TaskPlan(goal="deliver_water", tasks=[task_detect])
    
    engine = ExecutionEngine(bridge, perc, mem, llm)
    engine.start_plan(plan)
    
    # Run the loop for a short moment
    for _ in range(15):
        if not engine.is_running:
            # If the engine finished, it means the replanned flow ran or it aborted.
            # In mock mode, the replanned tasks get injected, then they run.
            break
        await asyncio.sleep(0.05)
        
    # Check that new tasks were injected into current plan.
    # The list should have recovery tasks injected before task_detect.
    assert len(plan.tasks) > 1
    # There should be tasks with id starting with "task_recovery_"
    recovery_tasks = [t for t in plan.tasks if "recovery" in t.id]
    assert len(recovery_tasks) > 0
