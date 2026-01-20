"""Tests for file analyzer module."""

import os
import tempfile
import zipfile
import pytest
from unittest.mock import Mock, patch
from ai_file_organizer.file_analyzer import FileAnalyzer


class TestFileAnalyzer:
    """Test FileAnalyzer class."""
    
    def test_init(self):
        """Test initialization."""
        with patch('ai_file_organizer.file_analyzer.magic.Magic'):
            analyzer = FileAnalyzer()
            assert analyzer is not None
    
    def test_analyze_file(self):
        """Test file analysis."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('test content')
            temp_path = f.name
        
        try:
            with patch('ai_file_organizer.file_analyzer.magic.Magic') as mock_magic:
                mock_magic_instance = Mock()
                mock_magic_instance.from_file.return_value = 'text/plain'
                mock_magic.return_value = mock_magic_instance
                
                analyzer = FileAnalyzer()
                file_info = analyzer.analyze_file(temp_path)
                
                assert file_info['filename'] == os.path.basename(temp_path)
                assert file_info['file_path'] == temp_path
                assert file_info['file_type'] == '.txt'
                assert file_info['mime_type'] == 'text/plain'
                assert 'file_size' in file_info
                assert 'is_executable' in file_info
                assert 'metadata' in file_info
        finally:
            os.unlink(temp_path)
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        with patch('ai_file_organizer.file_analyzer.magic.Magic'):
            analyzer = FileAnalyzer()
            
            assert analyzer._get_file_extension('test.txt') == '.txt'
            assert analyzer._get_file_extension('test.PDF') == '.pdf'
            assert analyzer._get_file_extension('test') == 'no_extension'
    
    def test_is_executable(self):
        """Test executable detection."""
        # Create a temporary executable file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('#!/bin/bash\necho test')
            temp_path = f.name
        
        try:
            os.chmod(temp_path, 0o755)
            
            with patch('ai_file_organizer.file_analyzer.magic.Magic'):
                analyzer = FileAnalyzer()
                assert analyzer._is_executable(temp_path) is True
        finally:
            os.unlink(temp_path)
    
    def test_get_archive_contents_zip(self):
        """Test archive contents extraction for ZIP files."""
        # Create a temporary ZIP file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('file1.txt', 'content1')
                zf.writestr('file2.txt', 'content2')
            
            with patch('ai_file_organizer.file_analyzer.magic.Magic'):
                analyzer = FileAnalyzer()
                contents = analyzer._get_archive_contents(temp_path)
                
                assert contents is not None
                assert 'file1.txt' in contents
                assert 'file2.txt' in contents
        finally:
            os.unlink(temp_path)
    
    def test_get_archive_contents_non_archive(self):
        """Test archive contents extraction for non-archive files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('test content')
            temp_path = f.name
        
        try:
            with patch('ai_file_organizer.file_analyzer.magic.Magic'):
                analyzer = FileAnalyzer()
                contents = analyzer._get_archive_contents(temp_path)
                
                assert contents is None
        finally:
            os.unlink(temp_path)
