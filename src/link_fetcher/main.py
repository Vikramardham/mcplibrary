#!/usr/bin/env python3
"""
Link Fetcher - A CLI tool to fetch all links from a webpage.
"""

import argparse
import sys
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table


def validate_url(url):
    """Validate if the provided URL is valid."""
    parsed = urlparse(url)
    return bool(parsed.netloc and parsed.scheme)


def fetch_webpage(url):
    """Fetch webpage content from the provided URL."""
    try:
        response = httpx.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.RequestError as e:
        raise Exception(f"Error fetching the webpage: {e}")
    except httpx.HTTPStatusError as e:
        raise Exception(f"HTTP error: {e}")


def extract_links(html_content, base_url):
    """Extract all links from the HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    links = []

    # Extract base domain for filtering external links
    base_domain = urlparse(base_url).netloc

    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href")
        if href:
            # Skip javascript links, anchors, and other non-http links
            if (
                href.startswith("javascript:")
                or href == "#"
                or href.startswith("mailto:")
            ):
                continue

            try:
                # Convert relative URLs to absolute URLs
                absolute_url = urljoin(base_url, href)

                # Check if the URL is valid
                if not validate_url(absolute_url):
                    continue

                # Check if the URL belongs to the same domain (filter external links)
                url_domain = urlparse(absolute_url).netloc
                if url_domain != base_domain:
                    continue

                link_text = a_tag.get_text(strip=True) or "[No text]"
                links.append((absolute_url, link_text))
            except Exception:
                # Skip any links that cause errors when parsing
                continue

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
