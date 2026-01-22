"""Tests for AI facade module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_file_organizer.ai_facade import AIFacade


class TestAIFacade:
    """Test AIFacade class."""
    
    def test_init_openai_provider(self):
        """Test initialization with OpenAI provider."""
        config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'temperature': 0.3,
            'api_key': 'test-key'
        }
        
        with patch('ai_file_organizer.ai_facade.ChatOpenAI') as mock_openai:
            facade = AIFacade(config)
            assert facade.provider == 'openai'
            mock_openai.assert_called_once()
    
    def test_init_azure_provider(self):
        """Test initialization with Azure provider."""
        config = {
            'provider': 'azure',
            'model': 'gpt-35-turbo',
            'temperature': 0.3,
            'api_key': 'test-key',
            'azure_endpoint': 'https://test.openai.azure.com/',
            'deployment_name': 'test-deployment'
        }
        
        with patch('ai_file_organizer.ai_facade.AzureChatOpenAI') as mock_azure:
            facade = AIFacade(config)
            assert facade.provider == 'azure'
            mock_azure.assert_called_once()
    
    def test_init_google_provider(self):
        """Test initialization with Google Gemini provider."""
        config = {
            'provider': 'google',
            'model': 'gemini-pro',
            'temperature': 0.3,
            'api_key': 'test-key'
        }
        
        with patch('ai_file_organizer.ai_facade.ChatGoogleGenerativeAI') as mock_google:
            facade = AIFacade(config)
            assert facade.provider == 'google'
            mock_google.assert_called_once()
    
    def test_init_local_provider(self):
        """Test initialization with local provider."""
        config = {
            'provider': 'local',
            'model': 'llama2',
            'temperature': 0.3,
            'base_url': 'http://localhost:8000/v1'
        }
        
        with patch('ai_file_organizer.ai_facade.ChatOpenAI') as mock_openai:
            facade = AIFacade(config)
            assert facade.provider == 'local'
            mock_openai.assert_called_once()
    
    def test_init_invalid_provider(self):
        """Test initialization with invalid provider."""
        config = {
            'provider': 'invalid',
            'model': 'test-model'
        }
        
        with pytest.raises(ValueError, match="Unsupported provider"):
            AIFacade(config)
    
    def test_categorize_file(self):
        """Test file categorization."""
        config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        
        file_info = {
            'filename': 'document.pdf',
            'file_type': '.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf',
            'is_executable': False
        }
        
        labels = ['Documents', 'Images', 'Videos']
        
        # Mock the LLM
        mock_response = Mock()
        mock_response.content = 'Documents'
        
        with patch('ai_file_organizer.ai_facade.ChatOpenAI') as mock_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_openai.return_value = mock_llm
            
            facade = AIFacade(config)
            category = facade.categorize_file(file_info, labels)
            
            assert category == 'Documents'
            mock_llm.invoke.assert_called_once()
    
    def test_categorize_file_case_insensitive(self):
        """Test file categorization with case-insensitive matching."""
        config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        
        file_info = {
            'filename': 'document.pdf',
            'file_type': '.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf',
            'is_executable': False
        }
        
        labels = ['Documents', 'Images', 'Videos']
        
        # Mock the LLM to return lowercase
        mock_response = Mock()
        mock_response.content = 'documents'
        
        with patch('ai_file_organizer.ai_facade.ChatOpenAI') as mock_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_openai.return_value = mock_llm
            
            facade = AIFacade(config)
            category = facade.categorize_file(file_info, labels)
            
            assert category == 'Documents'
    
    def test_categorize_file_invalid_response(self):
        """Test file categorization with invalid LLM response."""
        config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        
        file_info = {
            'filename': 'document.pdf',
            'file_type': '.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf',
            'is_executable': False
        }
        
        labels = ['Documents', 'Images', 'Videos']
        
        # Mock the LLM to return invalid category
        mock_response = Mock()
        mock_response.content = 'InvalidCategory'
        
        with patch('ai_file_organizer.ai_facade.ChatOpenAI') as mock_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_openai.return_value = mock_llm
            
            facade = AIFacade(config)
            category = facade.categorize_file(file_info, labels)
            
            # Should default to first label
            assert category is None
