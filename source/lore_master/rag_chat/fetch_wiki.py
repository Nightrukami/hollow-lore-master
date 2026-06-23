import time
import re
from pathlib import Path
from bs4 import BeautifulSoup
import requests
from tqdm import tqdm

from lore_master.core.config import get_settings

API = "https://hollowknight.fandom.com/api.php"
HEADERS = {"User-Agent": "LoreMasterLearningBot/0.1"}
s = get_settings()
KNOWLEDE_BASE = str(Path(__file__).resolve().parents[3] / s.knowlede_dir)

def list_category_pages(category: str = "Category:Lore") -> list[str]:
    params = {
        "action": "query", "list": "categorymembers",
        "cmtitle": category, "cmlimit": "500",
        "cmtype": "page",          # เอาเฉพาะหน้า ไม่เอา subcategory
        "format": "json",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    members = r.json()["query"]["categorymembers"]
    return [m["title"] for m in members]


def fetch_plaintext(title: str) -> tuple[str, str]:
    """Return ``(plaintext, url)`` for a single wiki page."""
    params = {
        "action": "parse", "prop": "text",
        "redirects": "1", "page": title, "format": "json",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
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


def _slugify(title: str) -> str:
    return re.sub(r"[^\w\-]+", "_", title).strip("_") or "untitled"


def fetch_wiki(
    delay: float = 0.5,
) -> None:
    """Fetch every page in ``category`` and write one ``.md`` file per page.

    Returns the number of files saved.
    """
    s = get_settings()
    for entry in s.lore_categories:
        if entry.startswith("Category:"):
            folder = Path(KNOWLEDE_BASE) / _slugify(entry)
            titles = list_category_pages(entry)
        else:
            # Not a category - treat the entry as a single page title.
            folder = Path(KNOWLEDE_BASE) / "General"
            titles = [entry]

        folder.mkdir(parents=True, exist_ok=True)

        saved = 0
        for title in tqdm(titles, desc="fetching wiki"):
            text, url = fetch_plaintext(title)
            if not text.strip():                   # ตัดหน้าว่างทิ้ง
                continue
            path = folder / f"{_slugify(title)}.md"
            # Keep the title and source URL in the file so they survive ingestion.
            path.write_text(
                f"# {title}\n\nSource: {url}\n\n{text}", encoding="utf-8"
            )
            saved += 1
            time.sleep(delay)
        print(f"save {saved} files in {entry}")                      # มารยาท: หน่วงเวลา ไม่ยิงรัว

    return

