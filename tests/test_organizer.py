"""Tests for file organizer module."""

import os
import tempfile
import shutil
import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_file_organizer.organizer import FileOrganizer


class TestFileOrganizer:
    """Test FileOrganizer class."""
    
    def test_init(self):
        """Test initialization."""
        ai_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        labels = ['Documents', 'Images', 'Videos']
        
        with patch('ai_file_organizer.organizer.AIFacade'):
            with patch('ai_file_organizer.organizer.FileAnalyzer'):
                organizer = FileOrganizer(ai_config, labels)
                # Labels are now stored as dict internally
                assert organizer.labels == {'Documents': [], 'Images': [], 'Videos': [], 'Other': []}
    
    def test_organize_files_invalid_input(self):
        """Test organize_files with invalid input folder."""
        ai_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        labels = ['Documents', 'Images']
        
        with patch('ai_file_organizer.organizer.AIFacade'):
            with patch('ai_file_organizer.organizer.FileAnalyzer'):
                organizer = FileOrganizer(ai_config, labels)
                
                with pytest.raises(ValueError, match="Input folder does not exist"):
                    organizer.organize_files('/nonexistent', '/output')
    
    def test_organize_files_dry_run(self):
        """Test organize_files in dry run mode."""
        ai_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        labels = ['Documents', 'Images', 'Videos']
        
        # Create temporary directories
        input_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        
        try:
            # Create test files
            test_file1 = os.path.join(input_dir, 'test1.txt')
            test_file2 = os.path.join(input_dir, 'test2.pdf')
            
            with open(test_file1, 'w') as f:
                f.write('test content 1')
            with open(test_file2, 'w') as f:
                f.write('test content 2')
            
            # Mock AI facade and file analyzer
            mock_ai_facade = Mock()
            mock_ai_facade.categorize_file.side_effect = ['Documents', 'Documents']
            
            mock_file_analyzer = Mock()
            mock_file_analyzer.analyze_file.side_effect = [
                {'filename': 'test1.txt', 'file_type': '.txt', 'file_size': 100, 
                 'mime_type': 'text/plain', 'is_executable': False},
                {'filename': 'test2.pdf', 'file_type': '.pdf', 'file_size': 200,
                 'mime_type': 'application/pdf', 'is_executable': False}
            ]
            
            with patch('ai_file_organizer.organizer.AIFacade', return_value=mock_ai_facade):
                with patch('ai_file_organizer.organizer.FileAnalyzer', return_value=mock_file_analyzer):
                    organizer = FileOrganizer(ai_config, labels)
                    stats = organizer.organize_files(input_dir, output_dir, dry_run=True)
                    
                    # Check stats
                    assert stats['total_files'] == 2
                    assert stats['processed'] == 2
                    assert stats['failed'] == 0
                    assert stats['categorization']['Documents'] == 2
                    
                    # Files should still exist in input (dry run)
                    assert os.path.exists(test_file1)
                    assert os.path.exists(test_file2)
        
        finally:
            shutil.rmtree(input_dir, ignore_errors=True)
            shutil.rmtree(output_dir, ignore_errors=True)
    
    def test_organize_files_actual_move(self):
        """Test organize_files with actual file movement."""
        ai_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        labels = ['Documents', 'Images']
        
        # Create temporary directories
        input_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        
        try:
            # Create test files
            test_file = os.path.join(input_dir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test content')
            
            # Mock AI facade and file analyzer
            mock_ai_facade = Mock()
            mock_ai_facade.categorize_file.return_value = 'Documents'
            
            mock_file_analyzer = Mock()
            mock_file_analyzer.analyze_file.return_value = {
                'filename': 'test.txt',
                'file_type': '.txt',
                'file_size': 100,
                'mime_type': 'text/plain',
                'is_executable': False
            }
            
            with patch('ai_file_organizer.organizer.AIFacade', return_value=mock_ai_facade):
                with patch('ai_file_organizer.organizer.FileAnalyzer', return_value=mock_file_analyzer):
                    organizer = FileOrganizer(ai_config, labels)
                    stats = organizer.organize_files(input_dir, output_dir, dry_run=False)
                    
                    # Check stats
                    assert stats['total_files'] == 1
                    assert stats['processed'] == 1
                    assert stats['failed'] == 0
                    
                    # File should be moved
                    assert not os.path.exists(test_file)
                    assert os.path.exists(os.path.join(output_dir, 'Documents', 'test.txt'))
        
        finally:
            shutil.rmtree(input_dir, ignore_errors=True)
            shutil.rmtree(output_dir, ignore_errors=True)
    
    def test_organize_files_duplicate_filename(self):
        """Test organize_files with duplicate filenames."""
        ai_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        labels = ['Documents']
        
        # Create temporary directories
        input_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        docs_dir = os.path.join(output_dir, 'Documents')
        os.makedirs(docs_dir)
        
        try:
            # Create test files with same name in different subdirs
            subdir = os.path.join(input_dir, 'subdir')
            os.makedirs(subdir)
            
            test_file1 = os.path.join(input_dir, 'test.txt')
            test_file2 = os.path.join(subdir, 'test.txt')
            
            with open(test_file1, 'w') as f:
                f.write('content 1')
            with open(test_file2, 'w') as f:
                f.write('content 2')
            
            # Mock AI facade and file analyzer
            mock_ai_facade = Mock()
            mock_ai_facade.categorize_file.return_value = 'Documents'
            
            mock_file_analyzer = Mock()
            mock_file_analyzer.analyze_file.side_effect = [
                {'filename': 'test.txt', 'file_type': '.txt', 'file_size': 100,
                 'mime_type': 'text/plain', 'is_executable': False},
                {'filename': 'test.txt', 'file_type': '.txt', 'file_size': 100,
                 'mime_type': 'text/plain', 'is_executable': False}
            ]
            
            with patch('ai_file_organizer.organizer.AIFacade', return_value=mock_ai_facade):
                with patch('ai_file_organizer.organizer.FileAnalyzer', return_value=mock_file_analyzer):
                    organizer = FileOrganizer(ai_config, labels)
                    stats = organizer.organize_files(input_dir, output_dir, dry_run=False)
                    
                    # Check that both files are processed
                    assert stats['total_files'] == 2
                    assert stats['processed'] == 2
                    
                    # Check that files exist with different names
                    assert os.path.exists(os.path.join(docs_dir, 'test.txt'))
                    assert os.path.exists(os.path.join(docs_dir, 'test_1.txt'))
        
        finally:
            shutil.rmtree(input_dir, ignore_errors=True)
            shutil.rmtree(output_dir, ignore_errors=True)
