# Web2MD - Web Content to Markdown Converter

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

## Description

Web2MD is a powerful web scraping tool that fetches search results and converts web content into clean Markdown format using FastAPI, SearXNG, and Browserless. It includes advanced AI Integration for filtering search results using OpenAI-compatible APIs, intelligent auto-research capabilities, and comprehensive media processing. Features include proxy support for web scraping, efficient HTML to Markdown conversion, and an advanced auto-research system that can intelligently gather information from multiple sources. Alternatives include Jina.ai, FireCrawl AI, Exa AI, and 2markdown, offering various web scraping and search engine solutions for developers.

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
    - [Auto-Research Endpoint (NEW)](#auto-research-endpoint-new)
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
- **Advanced AI Integration**: Filters and reranks search results using AI to provide the most relevant content.
- **YouTube Transcriptions**: Fetches YouTube video transcriptions for enhanced content analysis.
- **AI-Enhanced Media Search**: AI-powered reranking for both images and video results with transcript analysis.
- **Auto-Research System (NEW)**: Intelligent multi-step research that autonomously decides when to gather more information from different sources.
- **YouTube Rate Limiting Protection**: Intelligent detection and temporary disabling of video endpoints to prevent IP bans.
- **Token Usage Control**: Configurable limits for images and content to manage token consumption.
- **Development Environment**: Separate dev environment with dedicated scripts and configuration.
- **Queue-Based Processing**: Handles concurrent auto-research requests with intelligent queuing.
- **Cost Tracking**: Real-time cost calculation for AI API usage with OpenRouter integration.
- **Database-Backed Storage**: SQLite database for request tracking, audit trails, and automated cleanup.
- **Comprehensive Source References**: Both search and auto-research endpoints include structured source links from AI reranker for complete attribution tracking.

## Prerequisites

Ensure you have the following installed:

- Python 3.11
- Virtualenv
- Docker

## Quick Start with Docker (Recommended)

The easiest way to get Web2MD running with all dependencies is using Docker Compose:

### Prerequisites
- Docker and Docker Compose installed
- An OpenRouter API key (or compatible LLM provider)

### Setup Steps

1. **Clone the repository**:
    ```sh
    git clone https://github.com/lucanori/web2md.git
    cd web2md
    ```

2. **Create your environment file**:
    ```sh
    cp .env.example .env
    # Edit .env and add your API key:
    # WEB2MD_LLM_API_KEY=your_openrouter_api_key_here
    ```

3. **Start all services**:
    ```sh
    docker compose up
    ```

4. **Access the application**:
    - **Web2MD API**: http://localhost:7001
    - **SearXNG**: http://localhost:7002 
    - **Browserless**: http://localhost:7003

### Development Mode

The Docker setup includes auto-reload functionality - any changes to your code will automatically restart the FastAPI application. Perfect for development!

### Stop Services

```sh
docker compose down
```

### What's Included

The unified Docker setup provides:
- **🔍 SearXNG**: Metasearch engine for web searches
- **🌐 Browserless**: Headless Chrome for web scraping
- **⚡ FastAPI**: The main Web2MD application with auto-reload
- **🔄 Auto-rebuild**: Code changes trigger automatic restarts
- **📁 Volume mounting**: Live code editing without rebuilding

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
    WEB2MD_LLM_API_KEY=your_api_key_here
    AI_MODEL=google/gemini-2.5-flash
    AI_BASE_URL=https://openrouter.ai/api/v1

    # Auto-research feature settings
    AUTO_MAX_REQUESTS=5
    AUTO_MAX_CONTEXT_TOKENS=850000
    DB_CLEANUP_RETENTION_DAYS=90

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

To perform a search query, send a GET request to the `/search` endpoint with the query parameters `q` (search query), `num_results` (number of results), and `format` (get response in JSON or by default in Markdown).

Example:
```sh
curl "http://localhost:7001/search?q=python&num_results=5&format=json" # for JSON format
curl "http://localhost:7001/search?q=python&num_results=5" # by default Markdown
```

#### Enhanced JSON Response Format

When using `format=json`, the search endpoint now returns a structured response that includes both the processed content and the source URLs selected by the AI reranker:

```json
{
  "content": [
    {
      "title": "Python Programming Guide",
      "url": "https://example.com/python-guide",
      "markdown_content": "# Python Programming...",
      "images": [...]
    }
  ],
  "source_references": {
    "links": [
      {
        "url": "https://example.com/python-guide",
        "title": "Python Programming Guide",
        "relevance": "Query: python"
      },
      {
        "url": "https://docs.python.org/3/",
        "title": "Python Documentation",
        "relevance": "Query: python"
      }
    ]
  },
  "metadata": {
    "query": "python",
    "num_results": 2,
    "total_sources": 5,
    "ai_reranked": true
  }
}
```

This format provides:
- **content**: The processed markdown content from each URL
- **source_references**: All URLs that were selected by the AI reranker
- **metadata**: Query information and processing statistics

This makes it easy for UIs to display both the content and provide proper source attribution.

### Auto-Research Endpoint (NEW)

**🚀 Intelligent Multi-Step Research System**

The auto-research endpoint provides an advanced AI-powered research system that can autonomously gather comprehensive information from multiple sources. The system intelligently decides when and how to collect more information based on the user's query.

#### How It Works:
1. **Initial Search**: Always starts with a web search to gather basic information
2. **AI Decision Making**: Uses AI to analyze if more information is needed
3. **Multi-Source Gathering**: Can automatically search videos, images, or additional web content
4. **Smart Stopping**: AI decides when sufficient information has been collected
5. **Comprehensive Response**: Generates a well-structured markdown response with media references

#### Starting Auto-Research:
```sh
curl "http://localhost:7001/auto?q=how+to+implement+authentication+in+web+applications"
```

Response:
```json
{
  "request_id": "unique-uuid-here",
  "status": "queued", 
  "check_endpoint": "/auto/status/unique-uuid-here"
}
```

#### Checking Status/Getting Results:
```sh
curl "http://localhost:7001/auto/status/unique-uuid-here"
```

Response when completed:
```json
{
  "status": "completed",
  "result": {
    "markdown_response": "# Complete Research Response\n\n...",
    "media_references": {
      "videos": [
        {"url": "https://youtube.com/...", "title": "Tutorial Title", "relevance": "Query context"}
      ],
      "images": [
        {"url": "https://example.com/image.jpg", "title": "Image Title", "description": "Description"}
      ],
      "search_links": [
        {"url": "https://docs.example.com/auth", "title": "Authentication Guide", "relevance": "Query: authentication"},
        {"url": "https://blog.example.com/security", "title": "Security Best Practices", "relevance": "Query: web security"}
      ]
    },
    "metadata": {
      "total_requests_used": 3,
      "endpoints_called": ["search", "videos", "images"],
      "queries_used": ["original query", "adapted video query", "adapted image query"],
      "total_tokens": 45231
    },
    "websearch_price": 0.0085
  }
}
```

#### Auto-Research Features:
- **🧠 AI-Driven Decisions**: Automatically determines optimal research strategy
- **📊 Cost Tracking**: Real-time cost calculation from OpenRouter API
- **🔄 Queue System**: Handles multiple concurrent requests efficiently
- **📱 UI-Ready Output**: Separate media references for easy web integration
- **⚡ Token Management**: Intelligent context management with configurable limits
- **📈 Audit Trail**: Complete research history stored in database
- **🧹 Auto-Cleanup**: Automatic cleanup of old research data
- **🔗 Complete Source Tracking**: Aggregates all URLs selected by AI reranker from web searches, videos, and images

### Fetch URL Content

To fetch and convert the content of a specific URL to Markdown, send a GET request to the `/r/{url:path}` endpoint.

Example:
```sh
curl "http://localhost:7001/r/https://example.com&format=json" # for JSON format
curl "http://localhost:7001/r/https://example.com" # by default Markdown
```

### Fetching Images

To fetch AI-enhanced image search results, send a GET request to the `/images` endpoint with the query parameters `q` (search query) and `num_results` (number of results). The system now includes AI reranking for more relevant results.

Example:
```sh
curl "http://localhost:7001/images?q=python+programming+diagram&num_results=5"
```

### Fetching Videos

To fetch AI-enhanced video search results with transcript analysis, send a GET request to the `/videos` endpoint with the query parameters `q` (search query), `num_results` (number of results), and optionally `format` for output format.

The videos endpoint now features:
- **AI Reranking**: Videos ranked by transcript content relevance
- **Multiple Formats**: metadata (default), transcripts, or json
- **Transcript Integration**: Uses actual video content for better matching
- **Rate Limiting Protection**: Automatic detection and prevention of YouTube IP bans

Example:
```sh
curl "http://localhost:7001/videos?q=python+machine+learning+tutorial&num_results=5&format=transcripts"
```

### YouTube Rate Limiting Protection

Web2MD includes intelligent protection against YouTube rate limiting to prevent permanent IP bans:

#### How It Works:
- **Automatic Detection**: Recognizes YouTube rate limiting error messages
- **Smart Disabling**: Temporarily disables video endpoints for 1 hour when rate limited
- **Auto-Recovery**: Automatically re-enables video functionality after cooldown period
- **LLM Integration**: Informs the auto-research AI when videos are unavailable

#### Checking Video Status:
```sh
curl "http://localhost:7001/status/videos"
```

Response when disabled:
```json
{
  "videos_disabled": true,
  "cooldown_remaining_seconds": 2847,
  "cooldown_remaining_minutes": 47,
  "reason": "YouTube rate limiting protection",
  "status": "disabled"
}
```

#### Protected Scenarios:
- Direct video endpoint calls (`/videos`)
- Auto-research video searches
- Video transcript fetching
- AI reranking with transcript analysis

This protection ensures your IP doesn't get permanently banned from YouTube, especially important when running on cloud providers (AWS, GCP, Azure) which are commonly blocked by YouTube.

## Token Usage Control

Web2MD includes configurable limits to manage token consumption when processing websites with many images or large amounts of content. This is particularly important when using the output with LLMs that have token limits.

### Configuration Options

- `MAX_IMAGES_PER_SITE=3` - Maximum number of images to process per website (set to 0 to disable images completely)
- `MIN_IMAGE_SIZE=256` - Minimum image size in pixels (256x256px) to filter out small icons and decorative images
- `MAX_TOKENS_PER_REQUEST=100000` - Maximum tokens per request before content is truncated, useful for llms
- `AUTO_MAX_CONTEXT_TOKENS=850000` - Maximum tokens for auto-research context (with 50k tolerance)

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

**Auto-Research System**:
- Intelligent token management with configurable limits
- Context truncation when approaching limits
- Real-time token counting for optimal resource usage

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
- [x] **AI-Enhanced Media Search**: AI reranking for images and video results with transcript analysis.
- [x] **Auto-Research System**: Intelligent multi-step research with AI decision-making.
- [x] **Token Usage Control**: Configurable limits for images and content to manage token consumption.
- [x] **Development Environment**: Separate dev environment with dedicated scripts and configuration.
- [x] **Token Usage Testing**: Automated testing suite to measure and analyze token consumption patterns.
- [x] **Search Endpoint Restructure**: Moved main search from "/" to "/search" for better API organization.
- [x] **Queue-Based Processing**: Concurrent request handling with intelligent queuing system.
- [x] **Cost Tracking Integration**: Real-time cost calculation with OpenRouter API integration.
- [x] **Database Storage System**: SQLite-based storage for audit trails and automated cleanup.
- [x] **YouTube Rate Limiting Protection**: Intelligent detection and temporary disabling to prevent IP bans.
- [x] **Comprehensive Source Reference Integration**: Enhanced responses with structured source links from AI reranker across all endpoints (search, auto-research).
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