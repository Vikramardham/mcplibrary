# Link Fetcher

A powerful CLI tool to fetch all links from a webpage and organize them into a meaningful tree structure.

## Installation

```bash
# Using pip
pip install -e .

# Using uv (recommended)
uv pip install -e .

# Install required dependencies
uv pip install --upgrade google-genai python-dotenv
```

## Features

- Fetch all links from any webpage
- Display links in different formats (table, text, tree)
- Automatically categorize links by URL structure
- Use Google's Generative AI (Gemini) to intelligently categorize links
- Displays both URL-based and AI-enhanced tree structures for comparison
- Beautify output with rich terminal formatting
- Support for loading API keys from .env file

## Usage

```bash
# Basic usage - displays a table with URLs and link text
python src/link_fetcher.py example.com

# Display only URLs without link text
python src/link_fetcher.py example.com --no-text

# Output as plain text
python src/link_fetcher.py example.com --output text

# Generate tree structures (both URL-based and AI-enhanced) of the website
python src/link_fetcher.py example.com --output tree
```

## Options

- `url`: URL of the webpage to fetch links from (required)
- `--no-text`: Don't include link text in the output
- `--output`: Output format, choices: `table` (default), `text`, or `tree`
- `--api-key`: Google API key for using Generative AI categorization (optional if defined in .env file)
- `--save-to`: Save output to files with this base filename (will append _conventional.txt, _llm.txt, etc.)

## Tree Structure Feature

The tree structure feature organizes links in a hierarchical way to help users understand the website's organization. The tool generates two different tree structures for comparison:

### 1. Conventional Tree (URL-based Structure)

This tree organizes links based on their URL structure:
- Groups links by domain
- Categorizes links based on path segments
- Separates external links
- Useful for understanding the technical organization of the site

### 2. Enhanced Tree (AI-based Structure)

This tree uses Google's Gemini AI to intelligently categorize links:
- Identifies meaningful categories based on link content and purpose
- Creates intuitive groupings
- Highlights important links
- Provides category descriptions
- Useful for understanding the conceptual organization of the site

The tool displays both trees side by side, allowing you to compare how URL structure differs from conceptual organization.

Example:
```bash
python src/link_fetcher.py python.org --output tree
```

### Setting up Google API Key (Required)

The tool requires a Google Gemini API key. To set up:

1. **Create a .env file (Required)**:
   - Create a `.env` file in the project root with:
   ```
   GEMINI_API_KEY=your-key-here
   ```
   - The tool will automatically read the key from this file

2. **Alternative method**:
   - Use `--api-key YOUR_API_KEY` when running the tool

To get a Google Generative AI API key:
1. Go to [Google AI Studio](https://makersuite.google.com/)
2. Sign in with your Google account
3. Create a new API key or use an existing one

For more information, run:
```bash
python src/link_fetcher/api_setup.py
```

## Gemini SDK Integration

This tool uses the latest Google Gen AI SDK which provides a unified interface to Gemini models:

```python
# Example of how the tool uses the Gemini SDK
from google import genai

# Create a client with your API key
client = genai.Client(api_key=your_api_key)

# Generate content using the client
response = client.models.generate_content(
    model="gemini-1.5-pro",
    contents="Your prompt here"
)

# Process the response
result = response.text
```

## Dependencies

- httpx: For making HTTP requests
- BeautifulSoup4: For parsing HTML
- Rich: For beautiful terminal output
- Treelib: For creating tree structures
- python-dotenv: For loading environment variables from .env file (required)
- Google Gen AI SDK: For intelligent link categorization (required)

## Development

To set up the development environment:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv
uv pip install -e .
uv pip install --upgrade google-genai python-dotenv
```

## Examples

```bash
# Basic usage - displays a table with URLs and link text
python src/link_fetcher.py example.com

# Display only URLs without link text
python src/link_fetcher.py example.com --no-text

# Output as plain text
python src/link_fetcher.py example.com --output text

# Generate tree structures (both URL-based and AI-enhanced) of the website
python src/link_fetcher.py example.com --output tree

# Save the tree structures to files
python src/link_fetcher.py example.com --output tree --save-to ./output/example_trees
```

### File Output

When using the `--save-to` option, the tool generates the following files:

1. `<filename>_conventional.txt`: The URL-based tree in plain text format
2. `<filename>_llm.txt`: The AI-enhanced tree in plain text format
3. `<filename>_rich.txt`: Both trees with detailed formatting and descriptions
4. `<filename>_trees.json`: JSON representation of both trees for programmatic use

This is useful for:
- Saving website structure analysis for later reference
- Comparing website structures over time
- Including tree structures in reports or documentation
- Processing the data programmatically using the JSON output

## API Server

The Link Fetcher tool now includes an API server that allows you to query website structures and find relevant links programmatically. This can be used to build search interfaces, chatbots, or other applications that need to navigate website structures.

### Running the API Server

```bash
# Run the server with default settings (http://127.0.0.1:8000)
python src/link_fetcher/run_server.py

# Run on a different host and port
python src/link_fetcher/run_server.py --host 0.0.0.0 --port 9000

# Enable auto-reload for development
python src/link_fetcher/run_server.py --reload
```

Once the server is running, you can access the interactive API documentation at `http://127.0.0.1:8000/docs`.

### API Endpoints

The API provides the following endpoints:

1. **Analyze a Website**: `POST /analyze`
   - Fetches and analyzes links from a website
   - Generates tree structures (both conventional and enhanced)
   - Runs in the background for large websites

2. **Get Website Tree**: `GET /tree/{url}`
   - Retrieves the tree structures for a website
   - Automatically generates the tree if it doesn't exist

3. **Search Pages**: `POST /search`
   - Searches for pages relevant to a query within a website's tree structure
   - Prioritizes results from the enhanced (AI-based) tree

4. **List All Links**: `POST /links`
   - Lists all links from a website's tree structure
   - Can choose between conventional and enhanced tree

5. **Check Status**: `GET /status/{url}`
   - Checks if tree data already exists for a website

### Example Usage

Using `curl` to interact with the API:

```bash
# Analyze a website
curl -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d '{"url": "example.com"}'

# Search for pages
curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d '{"url": "example.com", "query": "about"}'

# Get website tree
curl -X GET http://localhost:8000/tree/example.com
```

Using Python with the `requests` library:

```python
import requests

# Base URL of the API
API_URL = "http://localhost:8000"

# Analyze a website
response = requests.post(
    f"{API_URL}/analyze",
    json={"url": "example.com", "force_refresh": False}
)
print(response.json())

# Search for pages
response = requests.post(
    f"{API_URL}/search",
    json={"url": "example.com", "query": "about", "max_results": 5}
)
results = response.json()
for item in results["results"]:
    print(f"URL: {item['url']}, Relevance: {item['relevance']}")
```

### API Integration Ideas

The Link Fetcher API can be integrated with:

1. **Search Interfaces**: Build a frontend that allows users to search website content
2. **Chatbots**: Enable bots to find and reference relevant pages based on user questions
3. **Documentation Tools**: Create tools for exploring and navigating documentation websites
4. **Website Analysis**: Analyze and visualize website structures programmatically 