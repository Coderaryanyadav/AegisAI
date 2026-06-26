import httpx
import json
import logging
from typing import List, Dict, Any, Optional
import os
from aegis_backend.core.http_client import get_http_client

logger = logging.getLogger("aegis_ai.ollama_service")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

class OllamaService:
    """Manages 100% offline interactions with local Ollama runtime using connection pooling."""

    @staticmethod
    async def get_available_models() -> List[str]:
        """Fetches list of models currently pulled in local Ollama."""
        try:
            client = get_http_client()
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models
            return []
        except Exception as e:
            logger.warning(f"Failed to connect to local Ollama service: {e}")
            return []

    @classmethod
    async def generate_completion(
        cls,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> str:
        """Sends a text completion request to the local Ollama model."""
        try:
            available = await cls.get_available_models()
        except Exception as e:
            logger.warning(f"Error checking available models for fallback: {e}")
            available = []

        models_to_try = []
        if available:
            requested_base = model.split(":")[0].lower()
            matched = None
            
            if model in available:
                matched = model
            else:
                for m in available:
                    if requested_base in m.lower():
                        matched = m
                        break
                
                if not matched:
                    for keyword in ["llama", "mistral", "qwen", "deepseek", "phi"]:
                        for m in available:
                            if keyword in m.lower():
                                matched = m
                                break
                        if matched:
                            break
                            
                if not matched:
                    matched = available[0]
            
            models_to_try.append(matched)
            for m in available:
                if m not in models_to_try:
                    models_to_try.append(m)
        else:
            models_to_try.append(model)

        last_exception = None
        for current_model in models_to_try:
            payload = {
                "model": current_model,
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
                default_timeout = float(os.environ.get("OLLAMA_DEFAULT_TIMEOUT", "180"))
                client = get_http_client()
                response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=default_timeout)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
                else:
                    raise RuntimeError(f"Ollama API returned error: {response.text}")
            except Exception as e:
                logger.warning(f"Generation failed with model '{current_model}': {e}. Attempting fallback to next model...")
                last_exception = e
                continue
                
        test_mode = os.environ.get("AEGIS_TEST_MODE") == "true"
        if not test_mode:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Local AI inference service (Ollama) is offline or unavailable. Please ensure the Ollama app is running."
            )

        # Delegate mock generation to the new core mock module to keep this clean
        from aegis_backend.core.mock_ollama import get_mock_completion
        return get_mock_completion(prompt, system_prompt, json_mode)

    @classmethod
    async def generate_structured(
        cls,
        model: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        schema_hint: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Queries Ollama and ensures the response is parsed as a JSON object."""
        resolved_model = model_name or model
        resolved_prompt = prompt or user_prompt or ""
        if schema_hint:
            resolved_prompt = f"{resolved_prompt}\n\nSchema Hint:\n{schema_hint}\n\nJSON Output:"

        result = await cls.generate_completion(
            model=resolved_model,
            prompt=resolved_prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=temperature
        )
        try:
            parsed = json.loads(result)
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")
            if schema_hint:
                try:
                    schema_dict = json.loads(schema_hint)
                    if isinstance(schema_dict, dict):
                        # Ensure all keys in schema_hint are present in the parsed result
                        for k, v in schema_dict.items():
                            if k not in parsed:
                                parsed[k] = v
                except Exception:
                    pass
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to decode JSON from Ollama response: {result}. Error: {e}")
            if schema_hint:
                try:
                    return json.loads(schema_hint)
                except Exception:
                    pass
            return {"raw_response": result, "error": "Invalid JSON returned from model"}

    @staticmethod
    async def is_ollama_running() -> bool:
        """Checks if local Ollama service is running and responsive."""
        try:
            client = get_http_client()
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

    @classmethod
    async def generate_completion_stream(
        cls,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ):
        """Sends a text completion request to the local Ollama model and streams response."""
        try:
            available = await cls.get_available_models()
        except Exception:
            available = []
        
        current_model = model
        if available:
            requested_base = model.split(":")[0].lower()
            matched = None
            if model in available:
                matched = model
            else:
                for m in available:
                    if requested_base in m.lower():
                        matched = m
                        break
                if not matched:
                    matched = available[0]
            current_model = matched

        payload = {
            "model": current_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        client = get_http_client()
        try:
            async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=180.0) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                yield data.get("response", "")
                            except Exception:
                                pass
                else:
                    yield f"Error from Ollama: {response.status_code}"
        except Exception as e:
            logger.error(f"Streaming request failed: {e}")
            yield f"Error: connection failed: {e}"

    @staticmethod
    async def pull_model(model: str):
        """Triggers local model download/pull via Ollama with unlimited timeout."""
        payload = {"name": model, "stream": False}
        try:
            logger.info(f"Starting background pull for model: {model}")
            client = get_http_client()
            response = await client.post(f"{OLLAMA_BASE_URL}/api/pull", json=payload, timeout=None)
            if response.status_code == 200:
                logger.info(f"Successfully pulled model: {model}")
                return True
            logger.error(f"Failed to pull model: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Error pulling model in background: {e}")
            return False
