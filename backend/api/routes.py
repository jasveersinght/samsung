from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
from openai import OpenAI
from backend.config import settings
from backend.logger import log_history, logger
from backend.planner.models import TaskPlan

router = APIRouter()

# Global pointers set during server startup
engine_instance = None
planner_instance = None
llm_instance = None

class CommandRequest(BaseModel):
    command: str

@router.post("/command")
async def receive_command(req: CommandRequest):
    if not engine_instance or not planner_instance or not llm_instance:
        raise HTTPException(status_code=500, detail="Core modules not initialized on server.")
    
    instruction = req.command
    logger.info(f"API: Received natural language command: '{instruction}'")
    
    try:
        # 1. Parse instruction with LLM
        parsed_goal = llm_instance.parse_instruction(instruction)
        logger.info(f"API: Parsed goal: {parsed_goal}")
        
        # 2. Generate Plan
        plan = planner_instance.generate_plan(parsed_goal)
        
        # 3. Start execution
        engine_instance.start_plan(plan)
        
        return plan.dict()
    except Exception as e:
        logger.error(f"API: Failed to process command: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan")
async def get_plan():
    if engine_instance and engine_instance.current_plan:
        return engine_instance.current_plan.dict()
    return None

@router.get("/status")
async def get_status():
    if not engine_instance:
        return {"status": "offline"}
    
    sensor_data = engine_instance.bridge.get_sensor_data()
    return {
        "status": "online",
        "robot_telemetry": sensor_data,
        "is_running": engine_instance.is_running,
        "is_paused": engine_instance.bridge.is_paused,
        "current_goal": engine_instance.current_plan.goal if engine_instance.current_plan else None
    }

@router.get("/logs")
async def get_logs():
    return list(log_history)

@router.post("/cancel")
async def cancel_execution():
    if engine_instance:
        engine_instance.cancel_current_execution()
        return {"status": "success", "message": "Execution cancelled"}
    return {"status": "error", "message": "Engine not running"}

@router.post("/pause")
async def pause_execution():
    if engine_instance:
        engine_instance.pause_execution()
        return {"status": "success", "message": "Execution paused"}
    return {"status": "error", "message": "Engine not running"}

@router.post("/resume")
async def resume_execution():
    if engine_instance:
        engine_instance.resume_execution()
        return {"status": "success", "message": "Execution resumed"}
    return {"status": "error", "message": "Engine not running"}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket: Client connected.")
    
    last_log_count = 0
    try:
        while True:
            # Gather state packet
            sensor_data = engine_instance.bridge.get_sensor_data() if engine_instance else {}
            plan_data = engine_instance.current_plan.dict() if (engine_instance and engine_instance.current_plan) else None
            
            # Extract logs added since last cycle
            logs_list = list(log_history)
            new_logs = logs_list[last_log_count:]
            last_log_count = len(logs_list)
            
            # Combine topic logs from simulated bridge
            topic_logs = getattr(engine_instance.bridge, "topic_logs", []) if engine_instance else []
            
            payload = {
                "telemetry": sensor_data,
                "plan": plan_data,
                "logs": new_logs,
                "topic_logs": topic_logs,
                "is_running": engine_instance.is_running if engine_instance else False,
                "is_paused": engine_instance.bridge.is_paused if engine_instance else False
            }
            
            await websocket.send_json(payload)
            await asyncio.sleep(0.15)  # Emitter rate limit (approx 6-7 Hz)
    except WebSocketDisconnect:
        logger.info("WebSocket: Client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")

@router.post("/speech")
async def transcribe_speech(file: UploadFile = File(...)):
    if not settings.OPENAI_API_KEY:
        # Fallback: Mock transcription based on file size/randomness
        logger.warning("OpenAI API Key is missing. Returning mock transcription.")
        contents = await file.read()
        length = len(contents)
        if length % 3 == 0:
            text = "Bring me a glass of water."
        elif length % 3 == 1:
            text = "Pick up the red bottle."
        else:
            text = "Go to the kitchen and return."
        logger.info(f"Mock transcription: '{text}'")
        return {"text": text}

    try:
        import tempfile
        import os
        
        filename = file.filename or "audio.wav"
        ext = os.path.splitext(filename)[1] or ".wav"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            with open(tmp_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            text = transcription.text
            logger.info(f"OpenAI Whisper transcription: '{text}'")
            return {"text": text}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.error(f"Speech transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
