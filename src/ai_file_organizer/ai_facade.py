"""AI facade module for LLM integration using langchain."""

import logging
import os
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

logger = logging.getLogger(__name__)


class AIFacade:
    """Facade for AI/LLM operations using langchain."""

    def __init__(self, config: Dict[str, Any]):
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
        """
        self.config = config
        self.provider = config.get("provider", "openai")
        self.llm = self._initialize_llm()
        # Create lowercase label mapping for efficient case-insensitive matching
        self._label_map = {}

    def _initialize_llm(self):
        """Initialize the LLM based on provider configuration."""
        if self.provider == "openai":
            return ChatOpenAI(
                model=self.config.get("model", "gpt-3.5-turbo"),
                temperature=self.config.get("temperature", 0.3),
                api_key=self.config.get("api_key", os.getenv("OPENAI_API_KEY")),
            )
        elif self.provider == "azure":
            return AzureChatOpenAI(
                deployment_name=self.config.get("deployment_name"),
                model=self.config.get("model", "gpt-3.5-turbo"),
                temperature=self.config.get("temperature", 0.3),
                api_key=self.config.get("api_key", os.getenv("AZURE_OPENAI_API_KEY")),
                azure_endpoint=self.config.get(
                    "azure_endpoint", os.getenv("AZURE_OPENAI_ENDPOINT")
                ),
            )
        elif self.provider == "google":
            return ChatGoogleGenerativeAI(
                model=self.config.get("model", "gemini-pro"),
                temperature=self.config.get("temperature", 0.3),
                google_api_key=self.config.get(
                    "api_key", os.getenv("GOOGLE_API_KEY")
                ),
            )
        elif self.provider == "local":
            # For local LLMs (Llama, etc.)
            return ChatOpenAI(
                model=self.config.get("model", "llama2"),
                temperature=self.config.get("temperature", 0.3),
                base_url=self.config.get("base_url", "http://localhost:8000/v1"),
                api_key=self.config.get("api_key", "not-needed"),
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def categorize_file(self, file_info: dict, categories: list) -> str:
        """
        Categorize a file using the LLM.
        Args:
            file_info (dict): Information about the file.
            categories (list): List of possible categories.
        Returns:
            str: The category assigned by the LLM, or None if not confidently determined.
        """
        # Improved prompt with one-shot example
        example_file = {
            "filename": "doc1.txt",
            "file_path": "/input/doc1.txt",
            "file_size": 34,
            "file_type": ".txt",
            "mime_type": "text/plain",
            "is_executable": False,
            "metadata": {
                "created": 1768924483.5866325,
                "modified": 1768924483.5866325,
                "accessed": 1768924555.676632,
                "mode": "0o100646",
            },
        }
        example_categories = ["Documents", "Images", "Videos", "Other"]
        example_category = "Documents"

        prompt = (
            "You are an expert at organizing files. "
            f"Given the following file information, choose the most appropriate category from the list of categories. "
            "Return only the category name, and nothing else.\n"
            "Example:\n"
            f'Categories: {", ".join(example_categories)}\n'
            f"File information: {example_file}\n"
            f"Category: {example_category}\n"
            "Now categorize this file:\n"
            f'Categories: {", ".join(categories)}\n'
            f"File information: {file_info}\n"
            "Category:"
        )
        logger.info(f"LLM prompt: {prompt}")
        raw_response = self.llm.invoke(prompt)
        response = raw_response.content.strip()
        logger.info(f"LLM response: {response}")

        # Direct match
        if response in categories:
            return response
        # Fallback: search for category names in the response (case-insensitive, whole word)
        import re

        found = []
        for cat in categories:
            # Use word boundaries to avoid partial matches
            if re.search(rf"\b{re.escape(cat)}\b", response, re.IGNORECASE):
                found.append(cat)
        if len(found) == 1:
            return found[0]
        # If none or multiple categories found, do nothing (return None)
        return None
