import asyncio
import time
import math
from typing import Dict, Any, List, Optional
from backend.planner.models import TaskPlan, TaskNode, TaskStatus
from backend.logger import logger

class ExecutionEngine:
    def __init__(self, bridge, perception, memory, llm_layer):
        self.bridge = bridge
        self.perception = perception
        self.memory = memory
        self.llm_layer = llm_layer
        
        self.current_plan: Optional[TaskPlan] = None
        self.is_running = False
        self.execution_task: Optional[asyncio.Task] = None

    def start_plan(self, plan: TaskPlan):
        """Starts executing a generated task plan in the background."""
        self.cancel_current_execution()
        self.current_plan = plan
        self.current_plan.active = True
        self.is_running = True
        self.memory.clear_failures()
        self.bridge.is_paused = False
        self.bridge.is_cancelled = False
        
        # Start execution loop
        self.execution_task = asyncio.create_task(self._execution_loop())
        logger.info(f"ExecutionEngine: Started background execution for goal: {plan.goal}")

    def cancel_current_execution(self):
        """Cancels any active execution and resets task states."""
        self.bridge.cancel_navigation()
        if self.execution_task and not self.execution_task.done():
            self.execution_task.cancel()
            logger.info("ExecutionEngine: Cancelled active execution task.")
            
        if self.current_plan:
            self.current_plan.active = False
            for task in self.current_plan.tasks:
                if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRY]:
                    task.status = TaskStatus.FAILED
                    task.error_message = "Cancelled by user"
                    
        self.is_running = False

    def pause_execution(self):
        logger.info("ExecutionEngine: Pausing execution.")
        self.bridge.is_paused = True

    def resume_execution(self):
        logger.info("ExecutionEngine: Resuming execution.")
        self.bridge.is_paused = False

    async def _execution_loop(self):
        try:
            while self.is_running and self.current_plan:
                # Find tasks that are PENDING and have all dependencies completed (SUCCESS)
                runnable_tasks = self._get_runnable_tasks()
                
                if not runnable_tasks:
                    # Check if all tasks are complete
                    all_success = all(t.status == TaskStatus.SUCCESS for t in self.current_plan.tasks)
                    any_failed = any(t.status == TaskStatus.FAILED for t in self.current_plan.tasks)
                    
                    if all_success:
                        logger.info("ExecutionEngine: Plan executed successfully!")
                        self.current_plan.active = False
                        self.is_running = False
                    elif any_failed:
                        logger.error("ExecutionEngine: Plan failed execution.")
                        self.current_plan.active = False
                        self.is_running = False
                    else:
                        # Waiting for running tasks or cycle detected
                        await asyncio.sleep(0.5)
                    continue

                # Run the first available task sequentially (physical robot constraint)
                task_to_run = runnable_tasks[0]
                await self._run_task(task_to_run)
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            logger.info("ExecutionEngine: Loop cancelled.")
        except Exception as e:
            logger.error(f"ExecutionEngine: Fatal error in execution loop: {e}", exc_info=True)
            self.is_running = False

    def _get_runnable_tasks(self) -> List[TaskNode]:
        """Returns a list of tasks that are ready to run based on status and dependencies."""
        runnable = []
        for task in self.current_plan.tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.RETRY]:
                # Check if all dependencies are SUCCESS
                deps_satisfied = True
                for dep_id in task.dependencies:
                    dep_task = self._find_task_by_id(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.SUCCESS:
                        deps_satisfied = False
                        break
                if deps_satisfied:
                    runnable.append(task)
        return runnable

    def _find_task_by_id(self, task_id: str) -> Optional[TaskNode]:
        for t in self.current_plan.tasks:
            if t.id == task_id:
                return t
        return None

    async def _run_task(self, task: TaskNode):
        """Executes a single task node with status tracking, timeouts, retries, and replanning."""
        task.status = TaskStatus.RUNNING
        logger.info(f"Executing: [{task.name}] (Action: {task.action})")
        
        attempt = 1
        success = False
        error_msg = ""
        
        while attempt <= (task.max_retries + 1) and not success:
            if self.bridge.is_cancelled:
                task.status = TaskStatus.FAILED
                task.error_message = "Cancelled by user"
                return
                
            try:
                # Wrap execution in timeout
                success = await asyncio.wait_for(
                    self._dispatch_action(task.action, task.parameters),
                    timeout=task.timeout
                )
                if not success:
                    error_msg = f"Action {task.action} returned False"
            except asyncio.TimeoutError:
                error_msg = f"Task timed out after {task.timeout} seconds"
                logger.warning(f"[{task.name}] Attempt {attempt} failed: {error_msg}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[{task.name}] Attempt {attempt} crashed: {error_msg}")
                
            if not success:
                if attempt <= task.max_retries:
                    task.status = TaskStatus.RETRY
                    task.retry_count = attempt
                    logger.info(f"[{task.name}] Retrying (Attempt {attempt + 1}/{task.max_retries + 1})...")
                    await asyncio.sleep(1.5)  # Cooldown before retry
                attempt += 1

        if success:
            task.status = TaskStatus.SUCCESS
            logger.info(f"[{task.name}] Completed successfully.")
        else:
            task.status = TaskStatus.FAILED
            task.error_message = error_msg
            logger.error(f"[{task.name}] Failed: {error_msg}")
            # Trigger failure recovery and replanning
            await self._trigger_replanning(task, error_msg)

    async def _dispatch_action(self, action: str, params: Dict[str, Any]) -> bool:
        """Dispatches the symbolic action to the ROS 2 / Perception / Memory components."""
        if action == "Locate":
            target = params.get("target")
            logger.info(f"Execution: Querying memory coordinate for target '{target}'")
            coords = self.memory.get_coordinates(target)
            if coords:
                logger.info(f"Execution: Target '{target}' located at {coords}")
                return True
            else:
                logger.error(f"Execution: Target '{target}' could not be located in map memory.")
                return False
                
        elif action == "Navigate":
            dest = params.get("destination")
            coords = self.memory.get_coordinates(dest)
            if not coords:
                logger.error(f"Execution: Cannot navigate, unknown location '{dest}'")
                return False
            # Call Nav2 (mock/real bridge)
            x, y, theta = coords
            # Run in executor to avoid blocking the async loop for synchronous mock updates
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.bridge.navigate_to, x, y, theta)
            return result
            
        elif action == "Detect":
            obj = params.get("object")
            # Scan with perception
            detections = self.perception.detect_objects(camera_frame=None, target_label=obj)
            if detections:
                pose = self.perception.estimate_pose(obj, detections)
                # If we detect the object, update its location in memory
                if pose:
                    # Determine current robot area/room based on coordinates
                    room = "kitchen"
                    if self.bridge.x < -1.5:
                        room = "office"
                    elif self.bridge.x > 1.0:
                        # Let's say if we are near sink coords (1.5, 6.2)
                        dist_to_sink = math.sqrt((self.bridge.x - 1.5)**2 + (self.bridge.y - 6.2)**2)
                        if dist_to_sink < 1.0:
                            room = "sink"
                        else:
                            room = "kitchen"
                    
                    self.memory.update_object_location(obj, room, pose, detected=True)
                return True
            else:
                # Add failure to history for replanning reasoning
                self.memory.record_failure("Detect", f"{obj} not in view", f"x={self.bridge.x:.2f}, y={self.bridge.y:.2f}")
                return False
                
        elif action in ["Pick", "Place", "Deliver", "Fill"]:
            # Manipulation actions
            action_desc = f"{action} " + (params.get("object") or params.get("liquid") or "")
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.bridge.manipulate_arm, action_desc)
            return result
            
        elif action == "Verify":
            condition = params.get("condition")
            logger.info(f"Execution: Verifying target condition '{condition}'")
            # Mock verification
            await asyncio.sleep(0.5)
            return True
            
        else:
            logger.warning(f"Execution: Unknown action '{action}'. Succeeding by default.")
            return True

    async def _trigger_replanning(self, failed_task: TaskNode, reason: str):
        """
        Uses LLM layer to generate a recovery plan, then dynamically updates
        the task graph with new recovery steps.
        """
        logger.info("Executing recovery/replanning pipeline...")
        memory_ctx = self.memory.get_memory_context()
        
        # Get alternate recovery tasks from LLM layer
        recovery_steps = self.llm_layer.generate_replanning_strategy(failed_task.name, reason, memory_ctx)
        
        if not recovery_steps:
            logger.error("Replanner: No recovery strategy generated. Plan aborting.")
            return

        logger.info(f"Replanner: Generated {len(recovery_steps)} recovery steps.")
        
        # We need to construct new TaskNodes and splice them into the graph
        new_tasks: List[TaskNode] = []
        
        # Find failed task's original dependencies.
        # The first recovery step should depend on whatever the failed task depended on,
        # OR it can depend on the current completed states.
        # Since we are already at the failed step, we want recovery steps to run *now*.
        # So we make the first recovery step depend on the failed task's dependencies.
        # And we make the failed task depend on the last recovery step.
        # In addition, we must clear the failed task's status back to PENDING and clear its error.
        
        parent_dependencies = failed_task.dependencies.copy()
        last_recovery_id = None
        
        for idx, step in enumerate(recovery_steps):
            step_action = step["action"]
            step_params = step["parameters"]
            step_id = f"task_recovery_{idx}_{step_action.lower()}_{int(time.time())}"
            step_name = f"Search: {step_action} " + str(step_params.get("destination") or step_params.get("object") or "")
            
            # First recovery task depends on the original failed task's dependencies
            # Subsequent recovery tasks depend on the previous recovery task
            deps = parent_dependencies if idx == 0 else [last_recovery_id]
            
            rec_node = TaskNode(
                id=step_id,
                name=step_name,
                action=step_action,
                parameters=step_params,
                status=TaskStatus.PENDING,
                dependencies=deps,
                max_retries=1,
                timeout=20.0
            )
            new_tasks.append(rec_node)
            last_recovery_id = step_id
            
        # Update the original failed task so it depends on the last recovery task
        failed_task.dependencies = [last_recovery_id]
        failed_task.status = TaskStatus.PENDING
        failed_task.error_message = None
        failed_task.retry_count = 0
        
        # Insert the new recovery tasks into our plan tasks list
        # Find the index of the failed task and insert the new tasks before it
        failed_idx = self.current_plan.tasks.index(failed_task)
        self.current_plan.tasks = (
            self.current_plan.tasks[:failed_idx] + 
            new_tasks + 
            self.current_plan.tasks[failed_idx:]
        )
        
        # Log the updated task graph
        logger.info("Replanner: Successfully injected recovery tasks into task plan graph.")
        for t in self.current_plan.tasks:
            logger.info(f" - Task: {t.id} (Status: {t.status}, Depends: {t.dependencies})")
