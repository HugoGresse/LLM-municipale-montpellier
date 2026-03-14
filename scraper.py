#!/usr/bin/env python3
"""
Scraper for https://montpellier-municipales.fr/
Crawls all pages within the domain and saves their text content to individual txt files.

Usage:
    python scraper.py [--output-dir OUTPUT_DIR] [--delay DELAY]

Options:
    --output-dir    Directory to save txt files (default: ./output)
    --delay         Delay in seconds between requests (default: 1.0)
"""

import argparse
import hashlib
import os
import re
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://montpellier-municipales.fr/"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_DELAY = 1.0
DEFAULT_TIMEOUT = 30.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MontpellierMunicipalesScraper/1.0; "
        "+https://github.com/HugoGresse/LLM-municipale-montpellier)"
    )
}


def sanitize_filename(url: str, base_url: str) -> str:
    """Convert a URL to a safe filename."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    # Replace slashes and other unsafe characters with underscores
    filename = re.sub(r"[^\w\-.]", "_", path)
    # Add query string hash if present to avoid collisions
    if parsed.query:
        query_hash = hashlib.md5(parsed.query.encode()).hexdigest()[:8]
        filename = f"{filename}_{query_hash}"
    return f"{filename}.txt"


def extract_text(soup: BeautifulSoup, url: str) -> str:
    """Extract readable text content from a BeautifulSoup page."""
    # Remove script and style elements
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    lines = [f"URL: {url}", ""]

    # Extract title
    title = soup.find("title")
    if title:
        lines.append(f"TITLE: {title.get_text(strip=True)}")
        lines.append("")

    # Extract meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        lines.append(f"DESCRIPTION: {meta_desc['content'].strip()}")
        lines.append("")

    # Extract main content
    lines.append("CONTENT:")
    lines.append("")

    # Try to find main content area
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"content|main|body", re.I))
        or soup.find(class_=re.compile(r"content|main|body", re.I))
        or soup.find("body")
    )

    if main_content:
        text = main_content.get_text(separator="\n", strip=True)
        # Collapse multiple blank lines into a single one
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines.append(text)

    return "\n".join(lines)


def is_internal_url(url: str, base_url: str) -> bool:
    """Check if a URL belongs to the same domain as the base URL."""
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    return parsed_url.netloc == parsed_base.netloc or parsed_url.netloc == ""


def extract_links(soup: BeautifulSoup, current_url: str) -> list[str]:
    """Extract all internal links from a page."""
    links = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute_url = urljoin(current_url, href)
        # Strip fragment
        absolute_url = absolute_url.split("#")[0]
        if is_internal_url(absolute_url, BASE_URL):
            links.append(absolute_url)
    return links


def scrape(output_dir: str = DEFAULT_OUTPUT_DIR, delay: float = DEFAULT_DELAY) -> None:
    """Crawl the website and save each page's content to a txt file."""
    os.makedirs(output_dir, exist_ok=True)

    visited: set[str] = set()
    queue: deque[str] = deque([BASE_URL])
    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"Starting scraper for {BASE_URL}")
    print(f"Output directory: {output_dir}")

    while queue:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        print(f"Scraping: {url}")
        try:
            response = session.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"  ERROR: {exc}")
            continue

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            print(f"  Skipping non-HTML content ({content_type})")
            continue

        soup = BeautifulSoup(response.text, "lxml")

        # Save text content
        text = extract_text(soup, url)
        filename = sanitize_filename(url, BASE_URL)
        filepath = os.path.join(output_dir, filename)

        # Handle filename collisions
        counter = 1
        base_filepath = filepath
        while os.path.exists(filepath):
            name, ext = os.path.splitext(base_filepath)
            filepath = f"{name}_{counter}{ext}"
            counter += 1

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  Saved to {filepath}")

        # Discover new links
        new_links = extract_links(soup, url)
        for link in new_links:
            if link not in visited:
                queue.append(link)

        if delay > 0:
            time.sleep(delay)

    print(f"\nDone! Scraped {len(visited)} pages.")
    print(f"Files saved in: {os.path.abspath(output_dir)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape all content from montpellier-municipales.fr into txt files."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save txt files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Delay in seconds between requests (default: {DEFAULT_DELAY})",
    )
    args = parser.parse_args()
    scrape(output_dir=args.output_dir, delay=args.delay)


if __name__ == "__main__":
    main()
