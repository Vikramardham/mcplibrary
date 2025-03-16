# MCP Document Fetcher

A Multi-Context Protocol (MCP) server that fetches, caches, and analyzes webpage content. This tool creates hierarchical representations of websites and enables semantic querying of their content.

## Features

- 🌐 Webpage content fetching and caching
- 📁 Hierarchical site structure generation
- 🔍 Semantic content querying using Gemini AI
- 🌲 Tree-based visualization of website structure
- 🔄 Efficient caching system for repeated queries

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd mcps
```

2. Create and activate a virtual environment using `uv`:
```bash
uv venv
source .venv/Scripts/activate (just `.venv/Scripts/activate on windows)
```

3. Install dependencies:
```bash
uv sync 
```

4. Set up environment variables:
```bash
export GEMINI_API_KEY="your-api-key"  # For Windows, use 'set' instead of 'export'
```

## Usage
1. Copy the contents of ./src/doc_fetcher to your local folder containing mcp servers 
Add the MCP server to your mcp.json (either cursor/windsurf)
```
{
    "mcpServers": {
        "doc-fetcher-mcp": {
            "command": "uv",
            "args": [
                "--directory",
                "<path_to_mcp_server_folder>",
                "run",
                "server.py"
            ]
        }
    }
}
```

2. Use the available MCP tools:
- Test it by chatting with your IDE. E.g: I'd like to build a simple chatbot using langgraph and use memory. Use the docs site: @https://langchain-ai.github.io/langgraph/ to understand the framework (The URL MUST be provided to the LLM. It won't do any guess work for you and this is an intentional choice)

## Project Structure

```
src/
├── mcp_server/
│   ├── server.py      # Main MCP server implementation
│   └── cache/         # Cached webpage content (gitignored)
├── link_fetcher/      # Link extraction and tree building
└── extract/           # HTML content extraction
```

## Cache Management

The server maintains a cache directory (`src/mcp_server/cache/`) that stores:
- Webpage content
- Site structure trees (JSON and Markdown)
- Extracted links
- Page content in JSON format

The cache is gitignored to prevent committing large amounts of data.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[MIT] 