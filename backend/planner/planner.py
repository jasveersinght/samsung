from typing import Dict, Any, List
from backend.planner.models import TaskNode, TaskPlan, TaskStatus
from backend.logger import logger

class SymbolicPlanner:
    def __init__(self, memory):
        self.memory = memory

    def generate_plan(self, parsed_goal: Dict[str, Any]) -> TaskPlan:
        """
        Generates an ordered task dependency graph from a parsed goal.
        """
        goal_name = parsed_goal.get("goal", "generic_task")
        target_obj = parsed_goal.get("object")
        contents = parsed_goal.get("contents")
        destination = parsed_goal.get("destination")
        
        logger.info(f"Generating plan for goal '{goal_name}'...")
        
        tasks: List[TaskNode] = []
        
        if goal_name == "deliver_water":
            # 1. Locate kitchen
            tasks.append(TaskNode(
                id="task_0_locate_kitchen",
                name="Locate kitchen",
                action="Locate",
                parameters={"target": "kitchen"},
                dependencies=[]
            ))
            # 2. Navigate to kitchen
            tasks.append(TaskNode(
                id="task_1_navigate_kitchen",
                name="Navigate to kitchen",
                action="Navigate",
                parameters={"destination": "kitchen"},
                dependencies=["task_0_locate_kitchen"]
            ))
            # 3. Detect glass
            tasks.append(TaskNode(
                id="task_2_detect_glass",
                name="Detect glass",
                action="Detect",
                parameters={"object": "glass"},
                dependencies=["task_1_navigate_kitchen"]
            ))
            # 4. Pick glass
            tasks.append(TaskNode(
                id="task_3_pick_glass",
                name="Pick glass",
                action="Pick",
                parameters={"object": "glass"},
                dependencies=["task_2_detect_glass"]
            ))
            # 5. Locate water source
            tasks.append(TaskNode(
                id="task_4_locate_water",
                name="Locate water source",
                action="Locate",
                parameters={"target": "water source"},
                dependencies=["task_3_pick_glass"]
            ))
            # 6. Fill glass
            tasks.append(TaskNode(
                id="task_5_fill_glass",
                name="Fill glass",
                action="Fill",
                parameters={"object": "glass", "liquid": "water"},
                dependencies=["task_4_locate_water"]
            ))
            # 7. Navigate to user
            tasks.append(TaskNode(
                id="task_6_navigate_user",
                name="Navigate to user",
                action="Navigate",
                parameters={"destination": "user"},
                dependencies=["task_5_fill_glass"]
            ))
            # 8. Deliver glass
            tasks.append(TaskNode(
                id="task_7_deliver",
                name="Deliver glass",
                action="Deliver",
                parameters={"object": "glass", "destination": "user"},
                dependencies=["task_6_navigate_user"]
            ))
            # 9. Verify completion
            tasks.append(TaskNode(
                id="task_8_verify",
                name="Verify completion",
                action="Verify",
                parameters={"condition": "water_delivered"},
                dependencies=["task_7_deliver"]
            ))
            
        elif goal_name == "pick_object":
            obj_name = target_obj or "object"
            # Get object location from memory (e.g. office)
            obj_info = self.memory.get_object_info(obj_name)
            loc = obj_info["location"] if obj_info else "office"
            
            tasks.append(TaskNode(
                id="task_0_locate_obj",
                name=f"Locate {obj_name}",
                action="Locate",
                parameters={"target": loc},
                dependencies=[]
            ))
            tasks.append(TaskNode(
                id="task_1_navigate_obj",
                name=f"Navigate to {loc}",
                action="Navigate",
                parameters={"destination": loc},
                dependencies=["task_0_locate_obj"]
            ))
            tasks.append(TaskNode(
                id="task_2_detect_obj",
                name=f"Detect {obj_name}",
                action="Detect",
                parameters={"object": obj_name},
                dependencies=["task_1_navigate_obj"]
            ))
            tasks.append(TaskNode(
                id="task_3_pick_obj",
                name=f"Pick {obj_name}",
                action="Pick",
                parameters={"object": obj_name},
                dependencies=["task_2_detect_obj"]
            ))
            tasks.append(TaskNode(
                id="task_4_verify_obj",
                name="Verify completion",
                action="Verify",
                parameters={"condition": f"{obj_name}_picked"},
                dependencies=["task_3_pick_obj"]
            ))
            
        elif goal_name == "navigate_and_return":
            dest = destination or "kitchen"
            
            tasks.append(TaskNode(
                id="task_0_locate_dest",
                name=f"Locate {dest}",
                action="Locate",
                parameters={"target": dest},
                dependencies=[]
            ))
            tasks.append(TaskNode(
                id="task_1_navigate_dest",
                name=f"Navigate to {dest}",
                action="Navigate",
                parameters={"destination": dest},
                dependencies=["task_0_locate_dest"]
            ))
            tasks.append(TaskNode(
                id="task_2_navigate_origin",
                name="Navigate back to origin",
                action="Navigate",
                parameters={"destination": "origin"},
                dependencies=["task_1_navigate_dest"]
            ))
            tasks.append(TaskNode(
                id="task_3_verify_nav",
                name="Verify completion",
                action="Verify",
                parameters={"condition": "returned_to_origin"},
                dependencies=["task_2_navigate_origin"]
            ))
            
        else:
            # Generic fallback plan
            tasks.append(TaskNode(
                id="task_0_generic",
                name="Navigate to destination",
                action="Navigate",
                parameters={"destination": destination or "origin"},
                dependencies=[]
            ))
            tasks.append(TaskNode(
                id="task_1_verify_generic",
                name="Verify completion",
                action="Verify",
                parameters={"condition": "generic_task_complete"},
                dependencies=["task_0_generic"]
            ))

        plan = TaskPlan(
            goal=goal_name,
            parsed_params=parsed_goal,
            tasks=tasks
        )
        logger.info(f"Plan generated successfully with {len(tasks)} steps.")
        return plan
