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
                google_api_key=self.config.get("api_key", os.getenv("GOOGLE_API_KEY")),
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

    def categorize_file(self, file_info: dict, categories) -> str:
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
        if isinstance(categories, list):
            categories_dict = {cat: [] for cat in categories}
        else:
            categories_dict = categories
        
        # Build hierarchical category list for prompt
        category_list = []
        for main_cat, sub_cats in categories_dict.items():
            if sub_cats:
                # Add parent category with its sub-categories
                sub_cat_str = ", ".join(sub_cats)
                category_list.append(f"{main_cat} (sub-categories: {sub_cat_str})")
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
        example_categories = {"Documents": ["Work", "Personal"], "Images": [], "Videos": [], "Other": []}
        example_category_list = [
            "Documents (sub-categories: Work, Personal)",
            "Images",
            "Videos",
            "Other"
        ]
        example_category = "Documents/Work"

        prompt = (
            "You are an expert at organizing files. "
            "Given the following file information, choose the most appropriate category from the list of categories. "
            "If a category has sub-categories, choose the most specific sub-category using the format 'Category/SubCategory'. "
            "If no sub-category fits, use just the main category name. "
            "Return only the category name (or category/sub-category), and nothing else.\n\n"
            "Example:\n"
            f'Categories: {", ".join(example_category_list)}\n'
            f"File information: {example_file}\n"
            f"Category: {example_category}\n\n"
            "Now categorize this file:\n"
            f'Categories: {", ".join(category_list)}\n'
            f"File information: {file_info}\n"
            "Category:"
        )
        logger.info(f"LLM prompt: {prompt}")
        raw_response = self.llm.invoke(prompt)
        response = raw_response.content.strip()
        logger.info(f"LLM response: {response}")

        # Parse response - could be "Category" or "Category/SubCategory"
        response_parts = response.split("/")
        main_category = response_parts[0].strip()
        sub_category = response_parts[1].strip() if len(response_parts) > 1 else None
        
        # Validate response against available categories
        import re
        
        # Try direct match first (case-sensitive)
        if main_category in categories_dict:
            if sub_category:
                # Validate sub-category exists
                if sub_category in categories_dict[main_category]:
                    return f"{main_category}/{sub_category}"
                else:
                    # Sub-category not found, return just main category
                    logger.warning(f"Sub-category '{sub_category}' not found in '{main_category}', using main category only")
                    return main_category
            return main_category
        
        # Try case-insensitive match for main category
        for cat in categories_dict.keys():
            if cat.lower() == main_category.lower():
                if sub_category:
                    # Try case-insensitive match for sub-category
                    for sub_cat in categories_dict[cat]:
                        if sub_cat.lower() == sub_category.lower():
                            return f"{cat}/{sub_cat}"
                    # Sub-category not found, return just main category
                    logger.warning(f"Sub-category '{sub_category}' not found in '{cat}', using main category only")
                return cat
        
        # Fallback: search for category names in the response (whole word)
        found = []
        for cat in categories_dict.keys():
            # Use word boundaries to avoid partial matches
            if re.search(rf"\b{re.escape(cat)}\b", response, re.IGNORECASE):
                found.append(cat)
        if len(found) == 1:
            return found[0]
        
        # If none or multiple categories found, return None
        return None
