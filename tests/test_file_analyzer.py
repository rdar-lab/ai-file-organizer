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
        """Test executable detection for all supported types."""
        analyzer = FileAnalyzer()

        # 1. Unix-style executable (chmod +x)
        if os.name != 'nt':  # Skip on Windows
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write('echo test')
                unix_exec_path = f.name
            try:
                os.chmod(unix_exec_path, 0o755)
                assert analyzer._is_executable(unix_exec_path) is True
            finally:
                os.unlink(unix_exec_path)

        # 2. Windows-style executable (by extension)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False) as f:
            f.write('@echo off\necho test')
            win_exec_path = f.name
        try:
            assert analyzer._is_executable(win_exec_path) is True
        finally:
            os.unlink(win_exec_path)

        # 3. Shebang script
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b'#! /usr/bin/env python\nprint(123)')
            shebang_path = f.name
        try:
            assert analyzer._is_executable(shebang_path) is True
        finally:
            os.unlink(shebang_path)

        # 4. ELF binary (Linux)
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b'\x7fELF' + b'\x00' * 60)
            elf_path = f.name
        try:
            assert analyzer._is_executable(elf_path) is True
        finally:
            os.unlink(elf_path)

        # 5. PE binary (Windows EXE)
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b'MZ' + b'\x00' * 62)
            pe_path = f.name
        try:
            assert analyzer._is_executable(pe_path) is True
        finally:
            os.unlink(pe_path)

        # 6. Mach-O binary (macOS)
        macho_magics = [b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xcf\xfa\xed\xfe']
        for magic in macho_magics:
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
                f.write(magic + b'\x00' * 60)
                macho_path = f.name
            try:
                assert analyzer._is_executable(macho_path) is True
            finally:
                os.unlink(macho_path)
    
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

    def test_get_executable_metadata_no_pefile(self):
        """Test executable metadata extraction when pefile is not available."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.exe', delete=False) as f:
            # Create a minimal PE file structure
            f.write(b'MZ' + b'\x00' * 62)
            temp_path = f.name
        
        try:
            with patch('ai_file_organizer.file_analyzer.PEFILE_AVAILABLE', False):
                with patch('ai_file_organizer.file_analyzer.magic.Magic'):
                    analyzer = FileAnalyzer()
                    metadata = analyzer._get_executable_metadata(temp_path)
                    
                    assert metadata is None
        finally:
            os.unlink(temp_path)
    
    def test_get_executable_metadata_invalid_pe(self):
        """Test executable metadata extraction with invalid PE file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.exe', delete=False) as f:
            # Create an invalid PE file
            f.write(b'Not a PE file')
            temp_path = f.name
        
        try:
            with patch('ai_file_organizer.file_analyzer.magic.Magic'):
                analyzer = FileAnalyzer()
                metadata = analyzer._get_executable_metadata(temp_path)
                
                # Should return None for invalid PE files
                assert metadata is None
        finally:
            os.unlink(temp_path)
    
    def test_analyze_file_with_executable_metadata(self):
        """Test that analyze_file includes executable_metadata when available."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.exe', delete=False) as f:
            # Create a minimal PE file structure
            f.write(b'MZ' + b'\x00' * 62)
            temp_path = f.name
        
        try:
            with patch('ai_file_organizer.file_analyzer.magic.Magic') as mock_magic:
                mock_magic_instance = Mock()
                mock_magic_instance.from_file.return_value = 'application/x-executable'
                mock_magic.return_value = mock_magic_instance
                
                analyzer = FileAnalyzer()
                
                # Mock the _get_executable_metadata method to return sample data
                sample_metadata = {
                    'FileDescription': 'Test Application',
                    'CompanyName': 'Test Company',
                    'FileVersion': '1.0.0.0'
                }
                
                with patch.object(analyzer, '_get_executable_metadata', return_value=sample_metadata):
                    file_info = analyzer.analyze_file(temp_path)
                    
                    assert 'executable_metadata' in file_info
                    assert file_info['executable_metadata'] == sample_metadata
        finally:
            os.unlink(temp_path)
