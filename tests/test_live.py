"""Live integration tests for AI File Organizer with Docker and local LLM."""

import os
import tempfile
import shutil
import time
import pytest
import requests
import subprocess
import yaml
import sys

# Mark all tests in this file as live tests
pytestmark = pytest.mark.live


class TestDockerIntegration:
    """Test class for Docker integration tests."""
    
    @staticmethod
    def run_command(cmd, cwd=None, timeout=300):
        """Run a shell command and stream output live."""
        
        print(f"Running command: {cmd} in {cwd if cwd else os.getcwd()}")
        
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            timeout=timeout
        )
        # Output is already shown live, so return empty strings for stdout/stderr
        return result.returncode
    
    @staticmethod
    def wait_for_ollama(base_url="http://localhost:11434", timeout=120):
        """Wait for Ollama service to be ready."""
        print(f"Waiting for Ollama at {base_url}...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    print("Ollama is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        return False
    
    @staticmethod
    def ensure_model_available(model_name="tinyllama", base_url="http://localhost:11434"):
        """Ensure the specified model is available in Ollama."""
        
        print(f"Ensuring Model {model_name} is available")
        
        try:
            # Check if model exists
            response = requests.get(f"{base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if any(model['name'].startswith(model_name) for model in models):
                    print(f"Model {model_name} is already available")
                    return True
            # Model doesn't exist, try to pull it
            print(f"Pulling model {model_name}... (this may take several minutes)")
            response = requests.post(
                f"{base_url}/api/pull",
                json={"name": model_name},
                timeout=600
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error ensuring model availability: {e}")
            return False
    
    @pytest.fixture(scope="module")
    def docker_compose_environment(self):
        """Set up and tear down docker-compose environment."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        print("Setting up docker-compose environment...")
        
        # Start docker-compose services
        print("Starting docker-compose services...")
        returncode = self.run_command(
            "docker compose up -d ollama",
            cwd=repo_root,
            timeout=300
        )
        
        if returncode != 0:
            self.fail(f"Failed to start docker-compose")
        
        # Wait for Ollama to be ready
        if not self.wait_for_ollama("http://localhost:11434", timeout=300):
            # Cleanup
            self.run_command("docker compose down", cwd=repo_root)
            self.fail("Ollama service did not become ready in time")
        
        # Ensure model is available
        model_name = os.getenv("OLLAMA_MODEL", "tinyllama")        
        if not self.ensure_model_available(model_name, "http://localhost:11434"):
            # Cleanup
            self.fail(f"Model {model_name} not available")
        
        yield {
            'repo_root': repo_root
        }
        
        # Cleanup
        print("Tearing down docker-compose environment...")
        self.run_command("docker compose down", cwd=repo_root, timeout=60)
    
    @pytest.fixture
    def test_workspace(self, docker_compose_environment):
        """Create test workspace with input files and config."""
        repo_root = docker_compose_environment['repo_root']
        temp_dir = tempfile.mkdtemp(prefix='ai-file-organizer-test-')
        
        # Create subdirectories for this test
        input_dir = os.path.join(temp_dir, 'input')
        output_dir = os.path.join(temp_dir, 'output')
        
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create test files
        test_files = {
            'document.txt': 'This is a text document with some content.',
            'image.jpg': b'\xFF\xD8\xFF\xE0',  # JPEG header
            'script.py': 'print("Hello, World!")',
            'data.json': '{"key": "value"}',
            'notes.md': '# Markdown Notes\n\nSome notes here.',
        }
        
        for filename, content in test_files.items():
            filepath = os.path.join(input_dir, filename)
            mode = 'wb' if isinstance(content, bytes) else 'w'
            with open(filepath, mode) as f:
                f.write(content)
        
        # Create config file
        config = {
            'ai': {
                'provider': 'local',
                'model': os.getenv("OLLAMA_MODEL", "tinyllama"),
                'temperature': 0.3,
                'base_url': 'http://ollama:11434/v1',
                'api_key': 'not-needed'
            },
            'labels': ['Documents', 'Images', 'Code', 'Data', 'Other'],
            'input_folder': '/input',
            'output_folder': '/output',
            'continuous': False
        }
        
        config_path = os.path.join(temp_dir, 'config.yml')
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        yield {
            'repo_root': repo_root,
            'temp_dir': temp_dir,
            'input_dir': input_dir,
            'output_dir': output_dir,
            'config_path': config_path
        }

        # Destroy and delete test directories
        if os.path.exists(temp_dir):
            print(f"Cleaning up test workspace: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)
        

    def test_docker_container_organizes_files(self, test_workspace):
        """Test that Docker container organizes files using docker-compose."""
        repo_root = test_workspace['repo_root']
        input_dir = test_workspace['input_dir']
        output_dir = test_workspace['output_dir']
        
        # Count files before
        files_before = os.listdir(input_dir)
        print(f"Files in input before: {files_before}")
        
        # Build the ai-file-organizer image
        print("Building ai-file-organizer Docker image...")
        returncode = self.run_command(
            "docker compose build ai-file-organizer",
            cwd=repo_root,
            timeout=300
        )
        
        if returncode != 0:
            pytest.fail(f"Failed to build Docker image")
        
        # Run the container with overridden volumes
        print("Running ai-file-organizer container...")
        returncode = self.run_command(
            f"docker compose run --rm "
            f"-v {input_dir}:/input "
            f"-v {output_dir}:/output "
            f"-v {test_workspace['config_path']}:/app/config.yml "
            f"ai-file-organizer",
            cwd=repo_root,
            timeout=300
        )
        
        # Check that files were processed
        # Files should be moved from input to output
        files_after = os.listdir(input_dir)
        print(f"Files in input after: {files_after}")
        
        # Check output directory
        if os.path.exists(output_dir):
            output_contents = []
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), output_dir)
                    output_contents.append(rel_path)
            print(f"Files in output: {output_contents}")
            
            # Verify that some files were organized
            assert len(output_contents) > 0, "No files were organized to output directory"
            
            # Verify subdirectories were created
            subdirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
            print(f"Subdirectories created: {subdirs}")
            assert len(subdirs) > 0, "No subdirectories were created"
    
    def test_docker_container_dry_run(self, test_workspace):
        """Test Docker container in dry-run mode."""
        repo_root = test_workspace['repo_root']
        input_dir = test_workspace['input_dir']
        output_dir = test_workspace['output_dir']
        config_path = test_workspace['config_path']
        
        # For dry run, we'll override the command
        files_before = set(os.listdir(input_dir))
        
        # Build the image
        print("Building ai-file-organizer Docker image...")
        returncode = self.run_command(
            "docker compose build ai-file-organizer",
            cwd=repo_root,
            timeout=300
        )
        
        if returncode != 0:
            pytest.fail(f"Failed to build Docker image")
        
        # Run with dry-run flag using docker run directly
        print("Running ai-file-organizer container in dry-run mode...")
        returncode = self.run_command(
            'docker run --rm '
            '--network ai-file-organizer_default '
            f'-v {input_dir}:/input '
            f'-v {output_dir}:/output '
            f'-v {config_path}:/app/config.yml '
            'ai-file-organizer:latest '
            'ai-file-organizer -i /input -o /output '
            '-l Documents Images Code Data Other '
            '--provider local --model tinyllama '
            '--base-url http://ollama:11434/v1 '
            '--api-key not-needed --dry-run',
            cwd=repo_root,
            timeout=300
        )
        
        # In dry-run mode, files should not be moved
        files_after = set(os.listdir(input_dir))
        assert files_before == files_after, "Files were moved in dry-run mode"
        
        print("Dry-run test passed - files were not moved")


    def test_cli_organizes_files(self, test_workspace):
        """Test that the CLI organizes files using the same setup as Docker."""
        repo_root = test_workspace['repo_root']
        input_dir = test_workspace['input_dir']
        output_dir = test_workspace['output_dir']
        config_path = test_workspace['config_path']

        # Count files before
        files_before = os.listdir(input_dir)
        print(f"Files in input before (CLI): {files_before}")

        # Run the CLI
        src_dir = os.path.join(repo_root, "src")
        cmd = (
            f"python3 -m ai_file_organizer.cli "
            f"-i {input_dir} -o {output_dir} "
            f"-l Documents Images Code Data Other "
            f"--provider local --model tinyllama "
            f"--base-url http://localhost:11434/v1 "
            f"--api-key not-needed "
            f"--config {config_path} "
        )
        returncode = self.run_command(cmd, cwd=src_dir, timeout=300)

        if returncode != 0:
            pytest.fail(f"CLI failed")

        # Check that files were processed
        files_after = os.listdir(input_dir)
        print(f"Files in input after (CLI): {files_after}")

        # Check output directory
        if os.path.exists(output_dir):
            output_contents = []
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), output_dir)
                    output_contents.append(rel_path)
            print(f"Files in output (CLI): {output_contents}")

            # Verify that some files were organized
            assert len(output_contents) > 0, "No files were organized to output directory (CLI)"

            # Verify subdirectories were created
            subdirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
            print(f"Subdirectories created (CLI): {subdirs}")
            assert len(subdirs) > 0, "No subdirectories were created (CLI)"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
