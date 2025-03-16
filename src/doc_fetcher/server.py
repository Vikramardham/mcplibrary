"""
A MCP server that fetches and caches webpage content.

This server provides tools for fetching, analyzing, and caching webpage content. It creates
hierarchical representations of websites and enables semantic querying of their content using
the Gemini AI model.

The server maintains a cache directory structure for each domain:
- fasthtml_doc.txt: Raw HTML content
- tree_structure.md: Markdown representation of the site hierarchy
- tree_structure.json: JSON representation of the site hierarchy
- extracted_links.txt: Organized list of extracted links
- pages_content.json: Cached content of individual pages

Environment Variables:
    GEMINI_API_KEY: API key for Google's Gemini AI model
"""
import os
import json
from pathlib import Path
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP
from lib.fetcher import validate_url, fetch_webpage, extract_links
from lib.tree_builder import WebsiteTreeBuilder
from google import genai

# Create a server instance
mcp = FastMCP("doc-fetcher-mcp")


# Cache directory inside the server folder
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_paths(url: str) -> tuple[Path, Path, Path, Path, Path]:
    """Get the cache file paths for a URL.
    
    This function generates standardized paths for caching different aspects of a webpage,
    including its content, structure, and extracted links.
    
    Args:
        url: The URL to generate cache paths for. If it doesn't start with 'http',
             'https://' will be prepended.
    
    Returns:
        tuple: A 5-tuple containing paths for:
            - fasthtml_doc.txt: Raw HTML content
            - tree_structure.md: Markdown representation of site hierarchy
            - tree_structure.json: JSON representation of site hierarchy
            - extracted_links.txt: Organized list of extracted links
            - pages_content.json: Cached content of individual pages
    """
    if not url.startswith("http"):
        url = "https://" + url
    domain = urlparse(url).netloc.replace(".", "_")
    base_path = CACHE_DIR / domain
    base_path.mkdir(exist_ok=True)
    return (
        base_path / "fasthtml_doc.txt",
        base_path / "tree_structure.md",
        base_path / "tree_structure.json",
        base_path / "extracted_links.txt",
        base_path / "pages_content.json"
    )

def fetch_and_cache(url: str, max_pages: int = 30) -> dict:
    """Fetch webpage content and cache it with tree structure.
    
    This function fetches a webpage and its linked pages, analyzes their structure,
    and caches various representations of the content. It handles both initial fetching
    and subsequent cache retrieval.
    
    Args:
        url: The URL to fetch and analyze
        max_pages: Maximum number of pages to include in the merged document
    
    Returns:
        dict: A dictionary containing:
            - tree: JSON representation of the site hierarchy
            - tree_md: Markdown representation of the site hierarchy
            - links: Formatted text of extracted and organized links
            - pages: Dictionary of page contents keyed by URL
            
    Raises:
        Exception: If there's an error fetching or processing the content
    """
    fasthtml_path, tree_md_path, tree_json_path, links_path, pages_path = get_cache_paths(url)
    
    # Return cached content if available
    if all(p.exists() for p in (tree_md_path, tree_json_path, links_path, pages_path)):
        return {
            "tree": json.loads(tree_json_path.read_text(encoding='utf-8')),
            "tree_md": tree_md_path.read_text(encoding='utf-8'),
            "links": links_path.read_text(encoding='utf-8'),
            "pages": json.loads(pages_path.read_text(encoding='utf-8'))
        }
    
    # Fetch and cache content
    try:
        # Fetch webpage content
        content = fetch_webpage(url)
        
        # Extract and process links
        links = extract_links(content, url)
        
        # Organize links by sections
        organized_links = {}
        for link_url, link_text in links:
            # Skip duplicate links and external links
            if link_url.startswith(url) and link_url not in organized_links:
                path = urlparse(link_url).path.strip('/')
                if path:  # Skip the root URL
                    parts = path.split('/')
                    current = organized_links
                    for i, part in enumerate(parts):
                        if i == len(parts) - 1:
                            current[part] = {"url": link_url, "title": link_text}
                        else:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
        
        # Generate links text
        links_text = f"URL: {url}\n\nExtracted Links:\n"
        def format_links(links_dict, level=0):
            result = ""
            indent = "  " * level
            for key, value in sorted(links_dict.items()):
                if isinstance(value, dict):
                    if "url" in value:  # It's a leaf node
                        result += f"{indent}- {value['title']}: {value['url']}\n"
                    else:  # It's a directory
                        result += f"{indent}- {key}/\n"
                        result += format_links(value, level + 1)
            return result
        
        links_text += format_links(organized_links)
        links_path.write_text(links_text, encoding='utf-8')
        
        # Generate tree structure
        tree_builder = WebsiteTreeBuilder(use_llm=False)
        trees = tree_builder.analyze_links(links, url)
        tree_dict = {
            "tag": urlparse(url).netloc,
            "children": []
        }
        
        def build_tree(links_dict):
            children = []
            for key, value in sorted(links_dict.items()):
                if isinstance(value, dict):
                    if "url" in value:  # Leaf node
                        children.append({
                            "tag": value["title"],
                            "url": value["url"]
                        })
                    else:  # Directory node
                        children.append({
                            "tag": key,
                            "children": build_tree(value)
                        })
            return children
        
        tree_dict["children"] = build_tree(organized_links)
        
        # Save both markdown and JSON versions of the tree
        md_tree = dict_tree_to_markdown(tree_dict)
        tree_md_path.write_text(md_tree, encoding='utf-8')
        tree_json_path.write_text(json.dumps(tree_dict, indent=2), encoding='utf-8')
        
        # Store individual page contents
        pages_content = {}
        for link_url, link_text in links:
            if link_url.startswith(url):  # Only cache internal pages
                try:
                    page_content = fetch_webpage(link_url)
                    pages_content[link_url] = {
                        "title": link_text,
                        "content": page_content
                    }
                except Exception as e:
                    print(f"Error fetching {link_url}: {e}")
                    continue
        
        # Save pages content
        pages_path.write_text(json.dumps(pages_content, indent=2), encoding='utf-8')
        
        return {
            "tree": tree_dict,
            "tree_md": md_tree,
            "links": links_text,
            "pages": pages_content
        }
        
    except Exception as e:
        return {
            "error": f"Error fetching content: {str(e)}",
            "tree": {},
            "tree_md": "",
            "links": "",
            "pages": {}
        }

@mcp.tool()
def download_docs_from_url(url: str, max_pages: int = 30) -> str:
    """Download and cache webpage content. This is to be used before querying the docs using the fetch_relevant_docs tool.
    This tool is to be used when the user first mentions a URL about the docs they are looking for.
    
    Args:
        url: The URL to fetch
        max_pages: Maximum number of pages to include in the merged document
    """
    if not validate_url(url):
        return f"Invalid URL: {url}"
    
    result = fetch_and_cache(url, max_pages)
    if "error" in result:
        return result["error"]
    
    return f"""Content fetched and cached:

Link Structure:
-------------
{result['links']}

Tree Structure:
-------------
{result['tree_md']}"""

def dict_tree_to_markdown(tree, level=0):
    """Convert a nested tree (or list of trees) into a markdown bullet list.
    
    This function recursively converts a hierarchical dictionary structure into
    a markdown-formatted bullet list, preserving the hierarchy through indentation.
    
    Args:
        tree: A dictionary or list representing the tree structure. Dictionary nodes
              should have 'tag' and optionally 'url' and 'children' keys.
        level: The current indentation level (default: 0)
    
    Returns:
        str: A markdown-formatted string representing the tree structure
    """
    markdown = ""
    indent = "  " * level
    
    if isinstance(tree, list):
        for node in tree:
            markdown += dict_tree_to_markdown(node, level)
    elif isinstance(tree, dict):
        tag = tree.get('tag')
        if tag:  # Only create entry if there's a tag
            markdown += f"{indent}- {tag}"
            if 'url' in tree:
                markdown += f" ({tree['url']})"
            markdown += "\n"
            
        if 'children' in tree:
            for child in tree['children']:
                markdown += dict_tree_to_markdown(child, level + 1)
                
    return markdown

def get_relevant_pages_from_llm(tree: str, query: str) -> list:
    """Use Gemini to identify relevant pages from the site hierarchy based on the query.
    
    This function uses Google's Gemini AI model to analyze a website's structure and
    identify pages that are most relevant to a given query.
    
    Args:
        tree: The site hierarchy tree in markdown format
        query: The user's search query
        
    Returns:
        list: A list of dictionaries, each containing:
            - url: The URL of a relevant page
            - reason: Explanation of why the page is relevant
            
    Requires:
        GEMINI_API_KEY environment variable to be set
    """
    prompt = f"""Given the following website hierarchy and a user's query, identify which pages are most likely to contain relevant information.
Only return pages that you think are highly relevant to answering the query.

Query: {query}

Website Hierarchy:
{tree}

Return your response in the following JSON format:
{{
    "relevant_pages": [
        {{
            "url": "page_url",
            "reason": "brief explanation of why this page is relevant"
        }}
    ]
}}

Analyze the hierarchy and select pages that are most likely to contain information relevant to the query."""

    try:
        # Create a client and generate content
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        
        # Parse the response
        content = response.text
        # Extract the JSON part from the response
        json_str = content[content.find("{"):content.rfind("}")+1]
        result = json.loads(json_str)
        return result.get("relevant_pages", [])
    except Exception as e:
        print(f"Error in LLM processing: {e}")
        return []

@mcp.tool()
def fetch_relevant_docs(url: str, query: str) -> str:
    """Fetch relevant documents from the cached content using LLM.
    This is to be used after the docs are downloaded using the download_docs_from_url tool.
    
    Args:
        url: The URL whose content to query
        query: The search query to find relevant content
    """
    if not validate_url(url):
        return f"Invalid URL: {url}"
    
    _, tree_md_path, _, links_path, pages_path = get_cache_paths(url)
    print(tree_md_path, pages_path)
    if not all(p.exists() for p in (tree_md_path, pages_path)):
        return "No cached content available. Please fetch the URL first using fetch_url_tool."
    
    try:
        # Load tree and pages content
        tree_md = tree_md_path.read_text(encoding='utf-8')
        pages_content = json.loads(pages_path.read_text(encoding='utf-8'))
        
        # Use LLM to identify relevant pages from the hierarchy
        relevant_pages = get_relevant_pages_from_llm(tree_md, query)
        
        if not relevant_pages:
            return "No relevant pages found for the query."
        
        # Fetch content for the identified pages
        result = "Relevant pages found:\n\n"
        for page_info in relevant_pages:
            page_url = page_info["url"]
            if page_url in pages_content:
                page_data = pages_content[page_url]
                result += f"Page: {page_data['title']} ({page_url})\n"
                result += f"Reason for relevance: {page_info['reason']}\n"
                result += f"Content Preview:\n{page_data['content'][:500]}...\n\n"
            else:
                result += f"Page {page_url} was identified as relevant but content is not cached.\n\n"
        
        return result
        
    except Exception as e:
        return f"Error querying content: {str(e)}"

if __name__ == "__main__":
    # Start the server
    print("Starting Doc Fetcher MCP Server...")
    mcp.run() 