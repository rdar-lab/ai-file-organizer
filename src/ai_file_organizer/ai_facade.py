"""AI facade module for LLM integration using langchain."""

import os
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage


class AIFacade:
    """Facade for AI/LLM operations using langchain."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AI facade with configuration.
        
        Args:
            config: Configuration dictionary with LLM settings
                - provider: 'openai', 'azure', or 'local'
                - model: Model name
                - temperature: Temperature setting
                - api_key: API key (for OpenAI/Azure)
                - azure_endpoint: Azure endpoint (for Azure)
                - base_url: Base URL (for local LLM)
        """
        self.config = config
        self.provider = config.get('provider', 'openai')
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the LLM based on provider configuration."""
        if self.provider == 'openai':
            return ChatOpenAI(
                model=self.config.get('model', 'gpt-3.5-turbo'),
                temperature=self.config.get('temperature', 0.3),
                api_key=self.config.get('api_key', os.getenv('OPENAI_API_KEY'))
            )
        elif self.provider == 'azure':
            return AzureChatOpenAI(
                deployment_name=self.config.get('deployment_name'),
                model=self.config.get('model', 'gpt-3.5-turbo'),
                temperature=self.config.get('temperature', 0.3),
                api_key=self.config.get('api_key', os.getenv('AZURE_OPENAI_API_KEY')),
                azure_endpoint=self.config.get('azure_endpoint', os.getenv('AZURE_OPENAI_ENDPOINT'))
            )
        elif self.provider == 'local':
            # For local LLMs (Llama, etc.)
            return ChatOpenAI(
                model=self.config.get('model', 'llama2'),
                temperature=self.config.get('temperature', 0.3),
                base_url=self.config.get('base_url', 'http://localhost:8000/v1'),
                api_key=self.config.get('api_key', 'not-needed')
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def categorize_file(self, file_info: Dict[str, Any], labels: list) -> str:
        """
        Categorize a file using the LLM.
        
        Args:
            file_info: Dictionary containing file information
            labels: List of possible category labels
            
        Returns:
            The category label chosen by the LLM
        """
        system_prompt = f"""You are a file categorization assistant. Your job is to categorize files into one of the following categories: {', '.join(labels)}.

Analyze the file information provided and choose the most appropriate category. Respond with ONLY the category name, nothing else."""

        user_prompt = f"""File Information:
- Filename: {file_info.get('filename', 'Unknown')}
- File Type: {file_info.get('file_type', 'Unknown')}
- File Size: {file_info.get('file_size', 'Unknown')} bytes
- MIME Type: {file_info.get('mime_type', 'Unknown')}
- Is Executable: {file_info.get('is_executable', False)}
"""
        
        if file_info.get('archive_contents'):
            user_prompt += f"\nArchive Contents:\n{file_info['archive_contents']}"
        
        if file_info.get('metadata'):
            user_prompt += f"\nAdditional Metadata:\n{file_info['metadata']}"
        
        user_prompt += f"\n\nChoose one category from: {', '.join(labels)}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = self.llm.invoke(messages)
        category = response.content.strip()
        
        # Validate that the response is one of the labels
        if category not in labels:
            # Try to find a match (case-insensitive)
            for label in labels:
                if label.lower() == category.lower():
                    return label
            # Default to first label if no match
            return labels[0]
        
        return category
