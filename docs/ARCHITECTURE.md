# Architecture Reference

## Core Modules

### ai_facade.py

#### `AIFacade`

Facade for AI/LLM operations using langchain.

**Constructor:**
```python
AIFacade(config: Dict[str, Any])
```

**Parameters:**
- `config` (dict): Configuration dictionary with LLM settings
  - `provider` (str): 'openai', 'azure', or 'local'
  - `model` (str): Model name (e.g., 'gpt-3.5-turbo')
  - `temperature` (float): Temperature setting (0.0-1.0)
  - `api_key` (str): API key for OpenAI/Azure
  - `azure_endpoint` (str): Azure endpoint (for Azure provider)
  - `base_url` (str): Base URL (for local LLM)

**Methods:**

##### `categorize_file(file_info: Dict[str, Any], labels: list) -> str`

Categorize a file using the LLM.

**Parameters:**
- `file_info` (dict): Dictionary containing file information
- `labels` (list): List of possible category labels

**Returns:**
- `str`: The category label chosen by the LLM

**Example:**
```python
ai = AIFacade({
    'provider': 'openai',
    'model': 'gpt-3.5-turbo',
    'api_key': 'sk-xxx'
})

file_info = {
    'filename': 'report.pdf',
    'file_type': '.pdf',
    'file_size': 1024000,
    'mime_type': 'application/pdf',
    'is_executable': False
}

category = ai.categorize_file(file_info, ['Documents', 'Images', 'Other'])
print(category)  # 'Documents'
```

---

### file_analyzer.py

#### `FileAnalyzer`

Analyze files and extract metadata.

**Constructor:**
```python
FileAnalyzer()
```

**Methods:**

##### `analyze_file(file_path: str) -> Dict[str, Any]`

Analyze a file and extract metadata.

**Parameters:**
- `file_path` (str): Path to the file to analyze

**Returns:**
- `dict`: Dictionary containing file information with keys:
  - `filename` (str): Base name of the file
  - `file_path` (str): Full path to the file
  - `file_size` (int): Size in bytes
  - `file_type` (str): File extension
  - `mime_type` (str): MIME type
  - `is_executable` (bool): Whether file is executable
  - `archive_contents` (str, optional): List of files in archive
  - `metadata` (dict): Additional metadata (timestamps, permissions)

**Example:**
```python
analyzer = FileAnalyzer()
file_info = analyzer.analyze_file('/path/to/file.pdf')
print(file_info['filename'])  # 'file.pdf'
print(file_info['file_size'])  # 1024000
print(file_info['mime_type'])  # 'application/pdf'
```

---

### organizer.py

#### `FileOrganizer`

Organize files using AI categorization.

**Constructor:**
```python
FileOrganizer(ai_config: Dict[str, Any], labels: List[str])
```

**Parameters:**
- `ai_config` (dict): Configuration for AI/LLM
- `labels` (list): List of category labels

**Methods:**

##### `organize_files(input_folder: str, output_folder: str, dry_run: bool = False) -> Dict[str, Any]`

Organize files from input folder to output folder.

**Parameters:**
- `input_folder` (str): Source folder containing files to organize
- `output_folder` (str): Destination folder for organized files
- `dry_run` (bool): If True, don't actually move files

**Returns:**
- `dict`: Statistics dictionary with keys:
  - `total_files` (int): Total number of files processed
  - `processed` (int): Successfully processed files
  - `failed` (int): Failed files
  - `categorization` (dict): Count of files per category

**Example:**
```python
ai_config = {
    'provider': 'openai',
    'model': 'gpt-3.5-turbo',
    'api_key': 'sk-xxx'
}

organizer = FileOrganizer(ai_config, ['Documents', 'Images', 'Videos'])
stats = organizer.organize_files('/input', '/output', dry_run=False)

print(f"Processed: {stats['processed']}")
print(f"Failed: {stats['failed']}")
for category, count in stats['categorization'].items():
    print(f"{category}: {count} files")
```

---

## CLI Module

### cli.py

#### `main()`

Main CLI entry point.

Parses command-line arguments and executes file organization.

**Command-line Arguments:**
- `-i, --input`: Input folder (required)
- `-o, --output`: Output folder (required)
- `-l, --labels`: List of labels
- `-c, --config`: Configuration file path
- `--provider`: LLM provider
- `--model`: Model name
- `--api-key`: API key
- `--azure-endpoint`: Azure endpoint
- `--base-url`: Local LLM base URL
- `--temperature`: Temperature (0.0-1.0)
- `--dry-run`: Dry run mode

**Example:**
```bash
ai-file-organizer -i /input -o /output -l Documents Images --api-key sk-xxx
```

---

## GUI Module

### gui.py

#### `main()`

Main GUI entry point.

Launches PySimpleGUI interface for file organization.

**Features:**
- Folder selection via file browser
- Label configuration
- LLM settings configuration
- Real-time progress tracking
- Dry run mode

**Example:**
```bash
ai-file-organizer-gui
```

---

## Usage Examples

### Basic File Organization

```python
from ai_file_organizer.organizer import FileOrganizer

ai_config = {
    'provider': 'openai',
    'model': 'gpt-3.5-turbo',
    'temperature': 0.3,
    'api_key': 'sk-xxx'
}

labels = ['Documents', 'Images', 'Videos', 'Audio', 'Other']

organizer = FileOrganizer(ai_config, labels)
stats = organizer.organize_files(
    input_folder='/home/user/Downloads',
    output_folder='/home/user/Organized',
    dry_run=False
)
```

### Using Azure OpenAI

```python
from ai_file_organizer.organizer import FileOrganizer

ai_config = {
    'provider': 'azure',
    'model': 'gpt-35-turbo',
    'temperature': 0.3,
    'api_key': 'your-azure-key',
    'azure_endpoint': 'https://your-resource.openai.azure.com/',
    'deployment_name': 'your-deployment'
}

labels = ['Work', 'Personal', 'Projects']

organizer = FileOrganizer(ai_config, labels)
stats = organizer.organize_files('/input', '/output')
```

### Using Local LLM

```python
from ai_file_organizer.organizer import FileOrganizer

ai_config = {
    'provider': 'local',
    'model': 'llama2',
    'temperature': 0.3,
    'base_url': 'http://localhost:8000/v1',
    'api_key': 'not-needed'
}

labels = ['Code', 'Docs', 'Assets', 'Other']

organizer = FileOrganizer(ai_config, labels)
stats = organizer.organize_files('/input', '/output')
```

### Custom File Analysis

```python
from ai_file_organizer.file_analyzer import FileAnalyzer

analyzer = FileAnalyzer()

# Analyze a single file
file_info = analyzer.analyze_file('/path/to/document.pdf')

print(f"Filename: {file_info['filename']}")
print(f"Size: {file_info['file_size']} bytes")
print(f"Type: {file_info['mime_type']}")
print(f"Executable: {file_info['is_executable']}")

# Check if it's an archive
if 'archive_contents' in file_info:
    print("Archive contents:")
    print(file_info['archive_contents'])
```

### Configuration from YAML

```python
import yaml
from ai_file_organizer.organizer import FileOrganizer

# Load config
with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

ai_config = config['ai']
labels = config['labels']

organizer = FileOrganizer(ai_config, labels)
stats = organizer.organize_files('/input', '/output')
```
