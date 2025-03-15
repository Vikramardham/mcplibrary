"""
Tree Builder - A module to organize website links into a meaningful tree structure.
"""

import os
import json
from pathlib import Path
from urllib.parse import urlparse
from rich.tree import Tree as RichTree
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from trafilatura import fetch_url, extract, extract_metadata
from dotenv import load_dotenv
from google import genai
from treelib import Tree
from .fetcher import validate_url

# Load environment variables from .env file
load_dotenv()


class WebsiteTreeBuilder:
    """Build and analyze a tree structure from website links."""

    def __init__(self, api_key=None):
        """Initialize the tree builder.

        Args:
            api_key: Optional Google API key for LLM categorization
        """
        self.console = Console()
        self.conventional_tree = None
        self.llm_tree = None
        self.all_links = []

    def analyze_links(self, links, base_url):
        """Analyze and categorize links using both conventional and LLM approaches."""

        # Initialize both trees with root nodes
        self.conventional_tree = Tree()
        self.conventional_tree.create_node(
            "Website Structure", "root", data={"type": "root"}
        )

        self.llm_tree = Tree()
        self.llm_tree.create_node("Enhanced Structure", "root", data={"type": "root"})

        # First, group links by their domain and path
        domains = {}
        for url, text in links:
            parsed = urlparse(url)

            # Skip empty or javascript links
            if not parsed.netloc or parsed.scheme == "javascript":
                continue

            # Create domain key if it doesn't exist
            domain_key = parsed.netloc
            if domain_key not in domains:
                domains[domain_key] = []

            # Add link to its domain group
            path = parsed.path if parsed.path else "/"
            domains[domain_key].append(
                {"url": url, "text": text, "path": path, "categories": []}
            )

        # Generate the conventional tree first
        self.console.print(
            "[bold]Building conventional tree based on URL structure...[/bold]"
        )
        self._categorize_by_structure(domains, base_url, self.conventional_tree)

        # Then generate the LLM-enhanced tree
        self.console.print(
            "[bold]Building enhanced tree using Google Generative AI...[/bold]"
        )
        self._categorize_with_llm(domains, base_url, self.llm_tree)

        # Return both trees
        return {"conventional": self.conventional_tree, "llm": self.llm_tree}

    def _categorize_with_llm(self, domains, base_url, tree):
        """Categorize links using Google's Generative AI."""
        self.console.print(
            "[bold]Categorizing links using Google Generative AI...[/bold]"
        )

        # Extract the base domain
        base_domain = urlparse(base_url).netloc

        # Process links from the base domain first
        if base_domain in domains:
            base_links = domains[base_domain]

            # Check if there are any links to process
            if not base_links:
                self.console.print(
                    "[yellow]No base domain links to categorize with LLM.[/yellow]"
                )
                # Fallback to structure-based categorization
                return self._categorize_by_structure(domains, base_url, tree)

            # Prepare data for the LLM
            link_data = []
            for link in base_links:
                link_data.append(
                    {"url": link["url"], "text": link["text"], "path": link["path"]}
                )

            # Format the prompt - simplified to improve reliability
            prompt = """
            Analyze and categorize these links from %s into a logical tree structure with up to 3 levels of hierarchy.
            
            Links to categorize: %s
            
            Return a JSON object with this structure:
            {
                "categories": [
                    {
                        "name": "Category Name",
                        "description": "Short description",
                        "links": [
                            {
                                "url": "full_url_here",
                                "text": "link_text_here",
                                "importance": 1-5 (where 5 is most important)
                            }
                        ],
                        "subcategories": [
                            {
                                "name": "Subcategory Name",
                                "description": "Short description",
                                "links": [
                                    {
                                        "url": "full_url_here",
                                        "text": "link_text_here",
                                        "importance": 1-5
                                    }
                                ],
                                "subcategories": [
                                    {
                                        "name": "Sub-subcategory Name",
                                        "description": "Short description",
                                        "links": [
                                            {
                                                "url": "full_url_here",
                                                "text": "link_text_here",
                                                "importance": 1-5
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            Guidelines:
            1. Group similar links together
            2. Use meaningful category names
            3. Include ALL links in your categorization
            4. Create up to 3 levels of hierarchy (categories, subcategories, sub-subcategories)
            5. Output ONLY valid JSON, no explanations or markdown
            """ % (
                base_url,
                json.dumps(link_data, indent=2),
            )

            try:
                # Using the correct client approach to generate content
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )

                content = response.text

                # Log the received content for debugging
                self.console.print("[dim]Received response from LLM...[/dim]")

                # Clean up the response to extract valid JSON
                try:
                    # Extract JSON from the response
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()

                    # Remove any non-JSON text before or after the actual JSON content
                    content = content.strip()
                    if content.startswith("{"):
                        # Find the closing bracket of the root object
                        bracket_count = 0
                        for i, char in enumerate(content):
                            if char == "{":
                                bracket_count += 1
                            elif char == "}":
                                bracket_count -= 1
                                if bracket_count == 0:
                                    content = content[: i + 1]
                                    break

                    categorized_data = json.loads(content)

                    # If we got this far, we have valid JSON
                    self.console.print(
                        "[green]Successfully parsed LLM response.[/green]"
                    )

                except json.JSONDecodeError as json_error:
                    self.console.print(
                        f"[yellow]JSON parsing error: {json_error}. Trying fallback parsing...[/yellow]"
                    )

                    # Try to find and extract just the JSON part
                    import re

                    json_match = re.search(
                        r'(\{.*"categories"\s*:\s*\[.*?\]\s*\})', content, re.DOTALL
                    )
                    if json_match:
                        try:
                            content = json_match.group(1)
                            categorized_data = json.loads(content)
                            self.console.print(
                                "[green]Successfully parsed JSON with fallback method.[/green]"
                            )
                        except json.JSONDecodeError:
                            raise ValueError("Failed to parse LLM response as JSON")
                    else:
                        raise ValueError(
                            "Could not extract valid JSON from LLM response"
                        )

                # Check if we have categories in the response
                if (
                    "categories" not in categorized_data
                    or not categorized_data["categories"]
                ):
                    self.console.print(
                        "[yellow]No categories found in LLM response. Using fallback categorization.[/yellow]"
                    )
                    return self._categorize_by_structure(domains, base_url, tree)

                # Update the domains structure with the categorization
                for category in categorized_data.get("categories", []):
                    category_name = category.get("name", "Uncategorized")
                    category_id = f"category_{category_name.lower().replace(' ', '_').replace('-', '_')}"

                    # Add category to tree
                    tree.create_node(
                        category_name,
                        category_id,
                        parent="root",
                        data={
                            "description": category.get("description", ""),
                            "type": "category",
                        },
                    )

                    # Add links to the category
                    for i, link in enumerate(category.get("links", [])):
                        link_url = link.get("url")
                        link_text = link.get("text")
                        link_importance = link.get("importance", 3)

                        if link_url:
                            link_id = f"{category_id}_link_{i}"
                            tree.create_node(
                                link_text,
                                link_id,
                                parent=category_id,
                                data={
                                    "url": link_url,
                                    "importance": link_importance,
                                    "type": "link",
                                },
                            )

                    # Handle subcategories
                    for j, subcat in enumerate(category.get("subcategories", [])):
                        subcat_name = subcat.get("name", f"Subcategory {j+1}")
                        subcat_id = f"{category_id}_subcat_{j}"

                        # Add subcategory to tree
                        tree.create_node(
                            subcat_name,
                            subcat_id,
                            parent=category_id,
                            data={
                                "description": subcat.get("description", ""),
                                "type": "category",
                            },
                        )

                        # Add links to the subcategory
                        for k, sublink in enumerate(subcat.get("links", [])):
                            sublink_url = sublink.get("url")
                            sublink_text = sublink.get("text")
                            sublink_importance = sublink.get("importance", 3)

                            if sublink_url:
                                sublink_id = f"{subcat_id}_link_{k}"
                                tree.create_node(
                                    sublink_text,
                                    sublink_id,
                                    parent=subcat_id,
                                    data={
                                        "url": sublink_url,
                                        "importance": sublink_importance,
                                        "type": "link",
                                    },
                                )

                        # Handle sub-subcategories (third level)
                        for idx, subsubcat in enumerate(
                            subcat.get("subcategories", [])
                        ):
                            subsubcat_name = subsubcat.get(
                                "name", f"Sub-subcategory {idx+1}"
                            )
                            subsubcat_id = f"{subcat_id}_subcat_{idx}"

                            # Add sub-subcategory to tree
                            tree.create_node(
                                subsubcat_name,
                                subsubcat_id,
                                parent=subcat_id,
                                data={
                                    "description": subsubcat.get("description", ""),
                                    "type": "category",
                                },
                            )

                            # Add links to the sub-subcategory
                            for m, subsublink in enumerate(subsubcat.get("links", [])):
                                subsublink_url = subsublink.get("url")
                                subsublink_text = subsublink.get("text")
                                subsublink_importance = subsublink.get("importance", 3)

                                if subsublink_url:
                                    subsublink_id = f"{subsubcat_id}_link_{m}"
                                    tree.create_node(
                                        subsublink_text,
                                        subsublink_id,
                                        parent=subsubcat_id,
                                        data={
                                            "url": subsublink_url,
                                            "importance": subsublink_importance,
                                            "type": "link",
                                        },
                                    )
            except Exception as e:
                self.console.print(
                    f"[bold red]Error using Generative AI: {str(e)}[/bold red]"
                )
                # Fallback to structure-based categorization for the LLM tree as well
                self._categorize_by_structure(domains, base_url, tree)
        else:
            # No links for the base domain
            self.console.print(
                f"[yellow]No links found for base domain: {base_domain}[/yellow]"
            )
            # Fallback to structure-based categorization
            self._categorize_by_structure(domains, base_url, tree)

        return tree

    def _categorize_by_structure(self, domains, base_url, tree):
        """Categorize links based on URL structure without LLM assistance."""
        self.console.print("[bold]Categorizing links by URL structure...[/bold]")

        # Extract the base domain
        base_domain = urlparse(base_url).netloc

        # Add main site category
        main_site_id = "category_main_site"
        tree.create_node(
            f"Main Site ({base_domain})",
            main_site_id,
            parent="root",
            data={"type": "category"},
        )

        # Group links by their first path segment
        path_groups = {}

        if base_domain in domains:
            for link in domains[base_domain]:
                path = link["path"].strip("/")
                segments = path.split("/")

                # The first path segment is the primary category
                primary = segments[0] if segments and segments[0] else "home"

                if primary not in path_groups:
                    path_groups[primary] = []

                path_groups[primary].append(link)

        # Create nodes for each path group
        for path, links in path_groups.items():
            path_name = path.capitalize().replace("-", " ").replace("_", " ")
            if not path or path == "home" or path == "/":
                path_name = "Homepage"

            path_id = f"path_{path}" if path else "path_home"

            # Add path category to tree
            tree.create_node(
                path_name, path_id, parent=main_site_id, data={"type": "path_category"}
            )

            # Add links for this path
            for i, link in enumerate(links):
                link_id = f"{path_id}_link_{i}"
                link_text = (
                    link["text"]
                    if link["text"] and link["text"] != "[No text]"
                    else link["url"]
                )
                tree.create_node(
                    link_text,
                    link_id,
                    parent=path_id,
                    data={"url": link["url"], "type": "link"},
                )

        # Since we've filtered external links at the extraction stage, we no longer need this section
        # External links section was removed

        return tree

    def display_tree(self):
        """Display both conventional and LLM-enhanced tree structures."""

        def convert_to_rich_tree(tree, title):
            """Convert a treelib Tree to a rich Tree for display."""
            rich_tree = RichTree(title)

            def add_node_to_rich_tree(node, parent_rich_node):
                node_data = node.data or {}
                node_type = node_data.get("type", "unknown")

                if node_type == "category":
                    text = f"📁 {node.tag}"
                    if node_data.get("description"):
                        text += f" - {node_data['description']}"
                    new_node = parent_rich_node.add(text)
                elif node_type == "link":
                    text = f"🔗 {node.tag}"
                    if "url" in node_data:
                        text += f"\n   {node_data['url']}"
                    new_node = parent_rich_node.add(text)
                else:
                    new_node = parent_rich_node.add(node.tag)

                # Add children recursively
                for child in tree.children(node.identifier):
                    add_node_to_rich_tree(child, new_node)

                return new_node

            # Start from root's children to skip the root node itself
            root = tree.get_node(tree.root)
            for child in tree.children(root.identifier):
                add_node_to_rich_tree(child, rich_tree)

            return rich_tree

        # Display conventional tree
        self.console.print(
            "\n[bold blue on white]==================== CONVENTIONAL TREE (URL-BASED) ====================[/bold blue on white]"
        )
        self.console.print(
            "[dim]This tree organizes links based on their URL structure and paths.[/dim]"
        )
        conv_rich_tree = convert_to_rich_tree(
            self.conventional_tree, "Website Structure"
        )
        self.console.print(conv_rich_tree)

        # Display LLM tree
        self.console.print(
            "\n[bold green on white]==================== ENHANCED TREE (AI-BASED) ====================[/bold green on white]"
        )
        self.console.print(
            "[dim]This tree uses AI to organize links based on their meaning and purpose.[/dim]"
        )
        llm_rich_tree = convert_to_rich_tree(self.llm_tree, "Enhanced Structure")
        self.console.print(llm_rich_tree)

        # Display rich versions with more details
        self.console.print(
            "\n[bold yellow]=== DETAILED TREE VIEWS (WITH DESCRIPTIONS AND FORMATTING) ===[/bold yellow]"
        )

        self._display_rich_tree(
            self.conventional_tree, "Conventional Website Structure (URL-based)"
        )
        self._display_rich_tree(self.llm_tree, "Enhanced Website Structure (AI-based)")

    def _display_rich_tree(self, tree, title):
        """Display a more detailed tree with rich formatting."""
        console = Console()

        # Create a more prominent title with explanation
        is_ai_tree = "AI" in title or "Enhanced" in title
        border_style = "green" if is_ai_tree else "blue"
        title_style = "bold white on " + border_style

        explanation = ""
        if "Conventional" in title:
            explanation = (
                "Links are grouped by their URL structure (directories and paths)"
            )
        elif "Enhanced" in title or "AI" in title:
            explanation = "Links are organized by their purpose and content (using AI categorization)"

        console.print(
            Panel.fit(
                f"[{title_style}]{title}[/{title_style}]\n[italic]{explanation}[/italic]",
                border_style=border_style,
                padding=(1, 2),
            )
        )

        # Create a function to format a node based on its data
        def format_node(node, indent=0):
            indentation = "  " * indent
            node_data = node.data or {}
            node_type = node_data.get("type", "unknown")

            if node_type == "category":
                text = Text(f"{indentation}📁 {node.tag}")
                text.stylize("bold magenta")
                console.print(text)

                # Print description if available
                if node_data.get("description"):
                    desc_text = Text(f"{indentation}   {node_data['description']}")
                    desc_text.stylize("italic")
                    console.print(desc_text)

            elif node_type == "path_category":
                text = Text(f"{indentation}📂 {node.tag}")
                text.stylize("bold cyan")
                console.print(text)

            elif node_type == "domain":
                text = Text(f"{indentation}🌐 {node.tag}")
                text.stylize("bold green")
                console.print(text)

            elif node_type == "link":
                # Determine importance if available
                importance = node_data.get("importance", 3)
                importance_marker = ""

                if importance >= 4:
                    importance_marker = "⭐ "

                url = node_data.get("url", "")
                text = Text(f"{indentation}🔗 {importance_marker}{node.tag}")
                text.stylize("blue")
                console.print(text)

                # Print URL
                url_text = Text(f"{indentation}   {url}")
                url_text.stylize("dim")
                console.print(url_text)

            else:
                # Root or other node type
                if node.identifier == "root":
                    text = Text(f"{indentation}🌍 {node.tag}")
                    text.stylize("bold yellow")
                    console.print(text)
                else:
                    console.print(f"{indentation}• {node.tag}")

        # Traverse the tree and format each node
        def traverse_tree(node_id, indent=0):
            node = tree.get_node(node_id)
            format_node(node, indent)

            for child_id in tree.is_branch(node_id):
                traverse_tree(child_id, indent + 1)

        # Display the tree starting from root
        traverse_tree("root", 0)

    def save_to_files(self, base_filename, base_url=None):
        """Save both tree structures to files.

        Args:
            base_filename: The base filename to use for output files.
                           Will append _conventional.txt, _llm.txt, etc.
            base_url: The base URL of the website being crawled.
                      Used to create a website-specific directory.
        """
        from rich.console import Console
        import os
        from urllib.parse import urlparse
        import csv
        import hashlib
        import sys
        import io

        # Create website-specific output directory
        if base_url:
            # Extract domain from base_url to use as directory name
            domain = urlparse(base_url).netloc.replace(".", "_")
            # Create output directory path
            output_dir = os.path.join("output", domain)
        else:
            # Use the directory from base_filename if base_url is not provided
            output_dir = os.path.dirname(base_filename)
            if not output_dir:
                output_dir = "output"

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Create images directory
        images_dir = os.path.join(output_dir, "images")
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)

        # Update base_filename to include the website-specific directory
        if base_url:
            base_name = os.path.basename(base_filename)
            base_filename = os.path.join(output_dir, base_name)

        # Save conventional tree - standard format
        conv_file = f"{base_filename}_conventional.txt"
        with open(conv_file, "w", encoding="utf-8") as f:
            # Create a file console that writes to the file
            file_console = Console(file=f, width=120)

            file_console.print(
                "\n==================== CONVENTIONAL TREE (URL-BASED) ===================="
            )
            file_console.print(
                "This tree organizes links based on their URL structure and paths."
            )

            # Capture tree output as string using a custom function
            # We can't directly use file parameter with the Tree.show() method
            # Use stdout redirection to capture the tree output
            original_stdout = sys.stdout
            string_io = io.StringIO()
            sys.stdout = string_io

            # Show the tree to the string buffer
            self.conventional_tree.show(key=lambda node: node.identifier)

            # Restore stdout and get the captured output
            sys.stdout = original_stdout
            tree_output = string_io.getvalue()

            # Write the captured output to the file
            file_console.print(tree_output)

        # Save LLM tree - standard format
        llm_file = f"{base_filename}_llm.txt"
        with open(llm_file, "w", encoding="utf-8") as f:
            # Create a file console that writes to the file
            file_console = Console(file=f, width=120)

            file_console.print(
                "\n==================== ENHANCED TREE (AI-BASED) ===================="
            )
            file_console.print(
                "This tree uses AI to organize links based on their meaning and purpose."
            )

            # Capture tree output as string
            original_stdout = sys.stdout
            string_io = io.StringIO()
            sys.stdout = string_io

            # Show the tree to the string buffer
            self.llm_tree.show(key=lambda node: node.identifier)

            # Restore stdout and get the captured output
            sys.stdout = original_stdout
            tree_output = string_io.getvalue()

            # Write the captured output to the file
            file_console.print(tree_output)

        # Save rich formatted trees
        rich_file = f"{base_filename}_rich.txt"
        with open(rich_file, "w", encoding="utf-8") as f:
            file_console = Console(file=f, width=120)

            file_console.print(
                "\n=== DETAILED TREE VIEWS (WITH DESCRIPTIONS AND FORMATTING) ==="
            )

            # Save conventional rich tree
            title = "Conventional Website Structure (URL-based)"
            explanation = (
                "Links are grouped by their URL structure (directories and paths)"
            )

            file_console.print(f"\n{title}")
            file_console.print(f"{explanation}\n")

            # Capture tree nodes
            self._save_rich_tree_to_file(self.conventional_tree, file_console)

            # Save LLM rich tree
            title = "Enhanced Website Structure (AI-based)"
            explanation = "Links are organized by their purpose and content (using AI categorization)"

            file_console.print(f"\n{title}")
            file_console.print(f"{explanation}\n")

            # Capture tree nodes
            self._save_rich_tree_to_file(self.llm_tree, file_console)

        # Save CSV with rich content
        self.console.print("[bold]Fetching page content and images...[/bold]")
        csv_file = f"{base_filename}_content.csv"

        # Collect all unique URLs from both trees
        all_urls = set()

        def collect_urls_from_tree(tree, node_id="root"):
            node = tree.get_node(node_id)
            if node.data and node.data.get("type") == "link" and "url" in node.data:
                all_urls.add(node.data["url"])

            for child_id in tree.is_branch(node_id):
                collect_urls_from_tree(tree, child_id)

        # Collect URLs from both trees
        collect_urls_from_tree(self.conventional_tree)
        collect_urls_from_tree(self.llm_tree)

        # Write CSV header
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv_writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(["Page Title", "URL", "Content"])

            # Process each URL
            for url in all_urls:
                self.console.print(f"Processing: {url}")

                # Fetch page content using trafilatura
                downloaded = fetch_url(url)
                if downloaded:
                    content = extract(
                        downloaded, output_format="markdown", include_images=True
                    )
                    metadata = extract_metadata(downloaded)
                    title = metadata.title if metadata else url

                    # Write page data to CSV
                    csv_writer.writerow(
                        [
                            title,
                            url,
                            content[:1000] if content else "",  # Limit content length
                        ]
                    )

        self.console.print("[bold green]Output saved to:[/bold green]")
        self.console.print("- Conventional tree: [blue]%s[/blue]" % conv_file)
        self.console.print("- Enhanced tree: [blue]%s[/blue]" % llm_file)
        self.console.print("- Rich formatted trees: [blue]%s[/blue]" % rich_file)
        self.console.print("- CSV content: [blue]%s[/blue]" % csv_file)

    def _save_rich_tree_to_file(self, tree, file_console):
        """Save a rich tree to a file using the provided console."""

        # Define a recursive function to traverse the tree
        def traverse_tree_for_file(node_id, level):
            node = tree.get_node(node_id)
            indent = "  " * level

            # Skip the root node in the output
            if node_id != "root":
                # Format based on node type
                if node.data and node.data.get("type") == "category":
                    # Category node
                    file_console.print(f"{indent}[bold]{node.tag}[/bold]")
                elif node.data and node.data.get("type") == "link":
                    # Link node - show URL and description
                    url = node.data.get("url", "")
                    description = node.data.get("description", "")

                    if description:
                        file_console.print(
                            f"{indent}[blue]{node.tag}[/blue]: {description}"
                        )
                    else:
                        file_console.print(f"{indent}[blue]{node.tag}[/blue]")

                    file_console.print(f"{indent}  [dim]{url}[/dim]")
                else:
                    # Generic node
                    file_console.print(f"{indent}{node.tag}")

            # Process children
            for child_id in tree.is_branch(node_id):
                traverse_tree_for_file(child_id, level + 1)

        # Display the tree starting from root
        traverse_tree_for_file("root", 0)

    def retrieve_relevant_urls(self, query, include_content=False, max_results=5):
        """Retrieve URLs relevant to a specific query using LLM.

        Args:
            query: The search query
            include_content: Whether to include page content in the results
            max_results: Maximum number of results to return
        """
        try:
            # Prepare the data for querying
            urls_with_content = []
            for url, text in self.all_links:
                if include_content:
                    try:
                        page_data = self._fetch_page_content(url)
                        urls_with_content.append(
                            {
                                "url": url,
                                "text": text,
                                "title": page_data["title"],
                                "content": page_data["content"],
                            }
                        )
                    except Exception as e:
                        self.console.print(
                            f"[yellow]Warning: Could not fetch content from {url}: {e}[/yellow]"
                        )
                        continue
                else:
                    urls_with_content.append({"url": url, "text": text})

            # Create a prompt for the LLM
            prompt = f"""Given the following URLs and their descriptions, identify the {max_results} most relevant ones for answering this query: "{query}"

URLs:
{json.dumps(urls_with_content, indent=2)}

Respond with ONLY a JSON array of objects containing 'url' and 'relevance_score' (0-100). Sort by relevance_score in descending order. Include only the top {max_results} most relevant URLs."""

            # Get model response
            client = genai.Client()
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

            # Parse the response
            try:
                results = json.loads(response.text)
                if not isinstance(results, list):
                    raise ValueError("Response is not a list")
            except json.JSONDecodeError:
                raise ValueError("Could not parse LLM response as JSON")

            # Sort by relevance score and limit to max_results
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            results = results[:max_results]

            # Create a tree with the results
            result_tree = Tree()
            result_tree.create_node("Search Results", "root", data={"type": "root"})

            for i, result in enumerate(results):
                url = result["url"]
                score = result.get("relevance_score", 0)

                # Find the link text for this URL
                link_text = next(
                    (text for u, text in self.all_links if u == url),
                    "No description",
                )

                # Create a node for this result
                result_id = f"result_{i}"
                result_tree.create_node(
                    link_text,
                    result_id,
                    parent="root",
                    data={
                        "type": "link",
                        "url": url,
                        "score": score,
                    },
                )

            # Store the tree
            self.llm_tree = result_tree

            # Display the results using rich tree
            rich_tree = RichTree("[bold]Search Results[/bold]")
            for node in result_tree.children(result_tree.root):
                node_data = node.data
                score = node_data.get("score", 0)
                url = node_data.get("url", "")
                result_node = rich_tree.add(
                    f"[bold]{node.tag}[/bold] [dim](Score: {score})[/dim]"
                )
                result_node.add(f"[link={url}]{url}[/link]")

            self.console.print(rich_tree)

        except Exception as e:
            self.console.print(f"[red]Error retrieving relevant URLs: {e}[/red]")
            return []

    def _fetch_page_content(self, url):
        """Fetch and extract content from a webpage using trafilatura.

        Args:
            url: URL to fetch content from

        Returns:
            dict: Dictionary containing page title, content, and images
        """
        try:
            downloaded = fetch_url(url)
            result = extract(
                downloaded,
                include_comments=True,
                include_tables=True,
                include_links=True,
                include_images=True,
                include_formatting=True,
                output_format="markdown",
                with_metadata=True,
                url=url,
            )

            if not result:
                raise Exception("Failed to extract content")

            # Parse the metadata from the result
            lines = result.split("\n")
            metadata = {}
            content_start = 0

            # Look for metadata section
            if lines[0].startswith("---"):
                for i, line in enumerate(lines[1:], 1):
                    if line.startswith("---"):
                        content_start = i + 1
                        break
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()

            # Extract content after metadata
            content = "\n".join(lines[content_start:])

            return {
                "title": metadata.get("title", "Untitled"),
                "content": content,
                "images": [],  # Images are already included in the markdown content
            }

        except Exception as e:
            raise Exception(f"Error fetching content from {url}: {e}")
