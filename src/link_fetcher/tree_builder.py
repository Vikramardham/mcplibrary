"""
Tree Builder - A module to organize website links into a meaningful tree structure.
"""

import json
import os
from urllib.parse import urlparse
from treelib import Tree
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Import dotenv for loading environment variables from .env file (required)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import Google Generative AI SDK (required)
from google import genai


class WebsiteTreeBuilder:
    """Builds a tree structure of website links using LLM categorization."""

    def __init__(self, api_key=None):
        """Initialize the tree builder with optional API key for Google Generative AI."""
        self.conventional_tree = Tree()
        self.llm_tree = Tree()
        self.console = Console()

        # Create root nodes for both trees
        self.conventional_tree.create_node("Root", "root")
        self.llm_tree.create_node("Root", "root")

        # Initialize Google Generative AI client
        self.genai_client = None

        # Priority for API key:
        # 1. Explicitly provided api_key parameter
        # 2. GEMINI_API_KEY from .env file or environment
        # 3. GOOGLE_API_KEY from environment
        if api_key:
            self.genai_client = genai.Client(api_key=api_key)
            self.console.print("[green]Using provided API key.[/green]")
        elif os.environ.get("GEMINI_API_KEY"):
            self.genai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            self.console.print("[green]Using GEMINI_API_KEY from environment.[/green]")
        elif os.environ.get("GOOGLE_API_KEY"):
            self.genai_client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
            self.console.print("[green]Using GOOGLE_API_KEY from environment.[/green]")
        else:
            self.console.print(
                "[bold red]Error: No API key found. Please add GEMINI_API_KEY to your .env file.[/bold red]"
            )
            raise ValueError("Missing API key - add GEMINI_API_KEY to your .env file")

    def analyze_links(self, links, base_url):
        """Analyze and categorize links using both conventional and LLM approaches."""

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
            prompt = f"""
            Analyze and categorize these links from {base_url} into a logical tree structure.
            
            Links to categorize: {json.dumps(link_data, indent=2)}
            
            Return a JSON object with this structure:
            {{
                "categories": [
                    {{
                        "name": "Category Name",
                        "description": "Short description",
                        "links": [
                            {{
                                "url": "full_url_here",
                                "text": "link_text_here",
                                "importance": 1-5 (where 5 is most important)
                            }}
                        ],
                        "subcategories": []
                    }}
                ]
            }}
            
            Guidelines:
            1. Group similar links together
            2. Use meaningful category names
            3. Include ALL links in your categorization
            4. Output ONLY valid JSON, no explanations or markdown
            """

            try:
                # Using the new client approach to generate content
                response = self.genai_client.models.generate_content(
                    model="gemini-1.5-pro",
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
        # Display conventional tree
        self.console.print(
            "\n[bold blue on white]==================== CONVENTIONAL TREE (URL-BASED) ====================[/bold blue on white]"
        )
        self.console.print(
            "[dim]This tree organizes links based on their URL structure and paths.[/dim]"
        )
        self.conventional_tree.show(key=lambda node: node.identifier)

        # Display LLM tree
        self.console.print(
            "\n[bold green on white]==================== ENHANCED TREE (AI-BASED) ====================[/bold green on white]"
        )
        self.console.print(
            "[dim]This tree uses AI to organize links based on their meaning and purpose.[/dim]"
        )
        self.llm_tree.show(key=lambda node: node.identifier)

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

    def get_tree_json(self):
        """Convert both trees to JSON structures."""

        def node_to_dict(tree, node_id):
            node = tree.get_node(node_id)
            result = {"name": node.tag, "data": node.data, "children": []}

            for child_id in tree.is_branch(node_id):
                result["children"].append(node_to_dict(tree, child_id))

            return result

        # Return both trees as JSON
        return {
            "conventional": node_to_dict(self.conventional_tree, "root"),
            "llm": node_to_dict(self.llm_tree, "root"),
        }

    def save_to_files(self, base_filename):
        """Save both tree structures to files.

        Args:
            base_filename: The base filename to use for output files.
                           Will append _conventional.txt, _llm.txt, etc.
        """
        from rich.console import Console
        from rich.text import Text
        import os

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(base_filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

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
            import sys
            import io

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
                "\n=== DETAILED TREE VIEWS (WITH DESCRIPTIONS AND FORMATTING) ===\n"
            )

            # Save conventional rich tree
            # Create a more prominent title with explanation
            is_ai_tree = False
            border_style = "blue"
            title_style = "bold white on " + border_style
            title = "Conventional Website Structure (URL-based)"
            explanation = (
                "Links are grouped by their URL structure (directories and paths)"
            )

            file_console.print(f"\n{title}\n{explanation}\n")

            # Capture tree nodes
            self._save_rich_tree_to_file(self.conventional_tree, file_console)

            # Save LLM rich tree
            is_ai_tree = True
            border_style = "green"
            title_style = "bold white on " + border_style
            title = "Enhanced Website Structure (AI-based)"
            explanation = "Links are organized by their purpose and content (using AI categorization)"

            file_console.print(f"\n{title}\n{explanation}\n")

            # Capture tree nodes
            self._save_rich_tree_to_file(self.llm_tree, file_console)

        # Save as JSON for programmatic use
        json_file = f"{base_filename}_trees.json"
        import json

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.get_tree_json(), f, indent=2)

        self.console.print(f"[bold green]Output saved to:[/bold green]")
        self.console.print(f"- Conventional tree: [blue]{conv_file}[/blue]")
        self.console.print(f"- Enhanced tree: [blue]{llm_file}[/blue]")
        self.console.print(f"- Rich formatted trees: [blue]{rich_file}[/blue]")
        self.console.print(f"- JSON format: [blue]{json_file}[/blue]")

    def _save_rich_tree_to_file(self, tree, file_console):
        """Save a rich tree to a file using the provided console."""

        def format_node_for_file(node, indent=0):
            """Format a node for file output."""
            indentation = "  " * indent
            node_data = node.data or {}
            node_type = node_data.get("type", "unknown")

            if node_type == "category":
                file_console.print(f"{indentation}📁 {node.tag}")

                # Print description if available
                if node_data.get("description"):
                    file_console.print(f"{indentation}   {node_data['description']}")

            elif node_type == "path_category":
                file_console.print(f"{indentation}📂 {node.tag}")

            elif node_type == "domain":
                file_console.print(f"{indentation}🌐 {node.tag}")

            elif node_type == "link":
                # Determine importance if available
                importance = node_data.get("importance", 3)
                importance_marker = ""

                if importance >= 4:
                    importance_marker = "⭐ "

                url = node_data.get("url", "")
                file_console.print(f"{indentation}🔗 {importance_marker}{node.tag}")

                # Print URL
                file_console.print(f"{indentation}   {url}")

            else:
                # Root or other node type
                if node.identifier == "root":
                    file_console.print(f"{indentation}🌍 {node.tag}")
                else:
                    file_console.print(f"{indentation}• {node.tag}")

        def traverse_tree_for_file(node_id, indent=0):
            """Traverse the tree and format each node for file output."""
            node = tree.get_node(node_id)
            format_node_for_file(node, indent)

            for child_id in tree.is_branch(node_id):
                traverse_tree_for_file(child_id, indent + 1)

        # Display the tree starting from root
        traverse_tree_for_file("root", 0)
