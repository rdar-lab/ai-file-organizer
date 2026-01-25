"""AI facade module for LLM integration using langchain."""

import datetime
import logging
import os
import random
import re
import threading
import time
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from .ollama_utils import ensure_ollama_model_available

logger = logging.getLogger(__name__)


class AIFacade:
    """Facade for AI/LLM operations using langchain."""

    def __init__(self, config: Dict[str, Any], cancel_event: Optional[threading.Event] = None):
        """
        Initialize AI facade with configuration.

        Args:
            config: Configuration dictionary with LLM settings
                - provider: 'openai', 'azure', 'google', or 'local'
                - model: Model name
                - temperature: Temperature setting
                - api_key: API key (for OpenAI/Azure/Google)
                - azure_endpoint: Azure endpoint (for Azure)
                - base_url: Base URL (for local LLM)
                - retries: (optional) number of retry attempts for LLM calls
                - backoff_factor: (optional) base backoff multiplier in seconds
                - max_backoff: (optional) maximum backoff in seconds
                - backoff_factor_rate_limit: (optional) base backoff multiplier in seconds - in rate-limit scenarios
                - max_backoff_rate_limit: (optional) maximum backoff in seconds - in rate-limit scenarios
            cancel_event: Optional threading.Event to support cancellation.
        """
        self._cancel_event = cancel_event
        self.config = config
        self.provider = config.get("provider", "openai")

        self.llm = self._initialize_llm()
        # Create lowercase label mapping for efficient case-insensitive matching
        self._label_map = {}

        # Retry configuration (kept small by default so unit tests run fast)
        self._retries = int(config.get("retries", 2))
        self._backoff_factor = float(config.get("backoff_factor", 1.0))
        self._max_backoff = float(config.get("max_backoff", 60.0))
        # Allow a larger max backoff specifically for rate-limited (429) responses
        # This helps when providers return Retry-After headers or when quota throttles
        # require longer pauses. Default is conservative but configurable.
        self._backoff_factor_rate_limit = float(config.get("backoff_factor_rate_limit", 10.0))
        self._max_backoff_rate_limit = float(config.get("max_backoff_rate_limit", 120.0))

    def _read_config(self, config_value, default_value=None):
        val = self.config.get(config_value)
        if val is not None and str(val).strip() != "":
            return val
        else:
            return default_value

    def _initialize_llm(self):
        """Initialize the LLM based on provider configuration."""
        if self.provider == "openai":
            api_key = self._read_config("api_key", os.getenv("AZURE_OPENAI_API_KEY"))
            if not api_key:
                raise ValueError("API key is required for OpenAI provider")
            return ChatOpenAI(
                model=self._read_config("model", "gpt-3.5-turbo"),
                temperature=self._read_config("temperature", 0.3),
                api_key=api_key,
            )
        elif self.provider == "azure":
            api_key = self._read_config("api_key", os.getenv("AZURE_OPENAI_API_KEY"))
            if not api_key:
                raise ValueError("API key is required for Azure provider")

            azure_endpoint_def = self._read_config("azure_endpoint", os.getenv("AZURE_OPENAI_ENDPOINT"))
            if not azure_endpoint_def:
                raise ValueError("Azure endpoint is required for Azure provider")

            return AzureChatOpenAI(
                azure_deployment=self._read_config("deployment_name"),
                model=self._read_config("model", "gpt-3.5-turbo"),
                temperature=self._read_config("temperature", 0.3),
                api_key=api_key,
                azure_endpoint=azure_endpoint_def,
            )
        elif self.provider == "google":
            api_key = self._read_config("api_key", os.getenv("GOOGLE_API_KEY"))
            if not api_key:
                raise ValueError("API key is required for Google provider")

            return ChatGoogleGenerativeAI(
                model=self._read_config("model", "gemini-pro"),
                temperature=self._read_config("temperature", 0.3),
                google_api_key=api_key,
            )
        elif self.provider == "local":
            ensure_ollama_model_available(self.config, cancel_event=self._cancel_event)

            # For local LLMs (Llama, etc.) - base_url can be provided in config or via OLLAMA_URL
            base_url = self._read_config("base_url", os.getenv("OLLAMA_URL", "http://localhost:11434/v1"))
            return ChatOpenAI(
                model=self._read_config("model", "llama2"),
                temperature=self._read_config("temperature", 0.3),
                base_url=base_url,
                api_key=self._read_config("api_key", "not-needed"),
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _invoke_with_retries(self, prompt: str):
        """Invoke the underlying LLM with retries on exception.

        Returns the raw response object from the LLM's invoke() call.
        Retries are performed for exceptions thrown by the LLM client. The
        configuration values from self.config control the retry behaviour.
        """
        attempt = 0
        while True:
            if self._cancel_event is not None and self._cancel_event.is_set():
                raise Exception("Cancelled while waiting for Ollama API")

            try:
                logger.debug("LLM invoke attempt %d", attempt + 1)
                raw_response = self.llm.invoke(prompt)
                return raw_response
            except Exception as exc:
                attempt += 1
                if attempt > self._retries:
                    logger.exception("LLM invoke failed after %d attempts", attempt)
                    raise

                # Detect rate-limit / resource exhausted errors (common signals: 429, 'RESOURCE_EXHAUSTED')
                is_rate_limited, retry_after = self._check_if_rate_limit_error(exc)

                # Compute backoff
                if is_rate_limited:
                    if retry_after is not None:
                        # honor server-provided Retry-After
                        sleep_time = float(retry_after) + random.uniform(0, 0.1 * float(retry_after))
                    else:
                        # Use a larger cap for 429s
                        sleep_time = min(self._max_backoff_rate_limit, self._backoff_factor_rate_limit * (2 ** (attempt - 1)))
                    logger.warning(
                        "LLM invoke rate-limited (attempt %d/%d): %s - retrying in %.2fs",
                        attempt,
                        self._retries,
                        exc,
                        sleep_time,
                    )
                else:
                    # exponential backoff with jitter for non-rate-limit errors
                    sleep_time = min(self._max_backoff, self._backoff_factor * (2 ** (attempt - 1)))
                    logger.warning(
                        "LLM invoke failed (attempt %d/%d): %s - retrying in %.2fs",
                        attempt,
                        self._retries,
                        exc,
                        sleep_time,
                    )

                time.sleep(sleep_time)

    # noinspection PyUnresolvedReferences,PyBroadException
    @staticmethod
    def _check_if_rate_limit_error(exc: Exception) -> tuple[bool, float]:
        is_rate_limited = False
        retry_after = None

        # Try to extract status code or retry headers from common exception shapes
        try:
            # requests / httpx like
            if hasattr(exc, "response") and exc.response is not None:
                resp = exc.response
                # status code attribute
                if hasattr(resp, "status_code"):
                    if int(getattr(resp, "status_code")) == 429:
                        is_rate_limited = True
                # headers
                headers = getattr(resp, "headers", None) or getattr(resp, "headers", {})
                if headers:
                    # header keys can be case-insensitive
                    ra = headers.get("Retry-After") or headers.get("retry-after")
                    if ra is not None:
                        try:
                            retry_after = float(ra)
                        except Exception:
                            # sometimes it's an HTTP-date - parse it and substract current time
                            try:
                                retry_after_dt = parsedate_to_datetime(ra)
                                retry_after = (retry_after_dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                            except Exception:
                                pass
        except Exception:
            # ignore parsing errors and fall back to string matching
            pass

        # Fallback string checks on exception message
        exc_text = str(exc)
        if not is_rate_limited and ("429" in exc_text or "RESOURCE_EXHAUSTED" in exc_text or "quota" in exc_text.lower()):
            is_rate_limited = True

        return is_rate_limited, retry_after

    def categorize_file(self, file_info: dict, categories) -> tuple[Optional[str], Optional[str]]:
        """
        Categorize a file using the LLM.
        Args:
            file_info (dict): Information about the file.
            categories: Either a list of categories or hierarchical dict of categories.
                       List format: ['Documents', 'Images', 'Videos']
                       Dict format: {category: [sub_category1, sub_category2, ...]}
        Returns:
            str: The category assigned by the LLM (e.g., "Documents" or "Documents/Work"),
                 or None if not confidently determined.
        """
        # Normalize categories to dict format
        categories_dict = self._prepare_cat_dict(categories)

        prompt = self._prepare_prompt(categories_dict, file_info)

        logger.info(f"LLM prompt: {prompt}")
        raw_response = self._invoke_with_retries(prompt)
        response = raw_response.content.strip()
        logger.info(f"LLM response: {response}")

        file_name = file_info.get("filename", "unknown")
        return response, self._detect_category_in_response(file_name, categories_dict, response)

    @staticmethod
    def _prepare_prompt(categories_dict: dict[Any, list[Any]], file_info: dict) -> str:
        has_sub_cats = False

        # Build hierarchical category list for prompt
        category_list = []
        for main_cat, sub_cats in categories_dict.items():
            if sub_cats:
                # Add parent category with its sub-categories
                sub_cat_str = ", ".join(sub_cats)
                category_list.append(f"{main_cat} (sub-categories: {sub_cat_str})")
                has_sub_cats = True
            else:
                # Just the parent category
                category_list.append(main_cat)

        # Improved prompt with one-shot example showing hierarchical structure
        example_file = {
            "filename": "work_report.pdf",
            "file_path": "/input/work_report.pdf",
            "file_size": 2048,
            "file_type": ".pdf",
            "mime_type": "application/pdf",
            "is_executable": False,
            "metadata": {
                "created": 1768924483.5866325,
                "modified": 1768924483.5866325,
                "accessed": 1768924555.676632,
                "mode": "0o100646",
            },
        }

        if has_sub_cats:
            example_category_list = [
                "Documents (sub-categories: Work, Personal)",
                "Images",
                "Videos",
                "Other",
            ]
            example_category = "Documents/Work"
        else:
            example_category_list = [
                "Documents",
                "Images",
                "Videos",
                "Other",
            ]
            example_category = "Documents"

        prompt = "You are an expert at organizing files. \n Given the following file information, choose the most appropriate category from the list of categories. \n"

        if has_sub_cats:
            prompt += (
                "If a category has sub-categories, choose the most specific sub-category using the format 'Category/SubCategory'. \n"
                "If no sub-category fits, use just the main category name. \n"
                "Return only the category name (or category/sub-category), and nothing else.\n\n"
            )
        else:
            prompt += "Return only the category name, and nothing else.\n\n"

        prompt += (
            "Example:\n"
            f'Categories: {", ".join(example_category_list)}\n'
            f"File information: {example_file}\n"
            f"Category: {example_category}\n\n"
            "Now categorize this file:\n"
            f'Categories: {", ".join(category_list)}\n'
            f"File information: {file_info}\n"
            "Category:"
        )
        return prompt

    @staticmethod
    def _prepare_cat_dict(categories) -> dict[Any, list[Any]]:
        if isinstance(categories, list):
            categories_dict = {cat: [] for cat in categories}
        else:
            categories_dict = categories
        return categories_dict

    @staticmethod
    def _detect_category_in_response(filename, categories_dict: dict[Any, list[Any]] | Any, response: str) -> Any:
        response_parts = response.split("/")
        main_category = response_parts[0].strip()
        sub_category = response_parts[1].strip() if len(response_parts) > 1 else None

        for cat in categories_dict.keys():
            if cat.lower() == main_category.lower():
                if sub_category:
                    # Try case-insensitive match for sub-category
                    for sub_cat in categories_dict[cat]:
                        if sub_cat.lower() == sub_category.lower():
                            return cat, sub_cat
                    # Sub-category not found, return just main category
                    logger.warning(f"File '{filename}': Sub-category '{sub_category}' not found in '{cat}', using main category only")
                    return cat, None
                return cat, None

        # Fallback: search for category names in the response (whole word) - no hierarchy supported here
        found = []
        for cat in categories_dict.keys():
            # Use word boundaries to avoid partial matches
            if re.search(rf"\b{re.escape(cat)}\b", response, re.IGNORECASE):
                found.append(cat)
        if len(found) == 1:
            return found[0], None

        # If none or multiple categories found, return None
        return None
