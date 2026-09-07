"""Collect every public repository listed in GitHub's dependents view."""
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

DEPENDENTS_URL = "https://github.com/hect0x7/JMComic-Crawler-Python/network/dependents"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = [dict(attrs), ""]

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.links.append(self.current)
            self.current = None


def parse_dependents_page(html):
    page = Links()
    page.feed(html)
    totals = [int(re.sub(r"\D", "", text)) for attrs, text in page.links
              if "selected" in attrs.get("class", "").split()
              and "dependent_type=REPOSITORY" in attrs.get("href", "")]
    if len(totals) != 1:
        raise ValueError("cannot read the displayed dependents count")
    names = []
    for row in re.findall(r'<span\b[^>]*data-repository-hovercards-enabled[^>]*>(.*?)</span>', html, re.S):
        links = Links()
        links.feed(row)
        repositories = [attrs["href"].strip("/") for attrs, _ in links.links
                        if attrs.get("data-hovercard-type") == "repository"]
        if len(repositories) != 1 or not re.fullmatch(r"[\w.-]+/[\w.-]+", repositories[0]):
            raise ValueError("unrecognized dependent repository row")
        names.extend(repositories)
    next_links = [urljoin(DEPENDENTS_URL, attrs["href"]) for attrs, text in page.links
                  if text.strip() == "Next"]
    if len(next_links) > 1:
        raise ValueError("ambiguous dependents pagination")
    if not next_links and not re.search(r'<button\b[^>]*disabled[^>]*>\s*Next\s*</button>', html):
        raise ValueError("cannot verify the end of dependents pagination")
    return totals[0], names, next_links[0] if next_links else None


def read_page(url):
    request = urllib.request.Request(url, headers={"User-Agent": "hect0x7-used-by-generator"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def collect_dependents(fetch_page=read_page):
    url = DEPENDENTS_URL
    seen_pages, names = set(), set()
    expected = None
    while url:
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.netloc != "github.com"
                or parsed.path != urlparse(DEPENDENTS_URL).path or url in seen_pages):
            raise ValueError("invalid or repeated dependents pagination URL")
        seen_pages.add(url)
        total, page_names, url = parse_dependents_page(fetch_page(url))
        if expected is not None and total != expected:
            raise ValueError("dependents changed during collection; retry the complete run")
        expected = total
        names.update(name.lower() for name in page_names)
    # Keep GitHub's reported count separate from the enumerable repository list.
    if expected and not names:
        raise ValueError("no repositories parsed from a non-empty dependents view")
    return expected, sorted(names)


def fetch_all_metadata(names, fetch_repository, token=None):
    def fetch(name):
        owner, repo = name.split("/")
        data = fetch_repository(owner, repo, token)
        if not data.get("pushed_at"):
            raise ValueError(f"missing pushed_at for {name}")
        return data

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(fetch, names))
