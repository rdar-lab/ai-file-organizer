# AI File Organizer

An intelligent file organization tool that uses AI/LLM models to automatically categorize and organize files into labeled folders.

## Features

- 🤖 **AI-Powered Categorization**: Uses advanced language models (GPT, Azure GPT, Llama) to intelligently categorize files
- 📁 **Automatic Organization**: Creates subdirectories for each category and moves files automatically
- 🔍 **Smart File Analysis**: Extracts file metadata including type, size, executable status, and archive contents
- 🎨 **Dual Interface**: Both CLI and GUI interfaces available
- 🔧 **Flexible Configuration**: Support for multiple LLM providers (OpenAI, Azure, Local/Llama)
- 🧪 **Dry Run Mode**: Preview categorization without actually moving files

## Installation

### From PyPI (coming soon)
```bash
pip install ai-file-organizer
```

### From Source
```bash
git clone https://github.com/rdar-lab/ai-file-organizer.git
cd ai-file-organizer
pip install -e .
```

## Quick Start

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
  provider: openai  # openai, azure, or local
  model: gpt-3.5-turbo
  temperature: 0.3
  api_key: YOUR_API_KEY_HERE
  
  # For Azure
  # azure_endpoint: https://your-resource.openai.azure.com/
  # deployment_name: your-deployment
  
  # For Local LLM
  # base_url: http://localhost:8000/v1

# Category labels
labels:
  - Documents
  - Images
  - Videos
  - Audio
  - Archives
  - Code
  - Other
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
--provider           LLM provider: openai, azure, or local (default: openai)
--model              Model name (default: gpt-3.5-turbo)
--api-key            API key for the LLM provider
--azure-endpoint     Azure endpoint URL (for Azure provider)
--base-url           Base URL for local LLM (for local provider)
--temperature        Temperature for LLM (default: 0.3)
--dry-run            Perform a dry run without actually moving files
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

### Example 3: Use Azure OpenAI
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

## Development

### Running Tests
```bash
pytest tests/
```

### Running Tests with Coverage
```bash
pytest --cov=ai_file_organizer tests/
```

## Requirements

- Python 3.8+
- langchain
- openai
- python-magic
- PySimpleGUI (for GUI)
- pyyaml

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on [GitHub](https://github.com/rdar-lab/ai-file-organizer/issues).
