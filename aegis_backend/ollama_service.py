import httpx
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import os
import re
from fastapi import HTTPException, status
from aegis_backend.core.http_client import get_http_client
from aegis_backend.core.memory_guard import MemoryGuard

logger = logging.getLogger("aegis_ai.ai_service")

LMSTUDIO_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

def clean_json_text(text: str) -> str:
    """Extracts clean JSON string even if wrapped in markdown code blocks or conversational text."""
    text = text.strip()
    # Check for markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    # Find outer JSON boundaries ({...} or [...])
    boundary_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if boundary_match:
        return boundary_match.group(1).strip()
    return text

class LocalAIService:
    """Manages 100% offline interactions with LM Studio (primary) and Ollama (fallback)

    providing high-performance, GPU-accelerated local inference.
    """

    @staticmethod
    async def is_lmstudio_running() -> bool:
        """Checks if local LM Studio API server is responsive on port 1234."""
        try:
            client = get_http_client()
            res = await client.get(f"{LMSTUDIO_BASE_URL}/models", timeout=2.0)
            return res.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def is_ollama_running() -> bool:
        """Checks if local Ollama service is responsive on port 11434."""
        try:
            client = get_http_client()
            res = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
            return res.status_code == 200
        except Exception:
            return False

    @classmethod
    async def is_ai_running(cls) -> bool:
        """Checks if either LM Studio or Ollama is online."""
        if await cls.is_lmstudio_running():
            return True
        return await cls.is_ollama_running()

    @classmethod
    async def get_available_models(cls) -> List[str]:
        """Fetches list of available models from LM Studio or Ollama."""
        client = get_http_client()
        
        # 1. Check LM Studio first
        try:
            response = await client.get(f"{LMSTUDIO_BASE_URL}/models", timeout=4.0)
            if response.status_code == 200:
                data = response.json()
                models = []
                for item in data.get("data", []):
                    model_id = item.get("id", "")
                    # Filter out embedding models from text generation model list
                    if "embed" not in model_id.lower():
                        models.append(model_id)
                if models:
                    return models
                # If only embed models or empty, return raw IDs
                return [item["id"] for item in data.get("data", []) if "id" in item]
        except Exception as e:
            logger.debug(f"LM Studio not reachable: {e}")

        # 2. Check Ollama as fallback
        try:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=4.0)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Ollama not reachable: {e}")

        return []

    @classmethod
    def resolve_model_name(cls, requested: Optional[str], available: List[str]) -> str:
        """Matches requested model name with loaded/available local models."""
        if not available:
            return requested or "qwen2.5-coder-14b-instruct-mlx"
        if requested and requested in available:
            return requested
        
        # Match by substring
        if requested:
            req_clean = requested.split(":")[0].lower().replace("-", "").replace(".", "")
            for m in available:
                m_clean = m.lower().replace("-", "").replace(".", "")
                if req_clean in m_clean or m_clean in req_clean:
                    return m

        # Priority matching for high-performance legal models
        for kw in ["qwen", "deepseek", "llama", "mistral", "phi", "gemma"]:
            for m in available:
                if kw in m.lower():
                    return m

        return available[0]

    @classmethod
    async def generate_completion(
        cls,
        model: Optional[str] = None,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> str:
        """Sends text completion request to LM Studio (primary) or Ollama (fallback)."""
        allowed, reason = MemoryGuard.check_inference_allowed()
        if not allowed:
            raise HTTPException(status_code=503, detail=reason)

        available = await cls.get_available_models()
        target_model = cls.resolve_model_name(model, available)
        client = get_http_client()
        timeout = float(os.environ.get("LOCAL_AI_TIMEOUT", "180"))

        # 1. Attempt LM Studio OpenAI-compatible completion
        if await cls.is_lmstudio_running():
            sys_content = system_prompt or "You are AegisAI, an elite enterprise legal assistant."
            if json_mode and "json" not in sys_content.lower():
                sys_content += "\n\nCRITICAL: Respond ONLY with a valid JSON object. Do not include markdown code blocks or text outside JSON."
            
            messages = [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": prompt}
            ]
            
            payload = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }

            try:
                res = await client.post(f"{LMSTUDIO_BASE_URL}/chat/completions", json=payload, timeout=timeout)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return clean_json_text(content) if json_mode else content.strip()
                else:
                    logger.warning(f"LM Studio returned status {res.status_code}: {res.text}")
            except Exception as e:
                logger.warning(f"LM Studio completion error: {e}. Attempting fallback...")

        # 2. Attempt Ollama completion as fallback
        if await cls.is_ollama_running():
            payload = {
                "model": target_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature}
            }
            if system_prompt:
                payload["system"] = system_prompt
            if json_mode:
                payload["format"] = "json"

            try:
                res = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=timeout)
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
            except Exception as e:
                logger.warning(f"Ollama fallback error: {e}")

        # 3. Check for test mode or offline mock
        if os.environ.get("AEGIS_TEST_MODE") == "true":
            from aegis_backend.core.mock_ollama import get_mock_completion
            return get_mock_completion(prompt, system_prompt, json_mode)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local AI inference engine (LM Studio / Ollama) is offline. Please start LM Studio on port 1234."
        )

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
        """Queries local model and guarantees the response is parsed into a Python dictionary."""
        resolved_model = model_name or model
        resolved_prompt = prompt or user_prompt or ""
        if schema_hint:
            resolved_prompt = f"{resolved_prompt}\n\nRequired JSON Schema:\n{schema_hint}\n\nJSON Output:"

        raw_output = await cls.generate_completion(
            model=resolved_model,
            prompt=resolved_prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=temperature
        )

        cleaned = clean_json_text(raw_output)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                if schema_hint:
                    try:
                        schema_dict = json.loads(schema_hint)
                        if isinstance(schema_dict, dict):
                            for k, v in schema_dict.items():
                                if k not in parsed:
                                    parsed[k] = v
                    except Exception:
                        pass
                return parsed
            elif isinstance(parsed, list):
                return {"items": parsed}
            return {"result": parsed}
        except Exception as e:
            logger.error(f"Failed to parse structured JSON from model: {raw_output}. Error: {e}")
            if schema_hint:
                try:
                    return json.loads(schema_hint)
                except Exception:
                    pass
            return {"raw_response": raw_output, "error": "Invalid JSON format returned"}

    @classmethod
    async def generate_completion_stream(
        cls,
        model: Optional[str] = None,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """Streams text completion tokens from LM Studio (primary) or Ollama (fallback)."""
        allowed, reason = MemoryGuard.check_inference_allowed()
        if not allowed:
            yield f"Error: {reason}"
            return

        available = await cls.get_available_models()
        target_model = cls.resolve_model_name(model, available)
        client = get_http_client()

        # 1. Stream from LM Studio (OpenAI SSE format)
        if await cls.is_lmstudio_running():
            sys_content = system_prompt or "You are AegisAI, an elite enterprise legal assistant."
            messages = [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": prompt}
            ]
            payload = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }

            try:
                async with client.stream("POST", f"{LMSTUDIO_BASE_URL}/chat/completions", json=payload, timeout=180.0) as res:
                    if res.status_code == 200:
                        async for line in res.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        yield delta
                                except Exception:
                                    continue
                        return
                    else:
                        yield f"Error from LM Studio (Status {res.status_code})"
                        return
            except Exception as e:
                logger.error(f"LM Studio stream failure: {e}")
                yield f"Error: stream connection failed: {e}"
                return

        # 2. Stream from Ollama as fallback
        if await cls.is_ollama_running():
            payload = {
                "model": target_model,
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": temperature}
            }
            if system_prompt:
                payload["system"] = system_prompt

            try:
                async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=180.0) as res:
                    if res.status_code == 200:
                        async for line in res.aiter_lines():
                            if line:
                                try:
                                    data = json.loads(line)
                                    token = data.get("response", "")
                                    if token:
                                        yield token
                                except Exception:
                                    pass
                        return
                    else:
                        yield f"Error from Ollama: {res.status_code}"
                        return
            except Exception as e:
                logger.error(f"Ollama stream failure: {e}")
                yield f"Error: stream connection failed: {e}"
                return

        # 3. Test mode fallback
        if os.environ.get("AEGIS_TEST_MODE") == "true":
            from aegis_backend.core.mock_ollama import get_mock_completion
            yield get_mock_completion(prompt, system_prompt, False)
        else:
            yield "Error: Local AI inference service is offline. Please start LM Studio on port 1234."

    @staticmethod
    async def pull_model(model: str) -> bool:
        """Triggers local model download/load via Ollama or LM Studio CLI."""
        # For Ollama
        try:
            client = get_http_client()
            res = await client.post(f"{OLLAMA_BASE_URL}/api/pull", json={"name": model, "stream": False}, timeout=None)
            return res.status_code == 200
        except Exception:
            return False

# Backward-compatible aliases for existing routers, tests, and services
OllamaService = LocalAIService
LMStudioService = LocalAIService
