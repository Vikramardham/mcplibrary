# Website Tree Crawler

A Python library that crawls documentation websites and builds a tree structure of URLs, titles, and content. This library is designed to help create context for Large Language Models (LLMs) by providing structured access to documentation content.

## Features

- Crawls documentation websites starting from a root URL
- Extracts title and content from each page
- Builds a hierarchical tree structure based on URL paths
- Filters URLs based on patterns to focus on relevant content
- Saves results as JSON for easy integration with other tools

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

### Command Line Interface

You can run the crawler from the command line:

```bash
python src/map.py https://docs.python.org/3/library/ --max-pages 50 --output python_docs.json
```

Or try the example script:

```bash
python src/example.py  # Crawl a site
python src/example.py --load  # Load previously saved results
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
2. LLM-friendly retrieval interface
3. Content chunking strategies
4. Improved content extraction for specific documentation formats

## License

MIT 