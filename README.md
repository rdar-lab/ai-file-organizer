# AI File Organizer

An intelligent file organization tool that uses AI/LLM models to automatically categorize and organize files into labeled folders.

## Features

- 🤖 **AI-Powered Categorization**: Uses advanced language models (GPT, Azure GPT, Google Gemini, Llama) to intelligently categorize files
- 📁 **Automatic Organization**: Creates subdirectories for each category and moves files automatically
- 🏗️ **Hierarchical Labels**: Support for sub-categories with automatic nested directory creation (e.g., Documents/Work, Images/Screenshots)
- 🔍 **Smart File Analysis**: Extracts file metadata including type, size, executable status, and archive contents
- 🎨 **Dual Interface**: Both CLI and GUI interfaces available
- 🔧 **Flexible Configuration**: Support for multiple LLM providers (OpenAI, Azure, Google Gemini, Local/Llama)
- 🧪 **Dry Run Mode**: Preview categorization without actually moving files

## Installation

### Option 1: From Source
```bash
git clone https://github.com/rdar-lab/ai-file-organizer.git
cd ai-file-organizer
pip install -e .
```

### Option 2: Using Docker

build locally:
```bash
docker build -t ai-file-organizer .
```

See [Docker Documentation](docs/DOCKER.md) for detailed Docker usage.

### Option 3: Pre-built Executables

Download pre-built executables for your platform from the [Releases](https://github.com/rdar-lab/ai-file-organizer/releases) page:
- Windows: `ai-file-organizer-windows.zip`
- Linux: `ai-file-organizer-linux.tar.gz`
- macOS: `ai-file-organizer-macos.tar.gz`

No Python installation required!

### Option 4: Docker compose with Ollama


- The `ai-file-organizer` service in `docker-compose.yml` is intentionally behind a Compose profile named `ai-file-organizer`.
  This means `docker compose up -d` will NOT create the application container by default — only the helper services (like Ollama) will start.

- To enable and start the app service, either:
    - Pass the profile: `docker compose --profile ai-file-organizer up -d`
    - Or set the environment variable: `COMPOSE_PROFILES=ai-file-organizer docker compose up -d`
    - Or use the provided helper scripts and pass the `--with-app` / `-WithApp` flag (see below).

- NVIDIA GPU support: an optional override `docker-compose.gpu.yml` is provided. It is only included when you explicitly enable GPU usage (the helper scripts will detect GPUs and include this file automatically).

- **Note: to check if GPU is supported inside the WSL2 env**

  ```bash
  # in WSL shell
  nvidia-smi || echo "nvidia-smi not found or no GPU visible in WSL"
  
  # Run a quick GPU-enabled container test (will pull an image):
  docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
  ```

## Helper scripts

Two helper scripts are included to simplify starting the environment and automatically handle GPUs:

- `scripts/start.sh` (Linux/macOS): Detects NVIDIA GPUs (via `nvidia-smi` or `/dev/nvidia*`) and will include `docker-compose.gpu.yml` when GPUs are present. Use `--with-app` to also enable the `ai-file-organizer` profile.

  Examples:
  ```bash
  # Start Ollama only (no app)
  ./scripts/start.sh up

  # Start Ollama + enable ai-file-organizer service
  ./scripts/start.sh up --with-app

  # Stop services
  ./scripts/start.sh down
  ```

- `scripts/start.ps1` (Windows PowerShell): Same behavior, use `-WithApp` to enable the app.

  Examples:
  ```powershell
  # Start Ollama only
  .\scripts\start.ps1 -Command up -Detached

  # Start Ollama + app
  .\scripts\start.ps1 -Command up -Detached -WithApp
  ```


## Quick Start

### Using Pre-built Executables

Download and extract the executable for your platform, then run:

```bash
# Linux/macOS
./ai-file-organizer -i /path/to/input -o /path/to/output -l Documents Images Videos --api-key YOUR_KEY

# Windows
ai-file-organizer.exe -i C:\input -o C:\output -l Documents Images Videos --api-key YOUR_KEY
```

### Using Docker

```bash
docker run -v $(pwd)/input:/input -v $(pwd)/output:/output \
  -e OPENAI_API_KEY=your-key \
  ghcr.io/rdar-lab/ai-file-organizer:latest \
  ai-file-organizer -i /input -o /output -l Documents Images Videos
```

### CLI Usage

Basic usage with OpenAI:
```bash
ai-file-organizer -i /path/to/input -o /path/to/output \
  -l Documents Images Videos Audio Code Other \
  --api-key YOUR_OPENAI_API_KEY
```

Using a configuration file:
```bash
ai-file-organizer -i /path/to/input -o /path/to/output -c config.yml
```

Dry run to preview categorization:
```bash
ai-file-organizer -i /path/to/input -o /path/to/output \
  -l Documents Images Videos \
  --api-key YOUR_API_KEY \
  --dry-run
```

Generate a CSV report of file classification (useful with dry run):
```bash
ai-file-organizer -i /path/to/input -o /path/to/output \
  -l Documents Images Videos \
  --api-key YOUR_API_KEY \
  --dry-run \
  --csv-report /path/to/report.csv
```

### GUI Usage

Launch the graphical interface:
```bash
ai-file-organizer-gui
```

The GUI provides an intuitive interface for:
- Selecting input and output folders
- Defining category labels
- Configuring LLM settings
- Monitoring progress in real-time

## Configuration

### Configuration File Format

Create a `config.yml` file:

```yaml
# AI/LLM Configuration
ai:
  provider: openai  # openai, azure, google, or local
  model: gpt-3.5-turbo
  temperature: 0.3
  api_key: YOUR_API_KEY_HERE
  
  # For Azure
  # azure_endpoint: https://your-resource.openai.azure.com/
  # deployment_name: your-deployment
  
  # For Google Gemini
  # model: gemini-pro
  # api_key: YOUR_GOOGLE_API_KEY
  
  # For Local LLM
  # base_url: http://localhost:8000/v1

# Category labels - Simple list format (flat structure)
labels:
  - Documents
  - Images
  - Videos
  - Audio
  - Archives
  - Code
  - Other

# OR use hierarchical format with sub-categories
# labels:
#   Documents:
#     - Work
#     - Personal
#     - Financial
#   Images:
#     - Photos
#     - Screenshots
#     - Designs
#   Videos: []  # No sub-categories
#   Audio: []
#   Archives: []
#   Code:
#     - Python
#     - JavaScript
#     - Other Code
#   Other: []
```

#### Hierarchical Labels (Sub-Categories)

The tool now supports hierarchical labels with sub-categories. When using hierarchical labels:

- Files can be categorized into both a main category and a sub-category (e.g., "Documents/Work")
- The AI will automatically choose the most specific sub-category when applicable
- Files are organized into nested directories based on the hierarchy
- Labels without sub-categories can be specified with an empty list `[]`

**Example with hierarchical labels:**

```yaml
labels:
  Documents:
    - Work
    - Personal
    - Financial
  Images:
    - Photos
    - Screenshots
  Code:
    - Python
    - JavaScript
  Other: []
```

This will create directory structures like:
```
output/
├── Documents/
│   ├── Work/
│   ├── Personal/
│   └── Financial/
├── Images/
│   ├── Photos/
│   └── Screenshots/
├── Code/
│   ├── Python/
│   └── JavaScript/
└── Other/
```

### Supported LLM Providers

#### OpenAI
```bash
ai-file-organizer -i input -o output \
  --provider openai \
  --model gpt-3.5-turbo \
  --api-key YOUR_OPENAI_API_KEY \
  -l Documents Images Videos
```

#### Azure OpenAI
```bash
ai-file-organizer -i input -o output \
  --provider azure \
  --model gpt-35-turbo \
  --api-key YOUR_AZURE_KEY \
  --azure-endpoint https://your-resource.openai.azure.com/ \
  -l Documents Images Videos
```

#### Google Gemini
```bash
ai-file-organizer -i input -o output \
  --provider google \
  --model gemini-pro \
  --api-key YOUR_GOOGLE_API_KEY \
  -l Documents Images Videos
```

#### Local LLM (Llama, etc.)
```bash
ai-file-organizer -i input -o output \
  --provider local \
  --model llama2 \
  --base-url http://localhost:8000/v1 \
  -l Documents Images Videos
```

## How It Works

1. **File Analysis**: The tool scans the input folder and analyzes each file:
   - File name and extension
   - File size and type
   - MIME type
   - Executable status
   - Executable metadata (for Windows PE files: description, publisher, version info)
   - Archive contents (for ZIP, TAR files)
   - File metadata (timestamps, permissions)

2. **AI Categorization**: File information is sent to the configured LLM with a prompt to categorize the file into one of the specified labels.

3. **Organization**: Files are moved to subdirectories in the output folder based on their assigned category.

## CLI Options

```
-i, --input          Input folder containing files to organize (required)
-o, --output         Output folder for organized files (required)
-l, --labels         List of category labels (space-separated)
-c, --config         Path to configuration file (YAML)
--provider           LLM provider: openai, azure, google, or local (default: openai)
--model              Model name (default: gpt-3.5-turbo)
--api-key            API key for the LLM provider
--azure-endpoint     Azure endpoint URL (for Azure provider)
--base-url           Base URL for local LLM (for local provider)
--temperature        Temperature for LLM (default: 0.3)
--dry-run            Perform a dry run without actually moving files
--csv-report         Path to save CSV report of file classification (useful with --dry-run)
```

## Examples

### Example 1: Organize Downloads Folder
```bash
ai-file-organizer \
  -i ~/Downloads \
  -o ~/OrganizedFiles \
  -l Documents Images Videos Audio Archives Code Other \
  --api-key sk-xxx
```

### Example 2: Organize Project Files
```bash
ai-file-organizer \
  -i ./my-project \
  -o ./organized-project \
  -l "Source Code" "Documentation" "Tests" "Config" "Assets" \
  -c config.yml
```

### Example 3: Use Hierarchical Labels with Config File
Create a `config.yml` with hierarchical labels:
```yaml
ai:
  provider: openai
  model: gpt-3.5-turbo
  api_key: YOUR_API_KEY

labels:
  Documents:
    - Work
    - Personal
    - Financial
  Images:
    - Photos
    - Screenshots
  Code:
    - Python
    - JavaScript
  Other: []
```

Run the organizer:
```bash
ai-file-organizer \
  -i ~/Downloads \
  -o ~/OrganizedFiles \
  -c config.yml
```

Files will be organized into nested directories like `Documents/Work/`, `Images/Photos/`, etc.

### Example 4: Use Azure OpenAI
```bash
ai-file-organizer \
  -i ./input \
  -o ./output \
  --provider azure \
  --model gpt-35-turbo \
  --api-key YOUR_AZURE_KEY \
  --azure-endpoint https://your-resource.openai.azure.com/ \
  -l Work Personal Projects Archives
```

### Example 5: Dry Run with CSV Report
```bash
ai-file-organizer \
  -i ~/Downloads \
  -o ~/OrganizedFiles \
  -l Documents Images Videos Code Other \
  --api-key YOUR_API_KEY \
  --dry-run \
  --csv-report ~/classification_report.csv
```

This will analyze all files without moving them and generate a CSV report containing:
- `file_name`: Name of the file
- `file_type`: File extension
- `file_size`: Size in bytes
- `decided_label`: The category assigned by the AI

### Example 6: Using DeepSeek model (16GB GPU required)

```yaml
ai:
  provider: local
  model: deepseek-r1:14b
  temperature: 0.3
labels:
- Apps
- Documents
- Images
- Videos
- Audio
- Other
- Logs
- Junk
- Guides
- Datasheets
- Invoices
- Agreements
input_folder: K:/Downloads
output_folder: K:/Organized
csv_report: K:/Organized/report.csv
```

## Development

### Running Tests
```bash
# Unit tests
pytest tests/test_*.py -v

# Live tests (requires Ollama)
docker-compose up -d ollama
pytest tests/test_live.py -v
```

### Running Tests with Coverage
```bash
pytest --cov=ai_file_organizer tests/
```

### Building Executables
```bash
# Install PyInstaller
pip install pyinstaller

# Build for your platform
./build_executables.sh

# Or manually
pyinstaller ai-file-organizer.spec --clean
pyinstaller ai-file-organizer-gui.spec --clean
```

### Building Docker Image
```bash
docker build -t ai-file-organizer .

# Test the image
docker run --rm ai-file-organizer ai-file-organizer --help
```

## Requirements

### For Python Installation:
- Python 3.8+
- langchain
- openai
- python-magic
- PySimpleGUI (for GUI)
- pyyaml

### For Docker:
- Docker 20.10+
- Docker Compose (optional)

### For Executables:
- No requirements! Just download and run

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on [GitHub](https://github.com/rdar-lab/ai-file-organizer/issues).
