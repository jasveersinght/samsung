from typing import Dict, Any, List, Optional
from backend.logger import logger

class RoboticsMemory:
    def __init__(self):
        # Semantic database mapping locations to landmarks and furniture
        self.semantic_db = {
            "kitchen": ["fridge", "sink", "cupboard", "dining table", "countertop"],
            "living room": ["sofa", "coffee table", "tv stand"],
            "office": ["desk", "bookshelf", "chair"]
        }
        
        # Spatial coordinate positions (x, y, theta) for rooms/locations
        self.map_memory = {
            "origin": (0.0, 0.0, 0.0),
            "kitchen": (2.0, 5.0, 1.57),
            "living room": (0.0, 0.0, 0.0),
            "office": (-3.0, 2.0, -0.78),
            "user": (-1.0, -1.0, 3.14),
            
            # Sub-locations in kitchen for replanning/searching
            "cupboard": (2.5, 6.0, 1.57),
            "sink": (1.5, 6.2, 3.14),
            "dining table": (3.0, 4.0, 0.0),
            "countertop": (1.8, 4.8, -1.57)
        }

        # Simulated object locations (with coordinates and detection status)
        self.object_locations = {
            "red bottle": {
                "location": "office",
                "coordinates": (-3.0, 2.5, 0.8),
                "detected": True
            },
            "glass": {
                # Setup so that detecting glass at default "kitchen" countertop fails first,
                # then replanning finds it at "sink" or "cupboard".
                "location": "sink",
                "coordinates": (1.5, 6.2, 0.95),
                "detected": False  # Initial state
            },
            "water source": {
                "location": "sink",
                "coordinates": (1.5, 6.25, 1.1),
                "detected": True
            }
        }
        
        # Failure and replanning records
        self.failures_history: List[Dict[str, Any]] = []
        self.execution_history: List[Dict[str, Any]] = []

    def get_coordinates(self, location: str) -> Optional[tuple]:
        """Gets coordinates for a room, furniture item, or landmark."""
        loc_lower = location.lower()
        if loc_lower in self.map_memory:
            return self.map_memory[loc_lower]
        logger.warning(f"Location '{location}' not found in map memory.")
        return None

    def get_object_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Gets location and status details for a target object."""
        obj_lower = object_name.lower()
        for k, v in self.object_locations.items():
            if obj_lower in k:
                return v
        return None

    def update_object_location(self, name: str, location: str, coords: tuple, detected: bool = True):
        """Updates or registers an object's spatial location."""
        self.object_locations[name.lower()] = {
            "location": location,
            "coordinates": coords,
            "detected": detected
        }
        logger.info(f"Memory updated: object '{name}' is at '{location}' {coords} (detected={detected})")

    def record_failure(self, task_name: str, reason: str, location: str):
        """Records execution failures to provide context for downstream replanning."""
        failure = {"task": task_name, "reason": reason, "location": location}
        self.failures_history.append(failure)
        logger.info(f"Memory recorded failure: {failure}")

    def clear_failures(self):
        self.failures_history.clear()

    def get_memory_context(self) -> Dict[str, Any]:
        """Returns the full memory snapshot for LLM/planner reasoning."""
        return {
            "semantic_db": self.semantic_db,
            "object_locations": self.object_locations,
            "failures": self.failures_history
        }
