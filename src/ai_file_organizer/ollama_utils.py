import logging
import os
import time
from typing import Any, Dict
from urllib.parse import urlparse

import requests
from requests import Response

logger = logging.getLogger(__name__)


def ensure_ollama_model_available_if_local(config: Dict[str, Any], *, timeout_seconds: int = 600):
    """Ensure Ollama model is available when using a local provider.

    This helper will attempt to reach the Ollama HTTP API (default: http://ollama:11434),
    list available models, request a pull if the requested model is missing, and wait
    until the model is listed or timeout expires.

    It is intentionally tolerant: it logs warnings on failures and returns without
    raising so application startup doesn't hard-fail if Ollama isn't reachable.
    """
    provider = config.get("provider")

    # Skip unless configured to use local provider
    if provider != "local":
        return

    model_name = config.get("model") or os.getenv("OLLAMA_MODEL")
    if not model_name:
        raise Exception("Local provider configured but no model specified")

    # If ensure_model is disabled, skip
    ensure_model = config.get("ensure_model", "0")
    if not ensure_model:
        return

    # Allow operator to opt-out (useful in some dev scenarios)
    if os.getenv("SKIP_OLLAMA_INIT", "false").lower() in ("1", "true", "yes"):
        return

    ollama_base = _get_ollama_base(config)

    # Wait for Ollama API to be reachable
    _wait_for_ollama_api(ollama_base, timeout_seconds=timeout_seconds)

    if _check_if_model_available(ollama_base, model_name):
        logger.info("Model %s already present in Ollama", model_name)
        return

    _pull_model(ollama_base, model_name, timeout_seconds=timeout_seconds)

    _wait_for_model_to_be_available(ollama_base, model_name, timeout_seconds=timeout_seconds)


def _wait_for_model_to_be_available(ollama_base: str, model_name: str, timeout_seconds):
    # Poll until model appears or timeout
    start = time.time()
    while time.time() - start < timeout_seconds:
        # noinspection PyBroadException
        try:
            if _check_if_model_available(ollama_base, model_name):
                logger.info("Model %s is now available in Ollama", model_name)
                return
        except Exception:
            pass
        time.sleep(2)

    raise Exception(f"Timed out waiting for Ollama model {model_name} after {timeout_seconds} seconds")


def _wait_for_ollama_api(ollama_base: str, timeout_seconds: int = 120):
    # Wait for Ollama API to be reachable
    logger.info("Waiting for Ollama API at %s...", ollama_base)
    for _ in range(int(timeout_seconds / 2)):
        # noinspection PyBroadException
        try:
            resp = _get_tags(ollama_base)
            if resp.status_code == 200:
                logger.info("Ollama API is reachable")
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        raise Exception(f"Ollama API at {ollama_base} did not become reachable")


def _pull_model(ollama_base: str, model_name: str, timeout_seconds):
    # Request model pull (don't fail hard if this fails)
    logger.info("Requesting Ollama pull for model %s", model_name)
    try:
        response = requests.post(
            f"{ollama_base}/api/pull",
            json={"name": model_name},
            timeout=timeout_seconds,
        )
        if response.status_code != 200:
            raise Exception(f"Unexpected status code {response.status_code} - {response.text}")
    except Exception as exc:
        raise Exception(f"Failed to request Ollama pull: {repr(exc)}")


def _get_ollama_base(config) -> str:
    base_url = config.get("base_url", os.getenv("OLLAMA_URL", "http://localhost:11434/v1"))

    # If base_url points to an inference endpoint like http://ollama:11434/v1, derive the
    # Ollama management API host (scheme://netloc) so we can call /api/tags and /api/pull.
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.netloc and parsed.path and parsed.path.strip("/").startswith("v1"):
        ollama_base = f"{parsed.scheme}://{parsed.netloc}"
    else:
        ollama_base = base_url.rstrip("/")
    return ollama_base


def _check_if_model_available(ollama_base: str, model_name: str) -> bool:
    response = _get_tags(ollama_base)
    if response.status_code != 200:
        raise Exception(f"Unexpected status code {response.status_code} - {response.text}")
    models = response.json().get("models", [])
    model_exists = any(model["name"].startswith(model_name) for model in models)
    return model_exists


def _get_tags(ollama_base: str) -> Response:
    response = requests.get(f"{ollama_base}/api/tags", timeout=5)
    return response
