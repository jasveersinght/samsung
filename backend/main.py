import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import settings
from backend.logger import logger
from backend.memory.memory import RoboticsMemory
from backend.agents.llm_layer import LLMLayer
from backend.ros2_bridge.bridge import RealROS2Bridge, ROS_AVAILABLE
from backend.ros2_bridge.mock_bridge import MockROS2Bridge
from backend.perception.perception import MockPerceptionSystem
from backend.planner.planner import SymbolicPlanner
from backend.execution.engine import ExecutionEngine
from backend.api import routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Core Robotics Framework Components
    logger.info("Initializing Robotics Task Planning Core Modules...")
    
    # 1. Initialize Memory
    memory = RoboticsMemory()
    
    # 2. Initialize LLM isolation layer
    llm_layer = LLMLayer()
    
    # 3. Initialize ROS 2 Bridge (Mock or Real)
    if settings.MOCK_ROS or not ROS_AVAILABLE:
        if not ROS_AVAILABLE and not settings.MOCK_ROS:
            logger.warning("ROS 2 (rclpy) is unavailable. Forcing Mock mode.")
        logger.info("Starting robot interface in MOCK simulation mode.")
        bridge = MockROS2Bridge()
    else:
        logger.info("Connecting to active ROS 2 environment.")
        bridge = RealROS2Bridge()
        
    # 4. Initialize Perception (passes memory reference for mock detection queries)
    perception = MockPerceptionSystem(memory)
    
    # 5. Initialize Planner
    planner = SymbolicPlanner(memory)
    
    # 6. Initialize Execution Engine
    engine = ExecutionEngine(bridge, perception, memory, llm_layer)
    
    # Expose modules to the api router
    routes.engine_instance = engine
    routes.planner_instance = planner
    routes.llm_instance = llm_layer
    
    logger.info("Robotics Framework Core Modules fully loaded and operational.")
    
    yield
    
    # Shutdown / Cleanup
    logger.info("Shutting down Robotics Framework modules...")
    if engine:
        engine.cancel_current_execution()

app = FastAPI(
    title="Robotics Task Planning Framework",
    description="ROS 2-integrated natural language task planner and execution engine.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include APIs
app.include_router(routes.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "operational", "framework": "Robotics Task Planner"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
