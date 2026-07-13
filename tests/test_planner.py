import pytest
from backend.memory.memory import RoboticsMemory
from backend.planner.planner import SymbolicPlanner

def test_planner_deliver_water():
    memory = RoboticsMemory()
    planner = SymbolicPlanner(memory)
    parsed = {
        "goal": "deliver_water",
        "object": "glass",
        "contents": "water",
        "destination": "user",
        "constraints": []
    }
    plan = planner.generate_plan(parsed)
    assert plan.goal == "deliver_water"
    assert len(plan.tasks) == 9
    assert plan.tasks[0].id == "task_0_locate_kitchen"
    assert "task_0_locate_kitchen" in plan.tasks[1].dependencies

def test_planner_pick_object():
    memory = RoboticsMemory()
    planner = SymbolicPlanner(memory)
    parsed = {
        "goal": "pick_object",
        "object": "red bottle",
        "contents": None,
        "destination": "robot",
        "constraints": []
    }
    plan = planner.generate_plan(parsed)
    assert plan.goal == "pick_object"
    assert len(plan.tasks) == 5
    assert plan.tasks[0].action == "Locate"
    assert plan.tasks[2].action == "Detect"
