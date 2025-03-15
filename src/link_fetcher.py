#!/usr/bin/env python3
"""
Link Fetcher - A CLI tool to fetch all links from a webpage.
Wrapper script for direct invocation.
"""

import sys
import argparse
import os
from urllib.parse import urlparse

# Import dotenv for loading environment variables from .env file (required)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the functionality from our main module
from link_fetcher.main import validate_url, fetch_webpage, extract_links, display_links
from link_fetcher.tree_builder import WebsiteTreeBuilder


def add_scheme_if_needed(url):
    """Add http:// scheme if no scheme is provided in the URL."""
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


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

    args = parser.parse_args()

    # Add http:// scheme if not provided
    url = add_scheme_if_needed(args.url)

    if not validate_url(url):
        from rich.console import Console

        console = Console()
        console.print(f"[bold red]Invalid URL: {url}[/bold red]")
        sys.exit(1)

    from rich.console import Console

    console = Console()

    try:
        console.print(f"[bold]Fetching links from: [/bold][cyan]{url}[/cyan]")

        html_content = fetch_webpage(url)
        links = extract_links(html_content, url)

        if not links:
            console.print("[yellow]No links found on the webpage.[/yellow]")
            sys.exit(0)

        console.print(f"[bold green]Found {len(links)} links.[/bold green]")

        if args.output == "tree":
            # Create a tree builder
            try:
                api_key = args.api_key
                tree_builder = WebsiteTreeBuilder(api_key=api_key)

                # Analyze and categorize links
                console.print("[bold]Analyzing and categorizing links...[/bold]")
                tree_builder.analyze_links(links, url)

                # Display both trees
                tree_builder.display_tree()

                # Save to files if requested
                if args.save_to:
                    console.print(f"\n[bold]Saving output to files...[/bold]")
                    tree_builder.save_to_files(args.save_to)

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
