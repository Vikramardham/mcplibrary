# Website Tree Crawler

A Python library that crawls documentation websites and builds a tree structure of URLs, titles, and content. This library is designed to help create context for Large Language Models (LLMs) by providing structured access to documentation content.

## Features

- Crawls documentation websites starting from a root URL
- Extracts title and content from each page
- Builds a hierarchical tree structure based on URL paths
- Creates website-specific output directories for better organization
- Generates up to 3 levels of hierarchy in the LLM tree (categories, subcategories, and sub-subcategories)
- Outputs rich content in CSV format with columns for page, URL, content, and images
- Downloads and saves images separately in a designated sub-folder
- Provides a retriever function that uses LLMs to fetch relevant URLs based on user questions
- Filters URLs based on patterns to focus on relevant content
- Saves results in multiple formats for easy integration with other tools

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from src.map import WebsiteTreeCrawler

# Create a crawler
crawler = WebsiteTreeCrawler(
    root_url="https://docs.python.org/3/library/",
    max_pages=100  # Limit the number of pages to crawl
)

# Start crawling
tree = crawler.crawl()

# Save results
crawler.save_tree("docs_tree.json")
crawler.save_pages("docs_pages.json")
```

### Command Line Interface

You can run the crawler from the command line:

```bash
python -m src.link_fetcher https://docs.python.org/3/library/ --output tree --save-to python_docs
```

This will create the following files in a website-specific output directory:
- `python_docs_conventional.txt`: Tree based on URL structure
- `python_docs_llm.txt`: Tree based on AI categorization
- `python_docs_rich.txt`: Detailed tree views with descriptions
- `python_docs_content.csv`: CSV file with page content and image references
- Images folder with downloaded images

### Using the Retriever Function

You can use the retriever function to find relevant URLs for a specific query:

```bash
python -m src.link_fetcher https://docs.python.org/3/library/ --query "How do I use dictionaries in Python?"
```

Additional options:
- `--include-content`: Include page content in query results
- `--max-results N`: Limit the number of results (default: 5)

### Loading Saved Results

```python
from src.map import load_tree, load_pages

# Load the saved tree and pages
tree = load_tree("docs_tree.json")
pages = load_pages("docs_pages.json")

# Access content
root_url = tree["root"]["url"]
root_title = tree["root"]["title"]
root_children = tree["root"]["children"]

# Access a specific page
page_url = "https://docs.python.org/3/library/functions.html"
if page_url in pages:
    page_title = pages[page_url]["title"]
    page_content = pages[page_url]["content"]
```

## Tree Structure

The generated tree has the following structure:

```json
{
  "root": {
    "url": "https://example.com/docs/",
    "title": "Documentation",
    "children": {
      "section1": {
        "url": "https://example.com/docs/section1/",
        "title": "Section 1",
        "children": {
          "page1": {
            "url": "https://example.com/docs/section1/page1/",
            "title": "Page 1",
            "content": "Content of page 1...",
            "children": {}
          }
        }
      }
    }
  }
}
```

## CSV Content Format

The CSV content file has the following columns:
- Page Title: The title of the webpage
- URL: The full URL of the page
- Content: The main text content of the page
- Images: Comma-separated list of relative paths to downloaded images

## Customization

You can customize the crawler behavior:

```python
crawler = WebsiteTreeCrawler(
    root_url="https://docs.example.com/",
    max_pages=200,
    excluded_patterns=[
        r'.*\.(css|js|png|jpg|jpeg|gif|svg|pdf|zip|tar|gz|ico)$',
        r'.*/tags/.*',
        r'.*/search/.*',
    ],
    included_patterns=[
        r'.*/api/.*',  # Only include URLs containing '/api/'
    ]
)
```

## Future Development

This library is the first step in building a comprehensive solution for LLM context retrieval. Future enhancements will include:

1. Vector embeddings for semantic search
2. Content chunking strategies
3. Improved content extraction for specific documentation formats

## License

MIT 