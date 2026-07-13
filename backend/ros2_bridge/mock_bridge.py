import time
import math
from typing import Dict, Any, Optional, Tuple
from backend.ros2_bridge.bridge import ROS2BridgeInterface
from backend.logger import logger

class MockROS2Bridge(ROS2BridgeInterface):
    """
    Mock ROS 2 bridge for simulation without actual ROS 2 installation.
    Simulates kinematics, Navigation2 path traversal, MoveIt2 arm movements,
    and sensor status telemetry.
    """
    def __init__(self):
        # Kinematics & state variables
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.battery_level = 95.0
        self.joint_positions = {"joint_1": 0.0, "joint_2": 0.0, "joint_3": 0.0, "gripper": 0.0}
        
        self.is_paused = False
        self.is_cancelled = False
        self.current_action = "idle"
        self.topic_logs = []

    def log_topic(self, topic: str, msg: str):
        log_msg = f"[{topic}] {msg}"
        self.topic_logs.append(log_msg)
        if len(self.topic_logs) > 50:
            self.topic_logs.pop(0)

    def navigate_to(self, target_x: float, target_y: float, target_theta: float, timeout: float = 60.0) -> bool:
        self.current_action = "navigating"
        self.is_cancelled = False
        logger.info(f"Mock Nav2: Executing path planning to (x={target_x:.2f}, y={target_y:.2f}, theta={target_theta:.2f})")
        
        # Calculate steps
        start_x, start_y = self.x, self.y
        distance = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
        steps = max(5, int(distance * 3))  # Number of interpolation steps
        
        for i in range(1, steps + 1):
            # Check for cancellation
            if self.is_cancelled:
                logger.warning("Mock Nav2: Navigation cancelled by operator.")
                self.current_action = "idle"
                return False
            
            # Check for pause loop
            while self.is_paused:
                time.sleep(0.1)
                if self.is_cancelled:
                    self.current_action = "idle"
                    return False
            
            # Interpolate position
            t = i / steps
            self.x = start_x + (target_x - start_x) * t
            self.y = start_y + (target_y - start_y) * t
            self.theta = self.theta + (target_theta - self.theta) * t
            
            # Update telemetry
            self.battery_level -= 0.15
            self.log_topic("/odom", f"Pose: x={self.x:.3f}, y={self.y:.3f}, theta={self.theta:.3f}")
            self.log_topic("/cmd_vel", f"Linear: {0.3:.2f}, Angular: {0.1:.2f}")
            
            time.sleep(0.3)  # Simulate motion delay
            
        self.x, self.y, self.theta = target_x, target_y, target_theta
        self.current_action = "idle"
        logger.info("Mock Nav2: Goal reached successfully.")
        return True

    def manipulate_arm(self, action: str, timeout: float = 30.0) -> bool:
        self.current_action = f"manipulating: {action}"
        self.is_cancelled = False
        logger.info(f"Mock MoveIt2: Actuating robotic arm for action '{action}'")
        
        steps = 4
        for i in range(1, steps + 1):
            if self.is_cancelled:
                logger.warning("Mock MoveIt2: Manipulation action cancelled.")
                self.current_action = "idle"
                return False
                
            while self.is_paused:
                time.sleep(0.1)
                if self.is_cancelled:
                    self.current_action = "idle"
                    return False
            
            # Simulate joint state changes
            t = i / steps
            if "pick" in action.lower():
                self.joint_positions["joint_1"] = 0.5 * t
                self.joint_positions["joint_2"] = 0.8 * t
                self.joint_positions["gripper"] = 1.0 * t
                self.log_topic("/joint_states", f"Actuating: gripper={1.0*t:.2f}")
            elif "place" in action.lower() or "deliver" in action.lower():
                self.joint_positions["joint_1"] = 0.2 * (1 - t)
                self.joint_positions["gripper"] = 0.0  # Open
                self.log_topic("/joint_states", f"Opening gripper.")
            elif "fill" in action.lower():
                self.joint_positions["joint_3"] = 0.6 * t
                self.log_topic("/joint_states", f"Lifting glass up to source.")
                
            self.battery_level -= 0.1
            time.sleep(0.4)
            
        self.current_action = "idle"
        logger.info(f"Mock MoveIt2: Manipulation '{action}' complete.")
        return True

    def get_tf_transform(self, parent: str, child: str) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]]:
        # Return dynamic transform based on current coordinates
        if parent == "map" and child == "base_link":
            return ((self.x, self.y, 0.0), (0.0, 0.0, math.sin(self.theta/2), math.cos(self.theta/2)))
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))

    def get_sensor_data(self) -> Dict[str, Any]:
        return {
            "battery_percent": max(0.0, round(self.battery_level, 2)),
            "lidar_status": "healthy",
            "camera_status": "active",
            "joint_states": self.joint_positions,
            "current_action": self.current_action,
            "pose": {"x": round(self.x, 3), "y": round(self.y, 3), "theta": round(self.theta, 3)}
        }

    def cancel_navigation(self) -> None:
        self.is_cancelled = True
        logger.info("Mock Nav2: Cancel command received.")
