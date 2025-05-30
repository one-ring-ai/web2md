# Web2MD - Web Content to Markdown Converter

English

[![License: AGPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

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
  - [Manual Setup](#manual-setup)
  - [Usage](#usage)
    - [Search Endpoint](#search-endpoint)
    - [Fetch URL Content](#fetch-url-content)
    - [Fetching Images](#fetching-images)
    - [Fetching Videos](#fetching-videos)
  - [Using Proxies](#using-proxies)
  - [Roadmap](#roadmap)
  - [Code Explanation](#code-explanation)
  - [License](#license)
  - [Author](#author)
  - [Contributing](#contributing)
  - [Acknowledgements](#acknowledgements)
  - [Star History](#star-history)

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

## Prerequisites

Ensure you have the following installed:

- Python 3.11
- Virtualenv
- Docker

## Docker Setup

You can use Docker to simplify the setup process. Follow these steps:

1. **Clone the repository**:
    ```sh
    git clone https://github.com/lucanori/web2md.git
    cd web2md
    ```

2. **Run Docker Compose**:
    ```sh
    docker compose up --build
    ```

With this setup, if you change the `.env` or `main.py` file, you no longer need to restart Docker. Changes will be reloaded automatically.

## Manual Setup

Follow these steps for manual setup:

1. **Clone the repository**:
    ```sh
    git clone https://github.com/lucanori/web2md.git
    cd web2md
    ```

2. **Create and activate virtual environment**:
    ```sh
    virtualenv venv
    source venv/bin/activate
    ```

3. **Install dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

4. **Create a .env file** in the root directory with the following content:
    ```bash
    SEARXNG_URL=http://searxng:8080
    BROWSERLESS_URL=http://browserless:3000
    BROWSERLESS_TOKEN=your_browserless_token_here  # Replace with your actual token
    # PROXY_PROTOCOL=http
    # PROXY_URL=your_proxy_url
    # PROXY_USERNAME=your_proxy_username
    # PROXY_PASSWORD=your_proxy_password
    # PROXY_PORT=your_proxy_port
    REQUEST_TIMEOUT=30

    # AI Integration for search result filter (OpenAI-compatible APIs)
    FILTER_SEARCH_RESULT_BY_AI=true
    AI_API_KEY=your_api_key_here
    AI_MODEL=google/gemini-2.5-flash-preview-05-20
    AI_BASE_URL=https://openrouter.ai/api/v1

    # Examples for different providers:
    # OpenAI: AI_BASE_URL=https://api.openai.com/v1
    # GROQ: AI_BASE_URL=https://api.groq.com/openai/v1
    # OpenRouter: AI_BASE_URL=https://openrouter.ai/api/v1
    # Ollama: AI_BASE_URL=http://localhost:11434/v1
    # LM Studio: AI_BASE_URL=http://localhost:1234/v1
    ```

5. **Run Docker containers for SearXNG and Browserless**:
    ```sh
    ./run-services.sh
    ```

6. **Start the FastAPI application**:
    ```sh
    uvicorn main:app --host 0.0.0.0 --port 7001
    ```

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

## Roadmap

- [x] **FastAPI**: A modern, fast web framework for building APIs with Python.
- [x] **SearXNG**: An open-source internet metasearch engine.
- [x] **Browserless**: A web browser automation service.
- [x] **Markdown Output**: Converts HTML content to Markdown format.
- [x] **Proxy Support**: Utilizes proxies for secure and anonymous scraping.
- [x] **AI Integration (Reranker AI)**: Filters search results using AI to provide the most relevant content.
- [x] **YouTube Transcriptions**: Fetches YouTube video transcriptions.
- [x] **Image and Video Search**: Fetches images and video results using SearXNG.

## Code Explanation

For a detailed explanation of the code, visit the article [here](https://www.essamamdani.com/search-result-scraper-markdown).

## License

This project is licensed under the GPLv3 License. See the [LICENSE](LICENSE) file for details.

## Author

Luca Nori - [lucanori](https://github.com/lucanori)

Original work by Essa Mamdani - [essamamdani.com](https://essamamdani.com)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [SearXNG](https://github.com/searxng/searxng)
- [Browserless](https://www.browserless.io/)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=lucanori/web2md&type=Date)](https://star-history.com/#lucanori/web2md&Date)
