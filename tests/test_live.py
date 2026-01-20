"""Live integration tests for AI File Organizer with local LLM."""

import os
import tempfile
import shutil
import time
import pytest
import requests
import subprocess

# Mark all tests in this file as live tests
pytestmark = pytest.mark.live


def wait_for_ollama(base_url="http://localhost:11434", timeout=60):
    """Wait for Ollama service to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    return False


def ensure_model_available(model_name="llama2", base_url="http://localhost:11434"):
    """Ensure the specified model is available in Ollama."""
    try:
        # Check if model exists
        response = requests.get(f"{base_url}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            if any(model['name'].startswith(model_name) for model in models):
                return True
        
        # Model doesn't exist, try to pull it
        print(f"Pulling model {model_name}...")
        response = requests.post(
            f"{base_url}/api/pull",
            json={"name": model_name}
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error ensuring model availability: {e}")
        return False


@pytest.fixture(scope="module")
def ollama_service():
    """Fixture to check Ollama service availability."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    if not wait_for_ollama(base_url):
        pytest.skip("Ollama service not available")
    
    # Try to ensure model is available
    model_name = os.getenv("OLLAMA_MODEL", "llama2")
    if not ensure_model_available(model_name, base_url):
        pytest.skip(f"Model {model_name} not available and could not be pulled")
    
    return base_url


@pytest.fixture
def test_files():
    """Create temporary test files for organization."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test files
    files = {
        'document.txt': 'This is a text document with some content.',
        'image.jpg': b'\xFF\xD8\xFF\xE0',  # JPEG header
        'script.py': 'print("Hello, World!")',
        'data.json': '{"key": "value"}',
        'notes.md': '# Markdown Notes\n\nSome notes here.',
    }
    
    for filename, content in files.items():
        filepath = os.path.join(temp_dir, filename)
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(filepath, mode) as f:
            f.write(content)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_organize_with_local_llm(ollama_service, test_files):
    """Test file organization with local Ollama LLM."""
    output_dir = tempfile.mkdtemp()
    
    try:
        # Configure to use local LLM
        ai_config = {
            'provider': 'local',
            'model': os.getenv("OLLAMA_MODEL", "llama2"),
            'temperature': 0.3,
            'base_url': f"{ollama_service}/v1",
            'api_key': 'not-needed'
        }
        
        labels = ['Documents', 'Images', 'Code', 'Data', 'Other']
        
        # Create organizer
        organizer = FileOrganizer(ai_config, labels)
        
        # Run organization
        stats = organizer.organize_files(test_files, output_dir, dry_run=False)
        
        # Verify results
        assert stats['total_files'] > 0, "No files were found"
        assert stats['processed'] > 0, "No files were processed"
        assert stats['failed'] == 0, "Some files failed to process"
        
        # Check that subdirectories were created
        for label in labels:
            label_dir = os.path.join(output_dir, label)
            # Subdirectories are created even if empty
            assert os.path.exists(label_dir), f"Directory {label} should exist"
        
        # Verify at least some files were moved
        total_moved = sum(stats['categorization'].values())
        assert total_moved == stats['processed'], "Not all processed files were categorized"
        
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_dry_run_with_local_llm(ollama_service, test_files):
    """Test dry run mode with local Ollama LLM."""
    output_dir = tempfile.mkdtemp()
    
    try:
        ai_config = {
            'provider': 'local',
            'model': os.getenv("OLLAMA_MODEL", "llama2"),
            'temperature': 0.3,
            'base_url': f"{ollama_service}/v1",
            'api_key': 'not-needed'
        }
        
        labels = ['Documents', 'Code', 'Other']
        
        organizer = FileOrganizer(ai_config, labels)
        
        # Count files before
        files_before = os.listdir(test_files)
        
        # Run in dry-run mode
        stats = organizer.organize_files(test_files, output_dir, dry_run=True)
        
        # Files should still be in original location
        files_after = os.listdir(test_files)
        assert files_before == files_after, "Files were moved in dry-run mode"
        
        # But processing should have occurred
        assert stats['processed'] > 0, "No files were processed in dry-run"
        
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_categorization_accuracy(ollama_service, test_files):
    """Test that categorization makes sense."""
    output_dir = tempfile.mkdtemp()
    
    try:
        ai_config = {
            'provider': 'local',
            'model': os.getenv("OLLAMA_MODEL", "llama2"),
            'temperature': 0.1,  # Low temperature for consistency
            'base_url': f"{ollama_service}/v1",
            'api_key': 'not-needed'
        }
        
        labels = ['Documents', 'Images', 'Code', 'Data', 'Other']
        
        organizer = FileOrganizer(ai_config, labels)
        stats = organizer.organize_files(test_files, output_dir, dry_run=False)
        
        # Check that at least some categorization occurred
        categories_with_files = [label for label, count in stats['categorization'].items() if count > 0]
        assert len(categories_with_files) > 0, "At least one category should have files"
        
        # Verify files exist in output
        moved_files = []
        for label in labels:
            label_dir = os.path.join(output_dir, label)
            if os.path.exists(label_dir):
                moved_files.extend(os.listdir(label_dir))
        
        # All processed files should be accounted for
        assert len(moved_files) == stats['processed']
        
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
