# User Guide

## Introduction

AI File Organizer is a tool that uses artificial intelligence to automatically categorize and organize your files. It analyzes file metadata and uses language models to make intelligent decisions about how to categorize your files.

## Getting Started

### Installation

Install the package using pip:

```bash
pip install ai-file-organizer
```

Or install from source:

```bash
git clone https://github.com/rdar-lab/ai-file-organizer.git
cd ai-file-organizer
pip install -e .
```

### First Time Setup

1. **Get an API Key**: You'll need an API key from one of the supported providers:
   - OpenAI: https://platform.openai.com/api-keys
   - Azure OpenAI: Contact your Azure administrator
   - Local LLM: Set up a local LLM server (e.g., using Ollama)

2. **Create a Configuration File** (optional but recommended):

```yaml
ai:
  provider: openai
  model: gpt-3.5-turbo
  temperature: 0.3
  api_key: YOUR_API_KEY

labels:
  - Documents
  - Images
  - Videos
  - Audio
  - Code
  - Archives
  - Other
```

Save this as `config.yml`.

## Using the CLI

### Basic Usage

The simplest way to use the CLI:

```bash
ai-file-organizer -i /path/to/input -o /path/to/output -c config.yml
```

### Command-Line Options

- `-i, --input`: Path to the folder containing files to organize
- `-o, --output`: Path where organized files should be saved
- `-l, --labels`: List of categories (e.g., `-l Documents Images Videos`)
- `-c, --config`: Path to YAML configuration file
- `--provider`: LLM provider (openai, azure, or local)
- `--model`: Model name
- `--api-key`: API key for the LLM
- `--dry-run`: Preview what would happen without moving files

### Examples

**Organize Downloads folder:**
```bash
ai-file-organizer \
  -i ~/Downloads \
  -o ~/OrganizedDownloads \
  -l Documents Images Videos Audio Other \
  --api-key sk-YOUR_KEY
```

**Dry run to preview:**
```bash
ai-file-organizer \
  -i ~/Downloads \
  -o ~/OrganizedDownloads \
  -c config.yml \
  --dry-run
```

**Use custom categories:**
```bash
ai-file-organizer \
  -i ./my-files \
  -o ./organized \
  -l "Work Documents" "Personal Photos" "Project Files" "Misc" \
  --api-key sk-YOUR_KEY
```

## Using the GUI

Launch the GUI application:

```bash
ai-file-organizer-gui
```

### GUI Features

1. **Folder Selection**: Browse and select input/output folders
2. **Label Configuration**: Define custom categories (comma-separated)
3. **LLM Settings**: Configure provider, model, and API key
4. **Progress Tracking**: Real-time progress updates
5. **Dry Run**: Test without moving files

### Step-by-Step GUI Usage

1. Click "Browse" next to Input Folder and select your source folder
2. Click "Browse" next to Output Folder and select destination
3. Enter your categories in the Labels field (comma-separated)
4. Select your LLM provider from the dropdown
5. Enter your API key
6. Optionally check "Dry Run" to preview
7. Click "Start Organizing"

## Configuration File Reference

### Full Configuration Example

```yaml
# AI/LLM Configuration
ai:
  provider: openai           # Options: openai, azure, local
  model: gpt-3.5-turbo      # Model name
  temperature: 0.3           # 0.0-1.0, lower is more deterministic
  api_key: YOUR_KEY         # Or use environment variable
  
  # Azure-specific (only if provider is azure)
  azure_endpoint: https://your-resource.openai.azure.com/
  deployment_name: your-deployment
  
  # Local LLM (only if provider is local)
  base_url: http://localhost:8000/v1

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

## How Categorization Works

The tool analyzes each file and extracts:

1. **File Name**: The name of the file
2. **File Type**: Extension and format
3. **File Size**: Size in bytes
4. **MIME Type**: Internet media type
5. **Executable Status**: Whether the file is executable
6. **Archive Contents**: List of files (for ZIP, TAR archives)
7. **Metadata**: Creation time, modification time, permissions

This information is sent to the AI model with a prompt asking it to categorize the file into one of your specified labels.

## Tips and Best Practices

### Choosing Labels

- Be specific but not too narrow
- Use 5-10 labels for best results
- Common categories: Documents, Images, Videos, Audio, Code, Archives
- You can use spaces in label names: "Work Documents", "Personal Photos"

### Choosing Temperature

- **0.0-0.3**: Very consistent, deterministic categorization
- **0.4-0.7**: Balanced, some variation
- **0.8-1.0**: More creative, less predictable

For file organization, we recommend 0.3 or lower.

### Using Dry Run

Always test with `--dry-run` first to:
- Verify API credentials work
- Check categorization results
- Ensure labels are appropriate
- Preview file movements

### Performance Tips

- For large folders, use gpt-3.5-turbo (faster and cheaper)
- For better accuracy, use gpt-4
- Local LLMs can be faster but may be less accurate

## Troubleshooting

### "Error: No labels specified"
- Add labels using `-l` flag or include them in config file

### "Invalid API key"
- Check your API key is correct
- Ensure you're using the right provider (openai vs azure)
- For OpenAI, key should start with 'sk-'

### "Input folder does not exist"
- Verify the path to your input folder is correct
- Use absolute paths to avoid confusion

### Files not categorizing correctly
- Try increasing temperature slightly
- Use more descriptive label names
- Consider using a more powerful model (gpt-4)

### "Module not found" errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- On Linux, you may need to install libmagic: `sudo apt-get install libmagic1`

## Advanced Usage

### Environment Variables

You can set API keys via environment variables instead of command line:

```bash
export OPENAI_API_KEY=sk-YOUR_KEY
ai-file-organizer -i input -o output -l Documents Images Videos
```

For Azure:
```bash
export AZURE_OPENAI_API_KEY=your-key
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

### Batch Processing

Process multiple folders using a shell script:

```bash
#!/bin/bash
for folder in folder1 folder2 folder3; do
  ai-file-organizer -i "$folder" -o "organized_$folder" -c config.yml
done
```

### Integration with Other Tools

The tool can be integrated into workflows:

```bash
# Download files, then organize them
wget -P downloads/ https://example.com/files.zip
unzip downloads/files.zip -d downloads/
ai-file-organizer -i downloads/ -o organized/ -c config.yml
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/rdar-lab/ai-file-organizer/issues
- Documentation: https://github.com/rdar-lab/ai-file-organizer/tree/main/docs
