# Docker deployment instructions

## Quick Start with Docker

### Build the Docker image

```bash
docker build -t ai-file-organizer .
```

### Run with Docker Compose

1. Create your configuration file `config.yml`:

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
  - Archives
  - Code
  - Other
```

2. Create input directory and add files to organize:

```bash
mkdir -p input output
# Add files to input/
```

3. Set environment variables (optional):

```bash
export OPENAI_API_KEY=your-api-key-here
```

4. Run with docker-compose:

```bash
docker-compose up
```

### Run with plain Docker

```bash
docker run -v $(pwd)/input:/input \
           -v $(pwd)/output:/output \
           -v $(pwd)/config.yml:/app/config.yml \
           -e OPENAI_API_KEY=your-key \
           ai-file-organizer \
           ai-file-organizer -i /input -o /output -c /app/config.yml
```

### Run with local LLM (Ollama)

1. Start Ollama service:

```bash
docker-compose up -d ollama
```

2. Pull a model (e.g., llama2):

```bash
docker exec -it ai-file-organizer-ollama ollama pull llama2
```

3. Update your config.yml to use local provider:

```yaml
ai:
  provider: local
  model: llama2
  temperature: 0.3
  base_url: http://ollama:11434/v1
  api_key: not-needed

labels:
  - Documents
  - Images
  - Code
  - Other
```

4. Run the organizer:

```bash
docker-compose up ai-file-organizer
```

## Development

### Build for development

```bash
docker build -t ai-file-organizer:dev .
```

### Run tests in Docker

```bash
docker run ai-file-organizer:dev pytest tests/
```

### Interactive shell

```bash
docker run -it --entrypoint /bin/bash ai-file-organizer
```

## Docker Hub Deployment

### Tag and push to Docker Hub

```bash
docker tag ai-file-organizer:latest yourusername/ai-file-organizer:latest
docker tag ai-file-organizer:latest yourusername/ai-file-organizer:v0.1.0
docker push yourusername/ai-file-organizer:latest
docker push yourusername/ai-file-organizer:v0.1.0
```

### Pull from Docker Hub

```bash
docker pull yourusername/ai-file-organizer:latest
```
