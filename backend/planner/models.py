from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRY = "RETRY"

class TaskNode(BaseModel):
    id: str
    name: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = Field(default_factory=list)  # List of TaskNode IDs that must succeed first
    retry_count: int = 0
    max_retries: int = 2
    timeout: float = 30.0
    error_message: Optional[str] = None

class TaskPlan(BaseModel):
    goal: str
    parsed_params: Dict[str, Any] = Field(default_factory=dict)
    tasks: List[TaskNode] = Field(default_factory=list)
    active: bool = False
