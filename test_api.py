"""
Test script for the Link Fetcher API.
"""

import requests
import json
import sys

# Base URL of the API
API_URL = "http://localhost:8000"


def test_api_root():
    """Test the root endpoint."""
    print("Testing root endpoint...")
    response = requests.get(f"{API_URL}/")
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def check_status(url):
    """Check if tree data exists for a URL."""
    print(f"Checking status for {url}...")
    response = requests.get(f"{API_URL}/status/{url}")
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    return response.json()["exists"]


def analyze_website(url, force_refresh=False):
    """Analyze a website and generate tree structure."""
    print(f"Analyzing website {url}...")
    response = requests.post(
        f"{API_URL}/analyze", json={"url": url, "force_refresh": force_refresh}
    )
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def get_website_tree(url):
    """Get the tree structure for a website."""
    print(f"Getting tree for {url}...")
    response = requests.get(f"{API_URL}/tree/{url}")
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        tree_data = response.json()
        print(f"Conventional tree has {len(tree_data['conventional_tree'])} nodes")
        print(f"Enhanced tree has {len(tree_data['enhanced_tree'])} nodes")
    else:
        print(f"Error: {response.text}")
    print()


def search_pages(url, query):
    """Search for pages relevant to a query."""
    print(f"Searching for '{query}' in {url}...")
    response = requests.post(
        f"{API_URL}/search", json={"url": url, "query": query, "max_results": 5}
    )
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        results = response.json()
        print(f"Found {len(results['results'])} results:")
        for i, item in enumerate(results["results"], 1):
            print(
                f"  {i}. {item['text']} - {item['url']} (Relevance: {item['relevance']})"
            )
    else:
        print(f"Error: {response.text}")
    print()


def list_links(url, tree_type="enhanced"):
    """List all links from a website's tree structure."""
    print(f"Listing all links for {url} (tree type: {tree_type})...")
    response = requests.post(
        f"{API_URL}/links", json={"url": url, "tree_type": tree_type}
    )
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data['links'])} links")
        for i, link in enumerate(data["links"][:5], 1):  # Show top 5 only
            print(f"  {i}. {link['text']} - {link['url']}")
        if len(data["links"]) > 5:
            print(f"  ... and {len(data['links']) - 5} more")
    else:
        print(f"Error: {response.text}")
    print()


def main():
    """Run tests for the Link Fetcher API."""
    url = "example.com"

    if len(sys.argv) > 1:
        url = sys.argv[1]

    print(f"Testing Link Fetcher API with URL: {url}")
    print("=" * 80)

    # Test the root endpoint
    test_api_root()

    # Check if tree data exists
    exists = check_status(url)

    # If tree data doesn't exist, analyze the website
    if not exists:
        analyze_website(url)

    # Get the tree structure
    get_website_tree(url)

    # Search for pages
    search_pages(url, "about")

    # List all links
    list_links(url)


if __name__ == "__main__":
    main()
