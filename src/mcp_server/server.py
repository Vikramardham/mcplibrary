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

# Create a server instance
mcp = FastMCP("doc-fetcher-mcp")

# Cache directory inside the server folder
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_paths(url: str) -> tuple[Path, Path, Path]:
    """Get the cache file paths for a URL.
    
    Returns:
        tuple: (fasthtml_path, tree_path, links_path)
    """
    if not url.startswith("http"):
        url = "https://" + url
    domain = urlparse(url).netloc.replace(".", "_")
    base_path = CACHE_DIR / domain
    base_path.mkdir(exist_ok=True)
    return (
        base_path / "fasthtml_doc.txt",
        base_path / "tree_structure.json",
        base_path / "extracted_links.txt"
    )

def fetch_and_cache(url: str, max_pages: int = 10) -> dict:
    """Fetch webpage content and cache it with tree structure.
    
    Args:
        url: The URL to fetch
        max_pages: Maximum number of pages to include in the merged document
    """
    fasthtml_path, tree_path, links_path = get_cache_paths(url)
    
    # Return cached content if available
    if all(p.exists() for p in (fasthtml_path, tree_path, links_path)):
        return {
            "fasthtml": fasthtml_path.read_text(encoding='utf-8'),
            "tree": json.loads(tree_path.read_text(encoding='utf-8')),
            "links": links_path.read_text(encoding='utf-8')
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
        tree_path.write_text(json.dumps(trees["conventional"].to_dict(), indent=2), encoding='utf-8')
        
        # Create comprehensive FastHTML document using the dedicated function
        # This will fetch content from all linked pages and create a merged document
        output_dir = get_output_dir(url)
        fasthtml_file = create_fasthtml_doc(url, links[:max_pages], output_dir)
        
        # Move the generated fasthtml file to our cache location
        if fasthtml_file.exists():
            fasthtml_content = fasthtml_file.read_text(encoding='utf-8')
            fasthtml_path.write_text(fasthtml_content, encoding='utf-8')
            # Clean up the temporary output directory
            if fasthtml_file.parent.exists():
                import shutil
                shutil.rmtree(fasthtml_file.parent)
        else:
            fasthtml_content = "No content could be extracted"
        
        return {
            "fasthtml": fasthtml_content,
            "tree": trees["conventional"].to_dict(),
            "links": links_text
        }
        
    except Exception as e:
        return {
            "error": f"Error fetching content: {str(e)}",
            "fasthtml": "",
            "tree": {},
            "links": ""
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

FastHTML Document (Merged from up to {max_pages} pages):
--------------------------------------------------
{result['fasthtml']}

Link Structure:
-------------
{result['links']}

Tree Structure:
-------------
{json.dumps(result['tree'], indent=2)}
"""

if __name__ == "__main__":
    # Start the server
    print("Starting Doc Fetcher MCP Server...")
    mcp.run() 