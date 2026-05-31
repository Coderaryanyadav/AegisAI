import httpx
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("aegis_ai.ollama_service")

OLLAMA_BASE_URL = "http://localhost:11434"

class OllamaService:
    """Manages 100% offline interactions with local Ollama runtime."""

    @staticmethod
    async def get_available_models() -> List[str]:
        """Fetches list of models currently pulled in local Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    return models
                return []
        except Exception as e:
            logger.warning(f"Failed to connect to local Ollama service: {e}")
            return []

    @staticmethod
    async def generate_completion(
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> str:
        """Sends a text completion request to the local Ollama model."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
                else:
                    raise RuntimeError(f"Ollama API returned error: {response.text}")
        except Exception as e:
            logger.error(f"Error querying Ollama API: {e}")
            raise RuntimeError(
                f"Local AI inference failed. Verify Ollama is running offline on port 11434. Details: {e}"
            )

    @classmethod
    async def generate_structured(
        cls,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Queries Ollama and ensures the response is parsed as a JSON object."""
        result = await cls.generate_completion(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=temperature
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from Ollama response: {result}. Error: {e}")
            # Fallback wrapper
            return {"raw_response": result, "error": "Invalid JSON returned from model"}

    @staticmethod
    async def is_ollama_running() -> bool:
        """Checks if local Ollama service is running and responsive."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def pull_model(model: str):
        """Triggers local model download/pull via Ollama with unlimited timeout."""
        payload = {"name": model, "stream": False}
        try:
            logger.info(f"Starting background pull for model: {model}")
            async with httpx.AsyncClient(timeout=None) as client:
                response = await client.post(f"{OLLAMA_BASE_URL}/api/pull", json=payload)
                if response.status_code == 200:
                    logger.info(f"Successfully pulled model: {model}")
                    return True
                logger.error(f"Failed to pull model: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error pulling model in background: {e}")
            return False
