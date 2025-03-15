"""
Content Fetcher Module

This module helps retrieve links from tree structures without fetching actual content yet.
It serves as a bridge between the server API and the tree data.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path


class LinkFetcher:
    """
    Class to fetch links from tree structures.
    """

    def __init__(self, output_dir: str = "./output"):
        """
        Initialize the link fetcher with the output directory.

        Args:
            output_dir: Directory containing tree data files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def get_tree_path(self, domain: str) -> Path:
        """
        Get the path to the tree JSON file for a domain.

        Args:
            domain: Domain name (e.g., example.com)

        Returns:
            Path to the tree JSON file
        """
        base_name = domain.replace(".", "_")
        return self.output_dir / f"{base_name}_trees.json"

    def tree_exists(self, domain: str) -> bool:
        """
        Check if a tree JSON file exists for a domain.

        Args:
            domain: Domain name

        Returns:
            True if tree exists, False otherwise
        """
        tree_path = self.get_tree_path(domain)
        return tree_path.exists()

    def load_tree(self, domain: str) -> Dict[str, Any]:
        """
        Load tree data for a domain.

        Args:
            domain: Domain name

        Returns:
            Dictionary containing tree data

        Raises:
            FileNotFoundError: If tree file doesn't exist
        """
        tree_path = self.get_tree_path(domain)
        if not tree_path.exists():
            raise FileNotFoundError(f"Tree data not found for {domain}")

        with open(tree_path, "r") as f:
            return json.load(f)

    def find_links_by_query(
        self, domain: str, query: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find links that match a query in the tree data.

        Args:
            domain: Domain name
            query: Search query (keywords)
            max_results: Maximum number of results to return

        Returns:
            List of dictionaries containing link data

        Raises:
            FileNotFoundError: If tree file doesn't exist
        """
        if not self.tree_exists(domain):
            raise FileNotFoundError(f"Tree data not found for {domain}")

        tree_data = self.load_tree(domain)
        results = []

        # First search in the enhanced (LLM) tree as it's more meaningful
        if "enhanced_tree" in tree_data and tree_data["enhanced_tree"]:
            for node_id, node_data in tree_data["enhanced_tree"].items():
                # Skip nodes that are not dictionaries
                if not isinstance(node_data, dict):
                    continue

                if node_data.get("type") == "link":
                    node_text = node_data.get("name", "").lower()
                    # Handle different data structures
                    data = node_data.get("data", {})
                    url = ""
                    if isinstance(data, dict):
                        url = data.get("url", "")

                    # Simple text matching for now
                    if query.lower() in node_text:
                        results.append(
                            {
                                "url": url,
                                "text": node_data.get("name", ""),
                                "description": node_data.get("description", ""),
                                "relevance": (
                                    "high" if query.lower() in node_text else "medium"
                                ),
                                "tree_type": "enhanced",
                            }
                        )

        # If we need more results, search in the conventional tree as well
        if (
            len(results) < max_results
            and "conventional_tree" in tree_data
            and tree_data["conventional_tree"]
        ):
            for node_id, node_data in tree_data["conventional_tree"].items():
                # Skip nodes that are not dictionaries
                if not isinstance(node_data, dict):
                    continue

                if node_data.get("type") == "link":
                    # Handle different data structures
                    data = node_data.get("data", {})
                    url = ""
                    if isinstance(data, dict):
                        url = data.get("url", "")

                    # Skip if URL is already in results
                    if any(r["url"] == url for r in results):
                        continue

                    node_text = node_data.get("name", "").lower()
                    if query.lower() in node_text:
                        results.append(
                            {
                                "url": url,
                                "text": node_data.get("name", ""),
                                "description": "",  # No description in conventional tree
                                "relevance": "medium",
                                "tree_type": "conventional",
                            }
                        )

        return results[:max_results]

    def list_all_links(
        self, domain: str, tree_type: str = "enhanced"
    ) -> List[Dict[str, Any]]:
        """
        List all links in a tree.

        Args:
            domain: Domain name
            tree_type: Type of tree to use ("enhanced" or "conventional")

        Returns:
            List of dictionaries containing link data

        Raises:
            FileNotFoundError: If tree file doesn't exist
        """
        if not self.tree_exists(domain):
            raise FileNotFoundError(f"Tree data not found for {domain}")

        tree_data = self.load_tree(domain)
        links = []

        tree_key = f"{tree_type}_tree"
        if tree_key not in tree_data:
            raise ValueError(f"Tree type '{tree_type}' not found")

        tree = tree_data[tree_key]
        if not tree:
            return links

        for node_id, node_data in tree.items():
            # Skip nodes that are not dictionaries
            if not isinstance(node_data, dict):
                continue

            if node_data.get("type") == "link":
                # Handle different data structures
                data = node_data.get("data", {})
                url = ""
                if isinstance(data, dict):
                    url = data.get("url", "")

                links.append(
                    {
                        "url": url,
                        "text": node_data.get("name", ""),
                        "description": node_data.get("description", ""),
                        "tree_type": tree_type,
                    }
                )

        return links
