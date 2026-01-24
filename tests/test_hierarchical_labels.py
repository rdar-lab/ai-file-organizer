"""Tests for hierarchical label functionality."""

import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from ai_file_organizer.organizer import FileOrganizer
from ai_file_organizer.ai_facade import AIFacade


class TestHierarchicalLabels:
    """Test hierarchical label support."""
    
    def test_init_with_hierarchical_labels(self):
        """Test initialization with hierarchical labels dict."""
        ai_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        labels = {
            'Documents': ['Work', 'Personal'],
            'Images': ['Photos', 'Screenshots'],
            'Videos': []
        }
        
        with patch('ai_file_organizer.organizer.AIFacade'):
            with patch('ai_file_organizer.organizer.FileAnalyzer'):
                organizer = FileOrganizer(ai_config, labels, '.', None, dry_run=True)
                assert organizer.labels == {
                    'Documents': ['Work', 'Personal'],
                    'Images': ['Photos', 'Screenshots'],
                    'Videos': [],
                    'Other': []
                }
    
    def test_categorize_file_with_hierarchical_labels(self):
        """Test file categorization with hierarchical labels."""
        config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        
        file_info = {
            'filename': 'work_document.pdf',
            'file_type': '.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf',
            'is_executable': False
        }
        
        labels = {
            'Documents': ['Work', 'Personal'],
            'Images': [],
            'Videos': []
        }
        
        # Mock the LLM to return hierarchical category
        mock_response = Mock()
        mock_response.content = 'Documents/Work'
        
        with patch('ai_file_organizer.ai_facade.ChatOpenAI') as mock_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_openai.return_value = mock_llm
            
            facade = AIFacade(config)
            category = facade.categorize_file(file_info, labels)
            
            assert category == 'Documents/Work'
    
    def test_categorize_file_main_category_only(self):
        """Test that LLM can return just main category when no sub-category fits."""
        config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        
        file_info = {
            'filename': 'misc_document.pdf',
            'file_type': '.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf',
            'is_executable': False
        }
        
        labels = {
            'Documents': ['Work', 'Personal'],
            'Images': [],
            'Videos': []
        }
        
        # Mock the LLM to return just main category
        mock_response = Mock()
        mock_response.content = 'Documents'
        
        with patch('ai_file_organizer.ai_facade.ChatOpenAI') as mock_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_openai.return_value = mock_llm
            
            facade = AIFacade(config)
            category = facade.categorize_file(file_info, labels)
            
            assert category == 'Documents'
    
    def test_organize_files_with_hierarchical_labels(self):
        """Test file organization with hierarchical labels creates nested directories."""
        ai_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        labels = {
            'Documents': ['Work', 'Personal'],
            'Images': []
        }
        
        # Create temporary directories
        input_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        
        try:
            # Create test file
            test_file = os.path.join(input_dir, 'work_doc.txt')
            with open(test_file, 'w') as f:
                f.write('test content')
            
            # Mock AI facade and file analyzer
            mock_ai_facade = Mock()
            mock_ai_facade.categorize_file.return_value = 'Documents/Work'
            
            mock_file_analyzer = Mock()
            mock_file_analyzer.analyze_file.return_value = {
                'filename': 'work_doc.txt',
                'file_type': '.txt',
                'file_size': 100,
                'mime_type': 'text/plain',
                'is_executable': False
            }
            
            with patch('ai_file_organizer.organizer.AIFacade', return_value=mock_ai_facade):
                with patch('ai_file_organizer.organizer.FileAnalyzer', return_value=mock_file_analyzer):
                    organizer = FileOrganizer(ai_config, labels, input_dir, output_dir, dry_run=False)
                    stats = organizer.organize_files()
                    
                    # Check stats
                    assert stats['total_files'] == 1
                    assert stats['processed'] == 1
                    assert stats['failed'] == 0
                    
                    # File should be moved to nested directory
                    assert not os.path.exists(test_file)
                    nested_path = os.path.join(output_dir, 'Documents', 'Work', 'work_doc.txt')
                    assert os.path.exists(nested_path)
        
        finally:
            shutil.rmtree(input_dir, ignore_errors=True)
            shutil.rmtree(output_dir, ignore_errors=True)
    
    def test_categorize_file_invalid_subcategory(self):
        """Test that invalid sub-category falls back to main category."""
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
        
        labels = {
            'Documents': ['Work', 'Personal'],
            'Images': []
        }
        
        # Mock the LLM to return invalid sub-category
        mock_response = Mock()
        mock_response.content = 'Documents/Invalid'
        
        with patch('ai_file_organizer.ai_facade.ChatOpenAI') as mock_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_openai.return_value = mock_llm
            
            facade = AIFacade(config)
            category = facade.categorize_file(file_info, labels)
            
            # Should fall back to main category
            assert category == 'Documents'
    
    def test_backward_compatibility_flat_list(self):
        """Test that flat list labels still work (backward compatibility)."""
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
        
        # Use flat list (old format)
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
