"""
A MCP server that fetches and caches webpage content.
"""
import os
import json
from pathlib import Path
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP
from link_fetcher.fetcher import validate_url, fetch_webpage, extract_links
from link_fetcher.tree_builder import WebsiteTreeBuilder
from extract import create_fasthtml_doc, get_output_dir
from google import genai

# Create a server instance
mcp = FastMCP("doc-fetcher-mcp")


# Cache directory inside the server folder
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_paths(url: str) -> tuple[Path, Path, Path, Path, Path]:
    """Get the cache file paths for a URL.
    
    Returns:
        tuple: (fasthtml_path, tree_md_path, tree_json_path, links_path, pages_path)
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
    
    Args:
        url: The URL to fetch
        max_pages: Maximum number of pages to include in the merged document
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
        links_text = f"URL: {url}\n\nExtracted Links:\n"
        for link_url, link_text in links:
            links_text += f"- {link_text}: {link_url}\n"
        links_path.write_text(links_text, encoding='utf-8')
        
        # Generate tree structure
        tree_builder = WebsiteTreeBuilder(use_llm=False)
        trees = tree_builder.analyze_links(links, url)
        tree_dict = trees["conventional"].to_dict()
        
        # Save both markdown and JSON versions of the tree
        md_tree = dict_tree_to_markdown(tree_dict)
        tree_md_path.write_text(md_tree, encoding='utf-8')
        tree_json_path.write_text(json.dumps(tree_dict, indent=2), encoding='utf-8')
        
        # Store individual page contents
        pages_content = {}
        for link_url, link_text in links:
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
def fetch_url_tool(url: str, max_pages: int = 30) -> str:
    """Fetch and cache webpage content.
    
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
    """Convert a nested tree (or list of trees) into a markdown bullet list."""
    markdown = ""
    if isinstance(tree, list):
        for node in tree:
            markdown += dict_tree_to_markdown(node, level)
    elif isinstance(tree, dict):
        # If at the root and no tag is provided, assume it's a container and process its children
        if level == 0 and 'tag' not in tree and 'children' in tree:
            markdown += dict_tree_to_markdown(tree.get('children', []), level)
        else:
            indent = '  ' * level
            tag = tree.get('tag') or tree.get('name') or 'No Tag'
            markdown += f"{indent}- {tag}\n"
            markdown += dict_tree_to_markdown(tree.get('children', []), level + 1)
    return markdown

def get_relevant_pages_from_llm(tree: str, query: str) -> list:
    """Use Gemini to identify relevant pages from the site hierarchy based on the query.
    
    Args:
        tree: The site hierarchy tree
        query: The user's query
        
    Returns:
        list: List of relevant page URLs
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
def query_content_tool(url: str, query: str) -> str:
    """Query the cached content for relevant information using LLM.
    
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