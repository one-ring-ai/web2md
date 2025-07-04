# Web2MD - Web Content to Markdown Converter

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

## Description

Web2MD is a powerful web scraping tool that fetches search results and converts web content into clean Markdown format using FastAPI, SearXNG, and Browserless. It includes the capability to use proxies for web scraping and handles HTML content conversion to Markdown efficiently. Features AI Integration for filtering search results using OpenAI-compatible APIs. Alternatives include Jina.ai, FireCrawl AI, Exa AI, and 2markdown, offering various web scraping and search engine solutions for developers.

## Table of Contents
- [Web2MD - Web Content to Markdown Converter](#web2md---web-content-to-markdown-converter)
  - [Description](#description)
  - [Table of Contents](#table-of-contents)
  - [Alternatives:](#alternatives)
  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Docker Setup](#docker-setup)
  - [Local Development Setup](#local-development-setup)
  - [Usage](#usage)
    - [Search Endpoint](#search-endpoint)
    - [Fetch URL Content](#fetch-url-content)
    - [Fetching Images](#fetching-images)
    - [Fetching Videos](#fetching-videos)
  - [Token Usage Control](#token-usage-control)
  - [Roadmap](#roadmap)
  - [License](#license)
  - [Author](#author)
  - [Contributing](#contributing)
  - [Acknowledgements](#acknowledgements)

## Alternatives:

- [Jina.ai](https://jina.ai/): A powerful search engine for developers.
- [FireCrawl AI](https://firecrawl.dev/): A web scraping API for developers.
- [Exa AI](https://exa.ai/): A web scraping API for developers.
- [2markdown](https://2markdown.com/): A web scraping tool that converts HTML to Markdown.

## Features

- **FastAPI**: A modern, fast web framework for building APIs with Python.
- **SearXNG**: An open-source internet metasearch engine.
- **Browserless**: A web browser automation service.
- **Markdown Output**: Converts HTML content to Markdown format.
- **Proxy Support**: Utilizes proxies for secure and anonymous scraping.
- **AI Integration (Reranker AI)**: Filters search results using AI to provide the most relevant content.
- **YouTube Transcriptions**: Fetches YouTube video transcriptions.
- **Image and Video Search**: Fetches images and video results using SearXNG.
- **Token Usage Control**: Configurable limits for images and content to manage token consumption.
- **Development Environment**: Separate dev environment with dedicated scripts and configuration.

## Prerequisites

Ensure you have the following installed:

- Python 3.11
- Virtualenv
- Docker

## Docker Setup

You can use Docker to simplify the setup process. Follow these steps:

1. **Run Docker Compose**:
    ```sh
    docker compose up -d
    ```

## Local Development Setup

For local development, we recommend using `uv` (a fast Python package manager) instead of traditional `pip` and `virtualenv`:

### Prerequisites
- Python 3.11+
- uv package manager

### Installation

1. **Install uv** (if not already installed):
    ```sh
    # Linux/macOS
    curl -Ls https://astral.sh/uv/install.sh | sh
    
    # Windows (PowerShell)
    irm https://astral.sh/uv/install.ps1 | iex
    
    # Using pip (any platform)
    pip install uv
    ```

2. **Clone the repository**:
    ```sh
    git clone https://github.com/lucanori/web2md.git
    cd web2md
    ```

3. **Create and activate virtual environment**:
    ```sh
    # Create virtual environment
    uv venv
    
    # Activate environment
    source .venv/bin/activate  # Linux/macOS
    .\.venv\Scripts\activate   # Windows
    ```

4. **Install dependencies**:
    ```sh
    uv pip install -r requirements.txt
    ```

5. **Create a .env file** in the root directory with the following content:
    ```bash
    # For local development (when running FastAPI locally)
    SEARXNG_URL=http://localhost:7002
    BROWSERLESS_URL=http://localhost:7003
    BROWSERLESS_TOKEN=your_browserless_token_here  # Replace with your actual token
    # PROXY_PROTOCOL=http
    # PROXY_URL=your_proxy_url
    # PROXY_USERNAME=your_proxy_username
    # PROXY_PASSWORD=your_proxy_password
    # PROXY_PORT=your_proxy_port
    REQUEST_TIMEOUT=30

    # Websites processing limits
    MAX_IMAGES_PER_SITE=0 # For llms: images increase by a lot input tokens
    MIN_IMAGE_SIZE=256
    MAX_TOKENS_PER_REQUEST=100000

    # AI Integration for search result filter (OpenAI-compatible APIs)
    FILTER_SEARCH_RESULT_BY_AI=true
    AI_API_KEY=your_api_key_here
    AI_MODEL=google/gemini-2.5-flash
    AI_BASE_URL=https://openrouter.ai/api/v1

    # Examples for different providers:
    # OpenAI: AI_BASE_URL=https://api.openai.com/v1
    # GROQ: AI_BASE_URL=https://api.groq.com/openai/v1
    # OpenRouter: AI_BASE_URL=https://openrouter.ai/api/v1
    # Ollama: AI_BASE_URL=http://localhost:11434/v1
    # LM Studio: AI_BASE_URL=http://localhost:1234/v1
    ```

6. **Run Docker containers for SearXNG and Browserless**:
    ```sh
    sh dev/run-services.sh
    ```

7. **Start the FastAPI application**:
    ```sh
    uvicorn main:app --host 0.0.0.0 --port 7001 --reload --env-file dev/.env
    ```

### Development Tips

- **Auto-reload**: Use `--reload` flag with uvicorn for automatic reloading during development
- **Fast dependency updates**: Use `uv pip install package_name` for quick package installation
- **Environment management**: uv creates lightweight virtual environments (~12ms vs 500ms-2s with traditional tools)
- **Cross-platform compatibility**: Use `uv pip compile requirements.in --universal` for platform-independent requirements

## Usage

### Search Endpoint

To perform a search query, send a GET request to the root endpoint `/` with the query parameters `q` (search query), `num_results` (number of results), and `format` (get response in JSON or by default in Markdown).

Example:
```sh
curl "http://localhost:7001/?q=python&num_results=5&format=json" # for JSON format
curl "http://localhost:7001/?q=python&num_results=5" # by default Markdown
```

### Fetch URL Content

To fetch and convert the content of a specific URL to Markdown, send a GET request to the `/r/{url:path}` endpoint.

Example:
```sh
curl "http://localhost:7001/r/https://example.com&format=json" # for JSON format
curl "http://localhost:7001/r/https://example.com" # by default Markdown
```

### Fetching Images

To fetch image search results, send a GET request to the `/images` endpoint with the query parameters `q` (search query) and `num_results` (number of results).
Note that you have to enable image processing in the `.env` file.

Example:
```sh
curl "http://localhost:7001/images?q=puppies&num_results=5"
```

### Fetching Videos

To fetch video search results, send a GET request to the `/videos` endpoint with the query parameters `q` (search query) and `num_results` (number of results).

Example:
```sh
curl "http://localhost:7001/videos?q=cooking+recipes&num_results=5"
```

## Token Usage Control

Web2MD includes configurable limits to manage token consumption when processing websites with many images or large amounts of content. This is particularly important when using the output with LLMs that have token limits.

### Configuration Options

- `MAX_IMAGES_PER_SITE=3` - Maximum number of images to process per website (set to 0 to disable images completely)
- `MIN_IMAGE_SIZE=256` - Minimum image size in pixels (256x256px) to filter out small icons and decorative images
- `MAX_TOKENS_PER_REQUEST=100000` - Maximum tokens per request before content is truncated, useful for llms

### Token Usage Estimates

Based on our testing with 20 different queries, here are rough estimates for token usage:

**Normal Websites** (news, general content):
- Average: ~28,200 tokens per query
- Range: 14,700 - 51,500 tokens
- Examples: News articles, blog posts, general information sites

**Documentation Websites** (technical content):
- Average: ~19,100 tokens per query
- Range: 3,700 - 48,300 tokens
- Examples: Programming tutorials, API documentation, technical guides

**Important Notes:**
- These are rough estimates and token usage can vary significantly
- Individual results can range from 3,700 tokens (simple docs) to 51,500 tokens (complex articles)
- For example: pandas tutorial used ~48,000 tokens while TypeScript interfaces guide used only ~7,800 tokens
- See `test/token_usage_results.json` for detailed test results

### Testing Token Usage

You can run your own token usage tests:

```bash
# Start web2md
sh dev/run-services.sh
uvicorn main:app --host 0.0.0.0 --port 7001 --reload --env-file dev/.env

# Run token usage test
sh test/run_test.sh
```

The test will process various queries and provide detailed statistics about token usage patterns.

## Roadmap

- [x] **FastAPI**: A modern, fast web framework for building APIs with Python.
- [x] **SearXNG**: An open-source internet metasearch engine.
- [x] **Browserless**: A web browser automation service.
- [x] **Markdown Output**: Converts HTML content to Markdown format.
- [x] **Proxy Support**: Utilizes proxies for secure and anonymous scraping.
- [x] **AI Integration (Reranker AI)**: Filters search results using AI to provide the most relevant content.
- [x] **YouTube Transcriptions**: Fetches YouTube video transcriptions.
- [x] **Image and Video Search**: Fetches images and video results using SearXNG.
- [x] **Token Usage Control**: Configurable limits for images and content to manage token consumption.
- [x] **Development Environment**: Separate dev environment with dedicated scripts and configuration.
- [x] **Token Usage Testing**: Automated testing suite to measure and analyze token consumption patterns.
- [ ] **Whisper STT Integration for videos**: Integrates Whisper STT for more accurate transcriptions in video search results.

## License

This project is licensed under the GPLv3 License. See the [LICENSE](LICENSE) file for details.

## Author

Luca Nori - [lucanori](https://github.com/lucanori)

Original work by Essa Mamdani - [search-result-scraper-markdown](https://github.com/essamamdani/search-result-scraper-markdown)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [SearXNG](https://github.com/searxng/searxng)
- [Browserless](https://www.browserless.io/)