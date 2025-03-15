#!/usr/bin/env python3
"""
Link Fetcher - A CLI tool to fetch all links from a webpage.
"""

import argparse
import sys
import os
from urllib.parse import urljoin, urlparse
import re
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from trafilatura import fetch_url, extract


def validate_url(url):
    """Validate if a URL is well-formed.

    Args:
        url: URL string to validate

    Returns:
        bool: True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def add_scheme_if_needed(url):
    """Add http:// scheme if not present in URL.

    Args:
        url: URL string to check

    Returns:
        URL with scheme added if needed
    """
    if not url.startswith(("http://", "https://")):
        return "http://" + url
    return url


def fetch_webpage(url):
    """Fetch webpage content from URL.

    Args:
        url: URL to fetch

    Returns:
        str: HTML content of webpage
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise Exception(f"Error fetching {url}: {e}")


def extract_links(html_content, base_url):
    """Extract all links from HTML content.

    Args:
        html_content: HTML content to parse
        base_url: Base URL for resolving relative links

    Returns:
        list: List of (url, text) tuples
    """
    soup = BeautifulSoup(html_content, "html.parser")
    links = []

    for link in soup.find_all("a"):
        href = link.get("href")
        if href:
            # Skip fragment identifiers and javascript links
            if href.startswith("#") or href.startswith("javascript:"):
                continue

            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)

            # Clean up the URL
            absolute_url = re.sub(r"#.*$", "", absolute_url)  # Remove fragments
            absolute_url = absolute_url.rstrip("/")  # Remove trailing slashes

            # Get link text
            text = link.get_text().strip()
            if not text:
                text = link.get("title", "").strip()
            if not text:
                text = href

            links.append((absolute_url, text))

    return links


def display_links(links, include_text=True):
    """Display the extracted links in a table format."""
    console = Console()
    table = Table(show_header=True)

    table.add_column("URL", style="blue")
    if include_text:
        table.add_column("Link Text", style="green")

    for link in links:
        if include_text:
            table.add_row(link[0], link[1])
        else:
            table.add_row(link[0])

    console.print(table)


def main():
    """Main function to run the CLI application."""
    parser = argparse.ArgumentParser(description="Fetch all links from a webpage.")
    parser.add_argument("url", help="URL of the webpage to fetch links from")
    parser.add_argument(
        "--no-text", action="store_true", help="Don't include link text in the output"
    )
    parser.add_argument(
        "--output",
        choices=["table", "text"],
        default="table",
        help="Output format: table or plain text",
    )

    args = parser.parse_args()

    if not validate_url(args.url):
        console = Console()
        console.print(f"[bold red]Invalid URL: {args.url}[/bold red]")
        sys.exit(1)

    try:
        console = Console()
        console.print(f"[bold]Fetching links from: [/bold][cyan]{args.url}[/cyan]")

        html_content = fetch_webpage(args.url)
        links = extract_links(html_content, args.url)

        if not links:
            console.print("[yellow]No links found on the webpage.[/yellow]")
            sys.exit(0)

        console.print(f"[bold green]Found {len(links)} links.[/bold green]")

        if args.output == "table":
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
