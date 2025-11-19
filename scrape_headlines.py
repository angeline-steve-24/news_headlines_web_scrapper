import requests
from bs4 import BeautifulSoup
import argparse
import time
from urllib.parse import urlparse

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; HeadlineScraper/1.0; +https://example.com/bot)"

def fetch_html(url, timeout=10, headers=None):
    headers = headers or {"User-Agent": DEFAULT_USER_AGENT}
    resp = requests.get(url, timeout=timeout, headers=headers)
    resp.raise_for_status()
    return resp.text

def extract_headlines(html, selectors):
    soup = BeautifulSoup(html, "html.parser")
    titles = []
    for sel in selectors:
        # Use CSS selectors when a '.' or '#' present, otherwise try tag name
        try:
            found = soup.select(sel) if (sel.startswith(".") or sel.startswith("#") or " " in sel or sel.find(">")!=-1 or sel.find("[")!=-1) else soup.find_all(sel)
        except Exception:
            # fallback: try find_all by tag name
            found = soup.find_all(sel)
        for node in found:
            # node might be a Tag or NavigableString; get text
            text = node.get_text(separator=" ", strip=True)
            if text:
                titles.append(text)
    # dedupe while preserving order
    seen = set()
    deduped = []
    for t in titles:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped

def guess_selectors_for_site(url):
    """
    Provide a short list of good default selectors for well-known/newsy sites.
    You can override by passing custom selectors via CLI.
    """
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower()
    # Common patterns: many sites use h1/h2, or classes like .headline or promo heading class for BBC
    if "bbc." in hostname:
        return [".gs-c-promo-heading__title", "h3", "h2"]
    if "cnn." in hostname:
        return [".cd__headline-text", "h2", "h3"]
    if "nytimes." in hostname or "nytimes" in hostname:
        return [".css-1cmu9py.e1voiwgp0", "h2", "h3"]
    # generic fallback
    return ["h1", "h2", "h3", ".headline", ".title", ".entry-title"]

def save_headlines(headlines, filepath, max_items=None):
    max_items = max_items or len(headlines)
    with open(filepath, "w", encoding="utf-8") as f:
        for i, t in enumerate(headlines[:max_items], start=1):
            f.write(f"{i}. {t}\n")
    return len(headlines[:max_items])

def main():
    p = argparse.ArgumentParser(description="Scrape top headlines from a news website and save to a .txt file")
    p.add_argument("--url", "-u", type=str, default="https://www.bbc.com/news", help="URL to scrape (default: BBC News)")
    p.add_argument("--output", "-o", type=str, default="headlines.txt", help="Output .txt file (default: headlines.txt)")
    p.add_argument("--selector", "-s", action="append", help="CSS/tag selector to look for (can be passed multiple times). If omitted, script will guess.")
    p.add_argument("--max", "-m", type=int, default=25, help="Maximum number of headlines to save (default 25)")
    p.add_argument("--delay", "-d", type=float, default=0.5, help="Delay before request in seconds (politeness) (default 0.5s)")
    args = p.parse_args()

    print(f"Scraping: {args.url}")
    # politeness delay
    time.sleep(args.delay)

    try:
        html = fetch_html(args.url)
    except requests.HTTPError as e:
        print("HTTP error while fetching:", e)
        return
    except requests.RequestException as e:
        print("Network error while fetching:", e)
        return

    selectors = args.selector if args.selector else guess_selectors_for_site(args.url)
    print("Using selectors (in order):", selectors)

    headlines = extract_headlines(html, selectors)
    if not headlines:
        print("No headlines found with the provided selectors. Try adding selectors using --selector")
        return

    saved_count = save_headlines(headlines, args.output, max_items=args.max)
    print(f"Found {len(headlines)} unique headlines — saved top {saved_count} to '{args.output}'.")

if __name__ == "__main__":
    main()
