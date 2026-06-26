from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "index.html"
ARTICLES_HTML = ROOT / "articles.html"
ARTICLES_JSON = ROOT / "data" / "articles.json"
MAX_HOME_CARDS = 6

SKIP_PATHS = {
    "index.html",
    "articles.html",
    "sitemap.xml",
    "robots.txt",
}


def normalize_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def is_article_page(path: Path) -> bool:
    rel = normalize_path(path)
    if rel in SKIP_PATHS:
        return False
    if not rel.endswith(".html"):
        return False
    # Treat dedicated HTML pages as article/guide pages.
    return rel.startswith(("articles/", "bosses/", ""))


def iter_html_files() -> Iterable[Path]:
    for path in sorted(ROOT.rglob("*.html")):
        if not path.is_file():
            continue
        if ".codex" in path.parts or ".git" in path.parts:
            continue
        yield path


def extract_title(html: str, rel_path: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if match:
        title = match.group(1)
        title = re.sub(r"\s+", " ", title).strip()
        for sep in [" — ", " - ", " | ", " – "]:
            if sep in title:
                title = title.split(sep, 1)[0]
                break
        if title:
            return title
    return rel_path


def parse_date_published(html: str) -> str | None:
    match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
    if not match:
        match = re.search(r'"datePublished"\s*:\s*"?([0-9T:\-Z]+)"?', html)
    return match.group(1) if match else None


def parse_date_modified(html: str) -> str | None:
    match = re.search(r'"dateModified"\s*:\s*"([^"]+)"', html)
    return match.group(1) if match else None


def parse_meta_description(html: str) -> str | None:
    match = re.search(r'<meta name="description" content="([^"]+)"', html, re.I)
    return match.group(1).strip() if match else None


def infer_category(rel_path: str) -> str:
    if rel_path.startswith("articles/"):
        return "Articles"
    if rel_path.startswith("bosses/"):
        return "Bosses"
    return "Guide"


def page_summary(rel_path: str, html: str) -> str:
    desc = parse_meta_description(html)
    if desc:
        return desc
    match = re.search(r"<p[^>]*>(.*?)</p>", html, re.S | re.I)
    if match:
        text = re.sub(r"<[^>]+>", "", match.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 160:
            text = text[:157] + "..."
        return text
    return ""


def infer_display_title(rel_path: str, title: str) -> str:
    title = title.replace("Mortal Shell II", "").strip()
    title = re.sub(r"\s+", " ", title)
    return title or rel_path


def build_articles() -> list[dict[str, str]]:
    articles = []
    for path in iter_html_files():
        rel = normalize_path(path)
        if not is_article_page(Path(rel)):
            continue
        html = path.read_text(encoding="utf-8", errors="ignore")
        title = extract_title(html, rel)
        published = parse_date_published(html)
        modified = parse_date_modified(html)
        if not published and not modified:
            continue
        date_value = published or modified
        articles.append(
            {
                "path": rel,
                "url": rel,
                "title": title,
                "display_title": infer_display_title(rel, title),
                "summary": page_summary(rel, html),
                "category": infer_category(rel),
                "datePublished": published,
                "dateModified": modified,
                "sortKey": date_value,
            }
        )

    def sort_key(item: dict[str, str]) -> tuple[str, str]:
        date = item.get("sortKey") or "0000-00-00"
        return (date, item.get("display_title", ""))

    articles.sort(key=sort_key, reverse=True)
    for article in articles:
        article.pop("sortKey", None)
    return articles


def date_display(date_value: str | None) -> str:
    if not date_value:
        return ""
    try:
        dt = datetime.fromisoformat(date_value)
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return date_value


def build_home_cards(articles: list[dict[str, str]]) -> str:
    lines = [
        '<section class="latest-articles" id="latest-articles">',
        '  <h2 style="text-align:center">Latest Articles</h2>',
        '  <p style="color:var(--text-muted);text-align:center;margin:0 auto 2rem;max-width:720px">Fresh strategy breakdowns and walkthroughs pulled automatically from the newest guides.</p>',
        '  <div class="card-grid">',
    ]

    for article in articles[:MAX_HOME_CARDS]:
        date_text = date_display(article.get("datePublished") or article.get("dateModified"))
        summary = article.get("summary", "")
        lines.append("    <div class=\"card\">")
        lines.append(f'      <h3><a href="{article["url"]}">{article["display_title"]}</a></h3>')
        if summary:
            lines.append(f"      <p>{summary}</p>")
        if date_text:
            lines.append(f'      <p style="font-size:.8rem;color:var(--text-muted);margin-top:.5rem">{date_text} · {article["category"]}</p>')
        lines.append("    </div>")

    lines.append("  </div>")
    lines.append("</section>")
    return "\n".join(lines)


def build_articles_cards(articles: list[dict[str, str]]) -> str:
    lines = []
    for article in articles:
        date_text = date_display(article.get("datePublished") or article.get("dateModified"))
        summary = article.get("summary", "")
        lines.append("    <div class=\"card\">")
        lines.append(f'      <h3><a href="{article["url"]}">{article["display_title"]}</a></h3>')
        if summary:
            lines.append(f"      <p>{summary}</p>")
        if date_text:
            lines.append(f'      <p style="font-size:.8rem;color:var(--text-muted);margin-top:.5rem">{date_text} · {article["category"]}</p>')
        lines.append("    </div>")
    return "\n".join(lines)


def update_block(html: str, start_comment: str, end_comment: str, block: str) -> str:
    pattern = re.compile(
        rf"({re.escape(start_comment)}\s*)(.*?)(\s*{re.escape(end_comment)})",
        re.S,
    )
    if pattern.search(html):
        return pattern.sub(rf"\g<1>{block}\g<3>", html)
    return html


def ensure_home_block(html: str, block: str) -> str:
    start = "<!-- HOME_LATEST_ARTICLES_START -->"
    end = "<!-- HOME_LATEST_ARTICLES_END -->"
    if start in html:
        return update_block(html, start, end, block)
    insertion = f"\n{start}\n{block}\n{end}\n"
    footer_match = re.search(r"\n<footer class=\"site-footer\">", html)
    if footer_match:
        return html[: footer_match.start()] + insertion + html[footer_match.start() :]
    return html + insertion


def ensure_articles_block(html: str, block: str) -> str:
    start = "<!-- ARTICLES_LIST_START -->"
    end = "<!-- ARTICLES_LIST_END -->"
    if start in html:
        return update_block(html, start, end, block)
    grid_match = re.search(r"<div class=\"card-grid\" id=\"articles-grid\">(.*?)</div>", html, re.S)
    if grid_match:
        replacement = f"{start}\n    <div class=\"card-grid\" id=\"articles-grid\">\n{block}\n    </div>\n{end}"
        return html[: grid_match.start()] + replacement + html[grid_match.end() :]
    return html


def save_articles_json(articles: list[dict[str, str]]) -> None:
    ARTICLES_JSON.parent.mkdir(parents=True, exist_ok=True)
    ARTICLES_JSON.write_text(
        json.dumps(articles, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    articles = build_articles()
    if not articles:
        raise SystemExit("No dated article pages found.")

    save_articles_json(articles)

    home_html = INDEX_HTML.read_text(encoding="utf-8", errors="ignore")
    home_html = ensure_home_block(home_html, build_home_cards(articles))
    INDEX_HTML.write_text(home_html, encoding="utf-8")

    articles_html = ARTICLES_HTML.read_text(encoding="utf-8", errors="ignore")
    articles_html = ensure_articles_block(articles_html, build_articles_cards(articles))
    ARTICLES_HTML.write_text(articles_html, encoding="utf-8")

    print(f"Updated {len(articles)} articles")
    print(f"Homepage latest: {min(len(articles), MAX_HOME_CARDS)}")
    print(f"Saved: {normalize_path(ARTICLES_JSON)}")


if __name__ == "__main__":
    main()
