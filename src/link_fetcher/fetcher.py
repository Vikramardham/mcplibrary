#!/usr/bin/env python3
"""
Link Fetcher - A CLI tool to fetch all links from a webpage.
"""

import argparse
import sys
import os
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table


def validate_url(url):
    """Validate if the provided URL is valid."""
    parsed = urlparse(url)
    return bool(parsed.netloc and parsed.scheme)


def add_scheme_if_needed(url):
    """Add https:// scheme if no scheme is provided in the URL."""
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


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


def fetch_page_content(url):
    """Fetch the content of a webpage and extract title, text, and images.
    
    Args:
        url: The URL of the webpage to fetch.
        
    Returns:
        A dictionary containing the page title, content text, and a list of image URLs.
    """
    try:
        response = httpx.get(url, follow_redirects=True)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract title
        title = soup.title.string if soup.title else "[No title]"
        
        # Extract main content (simplified approach)
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text content
        text = soup.get_text(separator="\n", strip=True)
        
        # Extract images
        images = []
        for img in soup.find_all("img", src=True):
            img_src = img.get("src")
            if img_src:
                # Convert relative URLs to absolute URLs
                absolute_img_url = urljoin(url, img_src)
                images.append(absolute_img_url)
        
        return {
            "title": title,
            "content": text,
            "images": images
        }
    except Exception as e:
        print(f"Error fetching page content: {e}")
        return {
            "title": "[Error]",
            "content": f"Error fetching content: {e}",
            "images": []
        }

def download_image(image_url, save_path):
    """Download an image from a URL and save it to the specified path.
    
    Args:
        image_url: The URL of the image to download.
        save_path: The path where the image should be saved.
        
    Returns:
        The local path to the saved image, or None if download failed.
    """
    try:
        response = httpx.get(image_url, follow_redirects=True)
        response.raise_for_status()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save the image
        with open(save_path, "wb") as f:
            f.write(response.content)
            
        return save_path
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
        return None


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
