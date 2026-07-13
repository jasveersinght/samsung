from typing import List, Dict, Any, Optional
import math
from backend.logger import logger

class DetectedObject:
    def __init__(self, label: str, confidence: float, pose_3d: tuple, bounding_box: Dict[str, int]):
        self.label = label
        self.confidence = confidence
        self.pose_3d = pose_3d  # (x, y, z)
        self.bounding_box = bounding_box  # {"xmin", "ymin", "xmax", "ymax"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "pose_3d": self.pose_3d,
            "bounding_box": self.bounding_box
        }

class ObjectDetectorInterface:
    def detect_objects(self, camera_frame: Any, target_label: str) -> List[DetectedObject]:
        raise NotImplementedError

class PoseEstimatorInterface:
    def estimate_pose(self, object_label: str, detections: List[DetectedObject]) -> Optional[tuple]:
        raise NotImplementedError

class SegmentorInterface:
    def segment_image(self, camera_frame: Any) -> Dict[str, Any]:
        raise NotImplementedError


class MockPerceptionSystem(ObjectDetectorInterface, PoseEstimatorInterface, SegmentorInterface):
    """
    Mock implementation of perception interfaces.
    Simulates object detection and poses based on the robot's distance to targets.
    """
    def __init__(self, memory):
        self.memory = memory

    def detect_objects(self, camera_frame: Any, target_label: str) -> List[DetectedObject]:
        logger.info(f"Perception scanning for: '{target_label}'")
        
        # Check coordinates from memory
        obj_info = self.memory.get_object_info(target_label)
        if not obj_info:
            logger.info(f"Perception scan results: 0 instances of '{target_label}' found (Unknown Object).")
            return []

        # Simulate failures: e.g. glass detection fails at "kitchen" countertop (first location)
        # to trigger the replanner sequence.
        if target_label.lower() == "glass" and not obj_info["detected"]:
            # Check where the robot currently is
            # If the robot is at countertop or kitchen origin, we return empty (glass not found)
            # This triggers the execution failure.
            # Once replanning routes it to the "sink", the perception will succeed!
            logger.warning("Perception: Glass not visible on countertop table.")
            return []

        # Find the object coordinates and compare with simulated robot coordinates
        target_coords = obj_info["coordinates"]
        
        # We succeed! Create a detected object with high confidence
        logger.info(f"Perception scan results: Found '{target_label}' with 96.5% confidence.")
        return [
            DetectedObject(
                label=target_label,
                confidence=0.965,
                pose_3d=target_coords,
                bounding_box={"xmin": 120, "ymin": 200, "xmax": 240, "ymax": 380}
            )
        ]

    def estimate_pose(self, object_label: str, detections: List[DetectedObject]) -> Optional[tuple]:
        if not detections:
            logger.warning(f"No detections found for '{object_label}' to estimate pose.")
            return None
        
        # Return the 3D pose of the first detection
        logger.info(f"Estimated pose for '{object_label}': {detections[0].pose_3d}")
        return detections[0].pose_3d

    def segment_image(self, camera_frame: Any) -> Dict[str, Any]:
        """Returns mock mask polygons for visualization purposes."""
        logger.info("Performing semantic instance segmentation on camera frame.")
        return {
            "resolution": (640, 480),
            "segments": [
                {"label": "table", "polygon": [[100, 300], [540, 300], [600, 450], [40, 450]]},
                {"label": "glass", "polygon": [[150, 220], [210, 220], [220, 280], [140, 280]]}
            ]
        }
