import os
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup
import requests
from tqdm import tqdm

from lore_master.core.config import get_settings

API = "https://hollowknight.fandom.com/api.php"
HEADERS = {"User-Agent": "LoreMasterLearningBot/0.1"}

# Verified via the API (list=categorymembers&cmtitle=Category:Wiki): every
# other category on this wiki - "Category:Hollow Knight",
# "Category:Hollow Knight: Silksong", "Category:Lore", etc. - is nested as a
# sub-category underneath this one, making it the true root of the tree.
ROOT_CATEGORY = "Category:Wiki"
DEFAULT_MAX_DEPTH = 6

s = get_settings()
KNOWLEDE_BASE = str(Path(__file__).resolve().parents[3] / s.knowlede_dir)


def _slugify(title: str) -> str:
    """Turn a wiki page/category title into a filesystem-safe name."""
    return re.sub(r"[^\w\-]+", "_", title).strip("_") or "untitled"


def fetch_category_members(category: str) -> list[dict]:
    """List everything that belongs to a category.

    Each member comes back as {"title": ..., "ns": ...}. ``ns`` (namespace)
    tells us what kind of member it is: 0 = a normal article page,
    14 = another category (a sub-category we still need to crawl into).
    """
    params = {
        "action": "query", "list": "categorymembers",
        "cmtitle": category, "cmlimit": "500",
        "format": "json",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    time.sleep(0.5)
    return r.json().get("query", {}).get("categorymembers", [])


def fetch_page_content(title: str) -> tuple[str, str]:
    """Return ``(plaintext, url)`` for a single wiki page.

    Note: this wiki doesn't support the TextExtracts API extension
    (prop=extracts/explaintext), so we render the page with
    action=parse and strip the HTML down to plain text ourselves.
    """
    params = {
        "action": "parse", "prop": "text",
        "redirects": "1", "page": title, "format": "json",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    time.sleep(0.5)
    html = r.json()["parse"]["text"]["*"]
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("div.mw-parser-output") or soup
    for sel in ("table", ".infobox", ".portable-infobox", ".navbox",
                ".reference", ".reflist", ".references", ".mw-editsection",
                ".toc", "figure", "style", "script"):
        for tag in body.select(sel):
            tag.decompose()
    blocks = []
    for el in body.find_all(["h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "dl"], recursive=False):
        chunk = el.get_text(separator=" ", strip=True)
        if chunk:
            blocks.append(chunk)
    text = "\n\n".join(blocks)
    url = f"https://hollowknight.fandom.com/wiki/{title.replace(' ', '_')}"
    return text, url


def crawl(
    category: str,
    base_path: Path,
    visited: set,
    depth: int = 0,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> int:
    """Recursively walk one category, saving every page found inside it.

    ``visited`` tracks every category and page title we've already handled.
    Wiki categories can reference each other in cycles (A lists B as a
    sub-category, B lists A back), so without this the recursion could loop
    forever. ``max_depth`` is a second, cheaper safety net in case two
    different-looking titles secretly point at the same category.
    """
    if category in visited or depth > max_depth:
        return 0
    visited.add(category)

    folder = base_path / _slugify(category)
    folder.mkdir(parents=True, exist_ok=True)
    tqdm.write(f"{'  ' * depth}Category: {category}")

    saved = 0
    for member in tqdm(fetch_category_members(category), desc=f"crawling {category}", leave=False):
        title = member.get("title", "")
        ns = member.get("ns")

        if ns == 14:  # sub-category -> recurse one level deeper
            saved += crawl(title, folder, visited, depth + 1, max_depth)
            continue

        if ns != 0 or title in visited:  # skip non-article namespaces & repeats
            continue
        visited.add(title)

        path = folder / f"{_slugify(title)}.md"
        if path.exists():  # already fetched in a previous run - don't re-fetch
            tqdm.write(f"{'  ' * depth}  skip (already saved): {title}")
            continue

        try:
            text, url = fetch_page_content(title)
        except Exception as exc:
            tqdm.write(f"{'  ' * depth}  ! failed to fetch '{title}': {exc}")
            continue

        if not text.strip():
            continue

        path.write_text(f"# {title}\n\nSource: {url}\n\n{text}", encoding="utf-8")
        tqdm.write(f"{'  ' * depth}  saved: {title}")
        saved += 1

    return saved


def _remove_empty_folders(base_path: Path) -> int:
    """Delete leftover empty folders (e.g. categories whose only members
    are File: pages, which we don't fetch). Walks bottom-up (topdown=False)
    so a folder that only becomes empty once its own empty children are
    removed still gets cleaned up in the same pass.
    """
    removed = 0
    for dirpath, _dirnames, _filenames in os.walk(base_path, topdown=False):
        folder = Path(dirpath)
        if folder != base_path and not any(folder.iterdir()):
            folder.rmdir()
            removed += 1
    return removed


def fetch_wiki() -> None:
    """Crawl the entire Hollow Knight wiki and save every page as markdown.

    Starts from ``ROOT_CATEGORY`` and recurses into every sub-category, so
    no hardcoded category list is needed - the wiki's own structure decides
    what gets fetched.
    """
    base_path = Path(KNOWLEDE_BASE)
    base_path.mkdir(parents=True, exist_ok=True)

    visited: set = set()
    total_saved = crawl(ROOT_CATEGORY, base_path, visited)
    removed = _remove_empty_folders(base_path)
    print(
        f"Done. Saved {total_saved} pages ({len(visited)} categories/pages visited). "
        f"Removed {removed} empty folders."
    )
