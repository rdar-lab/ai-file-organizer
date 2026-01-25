"""Tests for file organizer module."""

import csv
import os
import tempfile
import shutil
import pytest
from unittest.mock import Mock, patch
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
                organizer = FileOrganizer(ai_config, labels, '.', None, dry_run=True)
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
                with pytest.raises(ValueError, match="Input folder does not exist"):
                    FileOrganizer(ai_config, labels, '/nonexistent', None, dry_run=True)

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
            mock_ai_facade.categorize_file.side_effect = ('', ('Documents', None)), ('', ('Documents', None))
            
            mock_file_analyzer = Mock()
            mock_file_analyzer.analyze_file.side_effect = [
                {'filename': 'test1.txt', 'file_type': '.txt', 'file_size': 100, 
                 'mime_type': 'text/plain', 'is_executable': False},
                {'filename': 'test2.pdf', 'file_type': '.pdf', 'file_size': 200,
                 'mime_type': 'application/pdf', 'is_executable': False}
            ]
            
            with patch('ai_file_organizer.organizer.AIFacade', return_value=mock_ai_facade):
                with patch('ai_file_organizer.organizer.FileAnalyzer', return_value=mock_file_analyzer):
                    organizer = FileOrganizer(ai_config, labels, input_dir, output_dir, dry_run=True)
                    stats = organizer.organize_files()
                    
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
    
    def test_organize_files_with_csv_report(self):
        """Test organize_files with CSV report generation."""
        ai_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        labels = ['Documents', 'Images', 'Code']
        
        # Create temporary directories
        input_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        csv_file = os.path.join(output_dir, 'report.csv')
        
        try:
            # Create test files
            test_file1 = os.path.join(input_dir, 'test1.txt')
            test_file2 = os.path.join(input_dir, 'image.jpg')
            test_file3 = os.path.join(input_dir, 'script.py')
            test_file4 = os.path.join(input_dir, 'error.error')
            
            with open(test_file1, 'w') as f:
                f.write('test content 1')
            with open(test_file2, 'w') as f:
                f.write('test content 2')
            with open(test_file3, 'w') as f:
                f.write('print("hello")')
            with open(test_file4, 'w') as f:
                f.write('error')

            # Mock AI facade and file analyzer
            mock_ai_facade = Mock()
            # Return values based on the actual filename being categorized
            def categorize_side_effect(file_info, labels):
                filename = file_info['filename']
                if filename == 'test1.txt':
                    cat = 'Documents'
                elif filename == 'image.jpg':
                    cat = 'Images'
                elif filename == 'script.py':
                    cat = 'Code'
                else:
                    cat = 'Other'
                return '', (cat, None)
            
            mock_ai_facade.categorize_file.side_effect = categorize_side_effect
            
            mock_file_analyzer = Mock()
            # Return values based on the actual file path
            def analyze_side_effect(file_path):
                filename = os.path.basename(file_path)
                if filename == 'test1.txt':
                    return {'filename': 'test1.txt', 'file_type': '.txt', 'file_size': 14, 
                            'mime_type': 'text/plain', 'is_executable': False}
                elif filename == 'image.jpg':
                    return {'filename': 'image.jpg', 'file_type': '.jpg', 'file_size': 14,
                            'mime_type': 'image/jpeg', 'is_executable': False}
                elif filename == 'script.py':
                    return {'filename': 'script.py', 'file_type': '.py', 'file_size': 15,
                            'mime_type': 'text/x-python', 'is_executable': False}
                elif filename == 'error.error':
                    raise Exception('Error simulated during analysis')

            mock_file_analyzer.analyze_file.side_effect = analyze_side_effect
            
            with patch('ai_file_organizer.organizer.AIFacade', return_value=mock_ai_facade):
                with patch('ai_file_organizer.organizer.FileAnalyzer', return_value=mock_file_analyzer):
                    organizer = FileOrganizer(ai_config, labels, input_dir, output_dir, dry_run=True,
                                              csv_report_path=csv_file)
                    stats = organizer.organize_files()
                    
                    # Check stats
                    assert stats['total_files'] == 4
                    assert stats['processed'] == 3
                    assert stats['failed'] == 1
                    
                    # CSV file should exist
                    assert os.path.exists(csv_file)
                    
                    # Read and verify CSV content
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        
                        assert len(rows) == 4
                        
                        # Check headers include the original minimal set
                        expected_min_fields = {
                            "file_name",
                            "file_size",
                            "file_type",
                            "mime_type",
                            "is_executable",
                            "file_info",
                            "llm_response",
                            "category",
                            "sub_category",
                            "error"
                        }
                        assert expected_min_fields.issubset(set(rows[0].keys()))

                        # Check data - convert to dict for easier verification
                        rows_by_name = {row['file_name']: row for row in rows}
                        
                        assert 'test1.txt' in rows_by_name
                        assert rows_by_name['test1.txt']['file_type'] == '.txt'
                        assert rows_by_name['test1.txt']['file_size'] == '14'
                        
                        assert 'image.jpg' in rows_by_name
                        assert rows_by_name['image.jpg']['file_type'] == '.jpg'
                        
                        assert 'script.py' in rows_by_name
                        assert rows_by_name['script.py']['file_type'] == '.py'

                        assert 'error.error' in rows_by_name
                        assert rows_by_name['error.error']['error'] == "Exception('Error simulated during analysis')"

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
            mock_ai_facade.categorize_file.return_value = '', ('Documents', '')
            
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
                    organizer = FileOrganizer(ai_config, labels, input_dir, output_dir, dry_run=False)
                    stats = organizer.organize_files()
                    
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
            mock_ai_facade.categorize_file.return_value = '', ('Documents', '')
            
            mock_file_analyzer = Mock()
            mock_file_analyzer.analyze_file.side_effect = [
                {'filename': 'test.txt', 'file_type': '.txt', 'file_size': 100,
                 'mime_type': 'text/plain', 'is_executable': False},
                {'filename': 'test.txt', 'file_type': '.txt', 'file_size': 100,
                 'mime_type': 'text/plain', 'is_executable': False}
            ]
            
            with patch('ai_file_organizer.organizer.AIFacade', return_value=mock_ai_facade):
                with patch('ai_file_organizer.organizer.FileAnalyzer', return_value=mock_file_analyzer):
                    organizer = FileOrganizer(ai_config, labels, input_dir, output_dir, dry_run=False)
                    stats = organizer.organize_files()
                    
                    # Check that both files are processed
                    assert stats['total_files'] == 2
                    assert stats['processed'] == 2
                    
                    # Check that files exist with different names
                    assert os.path.exists(os.path.join(docs_dir, 'test.txt'))
                    assert os.path.exists(os.path.join(docs_dir, 'test_1.txt'))
        
        finally:
            shutil.rmtree(input_dir, ignore_errors=True)
            shutil.rmtree(output_dir, ignore_errors=True)
