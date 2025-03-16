#!/usr/bin/env python3
"""
Link Fetcher - A script to fetch all links from a webpage.
"""

import sys
import argparse
import os
from urllib.parse import urlparse
from pathlib import Path
import html
from rich.console import Console
from rich.table import Table
from trafilatura import fetch_url, extract

# Use absolute imports instead of relative imports
from lib.fetcher import (
    validate_url,
    fetch_webpage,
    extract_links,
    add_scheme_if_needed,
)
from lib.tree_builder import WebsiteTreeBuilder


def display_links(links, include_text=True):
    """Display links in a table format.

    Args:
        links: List of (url, text) tuples.
        include_text: Whether to include link text in the output.
    """
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("URL", style="dim", width=100)

    if include_text:
        table.add_column("Text", style="green")

    for link in links:
        if include_text:
            table.add_row(link[0], link[1])
        else:
            table.add_row(link[0])

    console.print(table)


def get_output_dir(url):
    """Create and return an output directory based on URL.

    Args:
        url: The input URL

    Returns:
        Path object for the output directory
    """
    # Parse the URL to get the domain
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace(":", "_").replace(".", "_")

    # Create output directory path
    # Use an absolute path to the output directory in the project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    base_output_dir = project_root / "output"
    output_dir = base_output_dir / domain

    # Ensure the directory exists
    os.makedirs(output_dir, exist_ok=True)

    return output_dir


def create_fasthtml_doc(url, links, output_dir):
    """Create a FastHTML-style document from the fetched links and their content.

    Args:
        url: The base URL that was crawled
        links: List of (url, text) tuples
        output_dir: Directory to save the output file

    Returns:
        Path to the created file
    """
    console = Console()

    # Create a file to store the FastHTML document
    fasthtml_file = output_dir / "fasthtml_doc.txt"

    # Parse the base URL to get the domain for the title
    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    # Start building the document
    with open(fasthtml_file, "w", encoding="utf-8") as f:
        # Write the project header
        f.write(
            f"<project title=\"{domain} Link Analysis\" summary='A collection of content from {domain} pages organized by hierarchy.'>\n\n"
        )

        # Create a hierarchy of links based on path structure
        hierarchy = {}
        for link_url, link_text in links:
            parsed_link = urlparse(link_url)
            if parsed_link.netloc != parsed_url.netloc:
                continue  # Skip external links

            # Get the path and split it into segments
            path = parsed_link.path.strip("/")
            if not path:
                path = "home"  # Root path

            segments = path.split("/")

            # Build the hierarchy
            current_level = hierarchy
            for i, segment in enumerate(segments):
                if not segment:
                    continue

                if segment not in current_level:
                    current_level[segment] = {"__links": []}

                if i == len(segments) - 1:
                    # This is the last segment, add the link
                    current_level[segment]["__links"].append((link_url, link_text))

                current_level = current_level[segment]

        # Write the hierarchy information at the top
        f.write("# Table of Contents\n\n")

        # Create a list of sections for the TOC
        toc_entries = []

        def write_hierarchy(level, path_segments=None, indent=0):
            if path_segments is None:
                path_segments = []

            for key, value in sorted(level.items()):
                if key == "__links":
                    continue

                current_path = path_segments + [key]
                section_id = "_".join(current_path)

                # Add to TOC entries
                toc_entries.append((section_id, key, indent))

                # Write the hierarchy item
                f.write(f"{' ' * indent}- {key}\n")

                # Process next level
                write_hierarchy(value, current_path, indent + 2)

        write_hierarchy(hierarchy)
        f.write("\n")

        # Write the actual TOC with links to sections
        f.write("## Document Sections\n\n")
        for section_id, section_name, indent in toc_entries:
            indent_spaces = " " * indent
            f.write(f"{indent_spaces}- [{section_name}](#{section_id})\n")

        f.write("\n---\n\n")

        # Process each link to extract content
        console.print("[bold]Fetching content from pages...[/bold]")

        # Track processed URLs to avoid duplicates
        processed_urls = set()

        # Track sections for TOC
        sections = []

        # Process links in a flattened hierarchy
        for link_url, link_text in links:
            parsed_link = urlparse(link_url)
            if parsed_link.netloc != parsed_url.netloc or link_url in processed_urls:
                continue

            processed_urls.add(link_url)

            try:
                console.print(f"[dim]Fetching: {link_url}[/dim]")

                # Use trafilatura to fetch and extract content
                downloaded = fetch_url(link_url)
                result = extract(
                    downloaded,
                    include_comments=True,
                    include_tables=True,
                    include_links=True,
                    include_images=True,
                    include_formatting=True,
                    output_format="markdown",
                    with_metadata=True,
                    url=link_url,
                )

                if not result:
                    raise Exception("Failed to extract content")

                # Start the document section
                path = parsed_link.path.strip("/")
                if not path:
                    path = "home"

                # Create a section ID for the TOC
                path_segments = path.split("/")
                section_id = "_".join([segment for segment in path_segments if segment])
                if not section_id:
                    section_id = "home"

                # Add an anchor for the TOC
                f.write(f'<a id="{section_id}"></a>\n\n')

                # Write the document with metadata and content
                f.write(
                    f'<doc title="{html.escape(link_text or "Untitled")}" desc="Content from {html.escape(link_url)}">\n\n'
                )
                f.write(result)
                f.write("\n</doc>\n\n")

            except Exception as e:
                console.print(f"[red]Error processing {link_url}: {e}[/red]")
                f.write(
                    f'<doc title="Error: {html.escape(link_url)}" desc="Failed to fetch content">\n'
                )
                f.write(f"Error fetching content: {e}\n")
                f.write("</doc>\n\n")

        # Close the project tag
        f.write("</project>")

    console.print(
        f"[bold green]Created FastHTML document: [/bold green][cyan]{fasthtml_file}[/cyan]"
    )
    return fasthtml_file


def main():
    """Main function to run the link fetcher as a script."""
    parser = argparse.ArgumentParser(description="Fetch all links from a webpage.")
    parser.add_argument("url", help="URL of the webpage to fetch links from")
    parser.add_argument(
        "--no-text", action="store_true", help="Don't include link text in the output"
    )
    parser.add_argument(
        "--output",
        choices=["table", "text", "tree", "fasthtml"],
        default="table",
        help="Output format: table, text, tree structure, or fasthtml document",
    )
    parser.add_argument(
        "--api-key",
        help="Google API key for using Generative AI (Gemini) categorization. Required if not in .env file.",
    )
    parser.add_argument(
        "--save-to",
        help="Save output to files with this base filename (will append _conventional.txt, _llm.txt, etc.)",
    )
    parser.add_argument(
        "--query",
        help="Retrieve relevant URLs for a specific query using LLM",
    )
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="Include page content in query results (only applicable with --query)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results to return for a query (only applicable with --query)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum number of pages to fetch content from (only applicable with --output fasthtml)",
    )

    args = parser.parse_args()

    # Add http:// scheme if not provided
    url = add_scheme_if_needed(args.url)

    if not validate_url(url):
        console = Console()
        console.print(f"[bold red]Invalid URL: {url}[/bold red]")
        sys.exit(1)

    console = Console()

    try:
        console.print(f"[bold]Fetching links from: [/bold][cyan]{url}[/cyan]")

        # Get output directory based on URL
        output_dir = get_output_dir(url)
        console.print(
            f"[bold]Output will be saved to: [/bold][cyan]{output_dir}[/cyan]"
        )

        html_content = fetch_webpage(url)
        links = extract_links(html_content, url)

        if not links:
            console.print("[yellow]No links found on the webpage.[/yellow]")
            sys.exit(0)

        console.print(f"[bold green]Found {len(links)} links.[/bold green]")

        # Save links to a text file in the output directory
        links_file_path = output_dir / "links.txt"
        with open(links_file_path, "w", encoding="utf-8") as f:
            for link_url, link_text in links:
                f.write(f"{link_url} | {link_text}\n")
        console.print(
            f"[bold green]Saved links to: [/bold green][cyan]{links_file_path}[/cyan]"
        )

        if args.output == "fasthtml":
            # Create a FastHTML-style document
            fasthtml_file = create_fasthtml_doc(
                url, links[: args.max_pages], output_dir
            )

        elif args.output == "tree" or args.query:
            # Create a tree builder
            try:
                api_key = args.api_key
                tree_builder = WebsiteTreeBuilder(api_key=api_key)

                # Analyze and categorize links
                console.print("[bold]Analyzing and categorizing links...[/bold]")
                tree_builder.analyze_links(links, url)

                # If query is provided, retrieve relevant URLs
                if args.query:
                    console.print(
                        f"\n[bold]Retrieving relevant URLs for query: [/bold][cyan]{args.query}[/cyan]"
                    )
                    tree_builder.retrieve_relevant_urls(
                        args.query,
                        include_content=args.include_content,
                        max_results=args.max_results,
                    )

                    # Save query results to file
                    query_results_file = (
                        output_dir / f"query_results_{args.query.replace(' ', '_')}.txt"
                    )
                    with open(query_results_file, "w", encoding="utf-8") as f:
                        console_file = Console(file=f, width=100)
                        tree_builder._save_rich_tree_to_file(
                            tree_builder.llm_tree, console_file
                        )
                    console.print(
                        f"[bold green]Saved query results to: [/bold green][cyan]{query_results_file}[/cyan]"
                    )

                    # If we're not displaying the tree, we can exit here
                    if args.output != "tree":
                        sys.exit(0)

                # Display both trees if output is tree
                if args.output == "tree":
                    tree_builder.display_tree()

                    # Generate filename in the output directory if not specified
                    if not args.save_to:
                        args.save_to = str(output_dir / "tree_output")
                    else:
                        # If save_to is specified but doesn't include the output directory,
                        # prepend the output directory
                        save_path = Path(args.save_to)
                        if output_dir.name not in str(save_path):
                            args.save_to = str(output_dir / save_path.name)

                    console.print("\n[bold]Saving output to files...[/bold]")
                    tree_builder.save_to_files(args.save_to, url)

            except ValueError as e:
                console.print(f"[bold red]Error: {e}[/bold red]")
                console.print(
                    "[yellow]Please add GEMINI_API_KEY to your .env file or provide it via --api-key parameter.[/yellow]"
                )
                sys.exit(1)
        elif args.output == "table":
            display_links(links, not args.no_text)

            # Save table to file
            table_file_path = output_dir / "links_table.txt"
            with open(table_file_path, "w", encoding="utf-8") as f:
                console_file = Console(file=f, width=100)
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("URL", style="dim", width=80)

                if not args.no_text:
                    table.add_column("Text", style="green")

                for link in links:
                    if not args.no_text:
                        table.add_row(link[0], link[1])
                    else:
                        table.add_row(link[0])

                console_file.print(table)
            console.print(
                f"[bold green]Saved table to: [/bold green][cyan]{table_file_path}[/cyan]"
            )
        else:
            for link in links:
                print(link[0])

            # Save plain text links to file
            text_file_path = output_dir / "links_plain.txt"
            with open(text_file_path, "w", encoding="utf-8") as f:
                for link in links:
                    f.write(f"{link[0]}\n")
            console.print(
                f"[bold green]Saved plain links to: [/bold green][cyan]{text_file_path}[/cyan]"
            )

    except Exception as e:
        console = Console()
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
