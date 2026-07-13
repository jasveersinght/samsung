import json
from typing import Dict, Any, List
from backend.config import settings
from backend.logger import logger

class LLMLayer:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        logger.info(f"LLMLayer initialized with provider: {self.provider}")

    def parse_instruction(self, instruction: str) -> Dict[str, Any]:
        """
        Parses a natural language instruction into a structured goal schema:
        {
            "goal": str,
            "object": str,
            "contents": str (optional),
            "destination": str (optional),
            "constraints": list
        }
        """
        logger.info(f"Parsing instruction: '{instruction}'")
        
        # Rule-based fallback/mock parser to ensure it runs out of the box
        norm_instr = instruction.lower().strip()
        
        if "glass of water" in norm_instr or "bring me a glass" in norm_instr:
            return {
                "goal": "deliver_water",
                "object": "glass",
                "contents": "water",
                "destination": "user",
                "constraints": []
            }
        elif "red bottle" in norm_instr:
            return {
                "goal": "pick_object",
                "object": "red bottle",
                "contents": None,
                "destination": "robot",
                "constraints": []
            }
        elif "go to the kitchen" in norm_instr or "return" in norm_instr:
            return {
                "goal": "navigate_and_return",
                "object": None,
                "contents": None,
                "destination": "kitchen",
                "constraints": ["return_to_origin"]
            }

        # If LLM API keys are provided and configured, run actual LLM query
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                import httpx
                headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
                prompt = self._get_parse_prompt(instruction)
                data = {
                    "model": "gpt-4-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }
                res = httpx.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers, timeout=10.0)
                res.raise_for_status()
                content = res.json()["choices"][0]["message"]["content"]
                return json.loads(content)
            except Exception as e:
                logger.error(f"OpenAI parsing failed: {e}. Falling back to default mock structure.")
        
        elif self.provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                import httpx
                # Simplified Gemini API call
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
                prompt = self._get_parse_prompt(instruction)
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }
                res = httpx.post(url, json=data, timeout=10.0)
                res.raise_for_status()
                content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(content)
            except Exception as e:
                logger.error(f"Gemini parsing failed: {e}. Falling back to default mock structure.")

        # Default fallback
        logger.warning(f"No match in mock parser and no API key configured. Using default parse structure.")
        return {
            "goal": "generic_task",
            "object": "target",
            "contents": None,
            "destination": "kitchen",
            "constraints": []
        }

    def generate_replanning_strategy(self, failed_task_name: str, reason: str, memory_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates custom recovery strategies (alternate steps) when a task fails.
        Returns a list of search actions/locations.
        """
        logger.warning(f"Replanning requested for failed task '{failed_task_name}'. Reason: {reason}")
        
        # Rule-based fallback recovery strategy
        if "detect" in failed_task_name.lower() or "locate" in failed_task_name.lower():
            target_obj = failed_task_name.split()[-1] if len(failed_task_name.split()) > 1 else "object"
            # Return sequence of search actions in nearby locations
            return [
                {"action": "Navigate", "parameters": {"destination": "cupboard"}},
                {"action": "Detect", "parameters": {"object": target_obj}},
                {"action": "Navigate", "parameters": {"destination": "sink"}},
                {"action": "Detect", "parameters": {"object": target_obj}},
                {"action": "Navigate", "parameters": {"destination": "dining table"}},
                {"action": "Detect", "parameters": {"object": target_obj}}
            ]

        # LLM integration if configured
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                import httpx
                headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
                prompt = self._get_replanning_prompt(failed_task_name, reason, memory_context)
                data = {
                    "model": "gpt-4-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }
                res = httpx.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers, timeout=10.0)
                res.raise_for_status()
                content = res.json()["choices"][0]["message"]["content"]
                return json.loads(content).get("recovery_steps", [])
            except Exception as e:
                logger.error(f"OpenAI replanning failed: {e}. Falling back to default recovery.")
                
        elif self.provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
                prompt = self._get_replanning_prompt(failed_task_name, reason, memory_context)
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }
                res = httpx.post(url, json=data, timeout=10.0)
                res.raise_for_status()
                content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(content).get("recovery_steps", [])
            except Exception as e:
                logger.error(f"Gemini replanning failed: {e}. Falling back to default recovery.")

        # Default fallback recovery sequence
        return [
            {"action": "Navigate", "parameters": {"destination": "cupboard"}},
            {"action": "Detect", "parameters": {"object": "glass"}},
            {"action": "Navigate", "parameters": {"destination": "sink"}},
            {"action": "Detect", "parameters": {"object": "glass"}},
            {"action": "Navigate", "parameters": {"destination": "dining table"}},
            {"action": "Detect", "parameters": {"object": "glass"}}
        ]

    def _get_parse_prompt(self, instruction: str) -> str:
        return f"""
        You are the NLU module of a ROS 2 autonomous robot. Parse the following natural language instruction:
        "{instruction}"
        
        Provide JSON output matching the following schema:
        {{
            "goal": "deliver_water" | "pick_object" | "navigate_and_return" | "generic_task",
            "object": "name of object (e.g. glass, bottle) or null",
            "contents": "contents of object (e.g. water, juice) or null",
            "destination": "user, kitchen, etc.",
            "constraints": ["constraint1", "constraint2", ...]
        }}
        """

    def _get_replanning_prompt(self, failed_task: str, reason: str, memory_context: Dict[str, Any]) -> str:
        return f"""
        You are the robotic task failure recovery module. 
        A task '{failed_task}' failed because of '{reason}'.
        Robot memory state: {json.dumps(memory_context)}
        
        Generate a list of search actions to find the target object or resolve the failure.
        Provide JSON output matching:
        {{
            "recovery_steps": [
                {{"action": "Navigate", "parameters": {{"destination": "location_name"}}}},
                {{"action": "Detect", "parameters": {{"object": "object_name"}}}}
            ]
        }}
        """
