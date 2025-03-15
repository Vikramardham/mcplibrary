#!/usr/bin/env python3
"""
Link Fetcher - A script to fetch all links from a webpage.
"""

import sys
import argparse
from rich.console import Console
from rich.table import Table

# Use absolute imports instead of relative imports
from src.link_fetcher.fetcher import (
    validate_url,
    fetch_webpage,
    extract_links,
    add_scheme_if_needed,
)
from src.link_fetcher.tree_builder import WebsiteTreeBuilder

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


def main():
    """Main function to run the link fetcher as a script."""
    parser = argparse.ArgumentParser(description="Fetch all links from a webpage.")
    parser.add_argument("url", help="URL of the webpage to fetch links from")
    parser.add_argument(
        "--no-text", action="store_true", help="Don't include link text in the output"
    )
    parser.add_argument(
        "--output",
        choices=["table", "text", "tree"],
        default="table",
        help="Output format: table, text, or tree structure",
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

        html_content = fetch_webpage(url)
        links = extract_links(html_content, url)

        if not links:
            console.print("[yellow]No links found on the webpage.[/yellow]")
            sys.exit(0)

        console.print(f"[bold green]Found {len(links)} links.[/bold green]")

        if args.output == "tree" or args.query:
            # Create a tree builder
            try:
                api_key = args.api_key
                tree_builder = WebsiteTreeBuilder(api_key=api_key)

                # Analyze and categorize links
                console.print("[bold]Analyzing and categorizing links...[/bold]")
                tree_builder.analyze_links(links, url)

                # If query is provided, retrieve relevant URLs
                if args.query:
                    console.print(f"\n[bold]Retrieving relevant URLs for query: [/bold][cyan]{args.query}[/cyan]")
                    tree_builder.retrieve_relevant_urls(
                        args.query, 
                        include_content=args.include_content,
                        max_results=args.max_results
                    )
                    
                    # If we're not displaying the tree, we can exit here
                    if args.output != "tree":
                        sys.exit(0)
                
                # Display both trees if output is tree
                if args.output == "tree":
                    tree_builder.display_tree()

                    # Save to files if requested
                    if args.save_to:
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
        else:
            for link in links:
                print(link[0])

    except Exception as e:
        console = Console()
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
