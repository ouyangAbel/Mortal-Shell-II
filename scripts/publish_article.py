from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "index.html"
ARTICLES_HTML = ROOT / "articles.html"
ARTICLES_JSON = ROOT / "data" / "articles.json"
SITEMAP_XML = ROOT / "sitemap.xml"
BASE_URL = "https://shell2hub.com"

SKIP_PATHS = {
    "index.html",
    "articles.html",
    "sitemap.xml",
    "robots.txt",
}

ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def normalize_url(page_rel: str) -> str:
    return f"{BASE_URL}/{page_rel}"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def extract_title(html: str, page_rel: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        for sep in [" \u2013", " - ", " | ", " \u2014"]:
            if sep in title:
                return title.split(sep, 1)[0]
        return title
    return page_rel


def parse_date_published(html: str) -> str | None:
    match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
    return match.group(1) if match else None


def parse_date_modified(html: str) -> str | None:
    match = re.search(r'"dateModified"\s*:\s*"([^"]+)"', html)
    return match.group(1) if match else None


def parse_meta_description(html: str) -> str | None:
    match = re.search(r'<meta name="description" content="([^"]+)"', html, re.I)
    return match.group(1).strip() if match else None


def infer_category(page_rel: str) -> str:
    if page_rel.startswith("articles/"):
        return "Articles"
    if page_rel.startswith("bosses/"):
        return "Bosses"
    return "Guide"


def display_title(title: str) -> str:
    cleaned = title.replace("Mortal Shell II", "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or title


def summary(html: str) -> str:
    desc = parse_meta_description(html)
    if desc:
        return desc
    match = re.search(r"<p[^>]*>(.*?)</p>", html, re.S | re.I)
    if match:
        text = re.sub(r"<[^>]+>", "", match.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        return text[:157] + "..." if len(text) > 160 else text
    return ""


def date_display(date_value: str | None) -> str:
    if not date_value:
        return ""
    try:
        return datetime.fromisoformat(date_value).strftime("%b %d, %Y")
    except ValueError:
        return date_value


def iter_html_files() -> Iterable[Path]:
    for path in sorted(ROOT.rglob("*.html")):
        if not path.is_file():
            continue
        if ".codex" in path.parts or ".git" in path.parts:
            continue
        yield path


def load_existing_articles() -> dict[str, dict[str, str]]:
    if not ARTICLES_JSON.exists():
        return {}
    try:
        data = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
        return {item["path"]: item for item in data}
    except (json.JSONDecodeError, KeyError):
        return {}


def build_article_record(page_rel: str) -> dict[str, str] | None:
    path = ROOT / page_rel
    if not path.exists():
        return None
    html = path.read_text(encoding="utf-8", errors="ignore")
    title = extract_title(html, page_rel)
    published = parse_date_published(html)
    modified = parse_date_modified(html)
    if not published and not modified:
        return None
    return {
        "path": page_rel,
        "url": page_rel,
        "title": title,
        "display_title": display_title(title),
        "summary": summary(html),
        "category": infer_category(page_rel),
        "datePublished": published,
        "dateModified": modified,
        "sortKey": published or modified,
    }


def update_article_records(target_paths: list[str] | None = None) -> list[dict[str, str]]:
    existing = load_existing_articles()

    if target_paths:
        candidates = []
        for raw_path in target_paths:
            normalized = rel(Path(raw_path))
            candidates.append(normalized)
            if normalized not in existing:
                # ensure parent records exist for listing consistency
                pass
    else:
        candidates = [rel(path) for path in iter_html_files() if rel(path) not in SKIP_PATHS]

    seen: set[str] = set()
    for page_rel in candidates:
        seen.add(page_rel)
        record = build_article_record(page_rel)
        if record:
            existing[page_rel] = record

    articles = list(existing.values())

    def sort_key(item: dict[str, str]) -> tuple[str, str]:
        return (item.get("sortKey") or "0000-00-00", item.get("display_title", ""))

    articles.sort(key=sort_key, reverse=True)
    for article in articles:
        article.pop("sortKey", None)
    return articles


def save_articles_json(articles: list[dict[str, str]]) -> None:
    ensure_parent(ARTICLES_JSON)
    ARTICLES_JSON.write_text(json.dumps(articles, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_home_cards(articles: list[dict[str, str]], limit: int = 6) -> str:
    lines = [
        '<section class="latest-articles" id="latest-articles">',
        '  <h2 style="text-align:center">Latest Articles</h2>',
        '  <p style="color:var(--text-muted);text-align:center;margin:0 auto 2rem;max-width:720px">Fresh strategy breakdowns and walkthroughs pulled automatically from the newest guides.</p>',
        '  <div class="card-grid">',
    ]
    for article in articles[:limit]:
        date_text = date_display(article.get("datePublished") or article.get("dateModified"))
        lines.append("    <div class=\"card\">")
        lines.append(f'      <h3><a href="{article["url"]}">{article["display_title"]}</a></h3>')
        if article.get("summary"):
            lines.append(f'      <p>{article["summary"]}</p>')
        if date_text:
            lines.append(f'      <p style="font-size:.8rem;color:var(--text-muted);margin-top:.5rem">{date_text} \u00b7 {article["category"]}</p>')
        lines.append("    </div>")
    lines += ["  </div>", "</section>"]
    return "\n".join(lines)


def build_articles_cards(articles: list[dict[str, str]]) -> str:
    lines = []
    for article in articles:
        date_text = date_display(article.get("datePublished") or article.get("dateModified"))
        lines.append("    <div class=\"card\">")
        lines.append(f'      <h3><a href="{article["url"]}">{article["display_title"]}</a></h3>')
        if article.get("summary"):
            lines.append(f'      <p>{article["summary"]}</p>')
        if date_text:
            lines.append(f'      <p style="font-size:.8rem;color:var(--text-muted);margin-top:.5rem">{date_text} \u00b7 {article["category"]}</p>')
        lines.append("    </div>")
    return "\n".join(lines)


def update_block(html: str, start_comment: str, end_comment: str, block: str) -> str:
    pattern = re.compile(rf"({re.escape(start_comment)}\s*)(.*?)(\s*{re.escape(end_comment)})", re.S)
    if pattern.search(html):
        return pattern.sub(rf"\g<1>{block}\g<3>", html)
    return html


def sync_home_latest(articles: list[dict[str, str]]) -> None:
    html = INDEX_HTML.read_text(encoding="utf-8", errors="ignore")
    block = build_home_cards(articles)
    start = "<!-- HOME_LATEST_ARTICLES_START -->"
    end = "<!-- HOME_LATEST_ARTICLES_END -->"
    if start in html:
        html = update_block(html, start, end, block)
    else:
        insertion = f"\n{start}\n{block}\n{end}\n"
        footer_match = re.search(r"\n<footer class=\"site-footer\">", html)
        if footer_match:
            html = html[: footer_match.start()] + insertion + html[footer_match.start() :]
        else:
            html += insertion
    INDEX_HTML.write_text(html, encoding="utf-8")


def sync_articles_listing(articles: list[dict[str, str]]) -> None:
    html = ARTICLES_HTML.read_text(encoding="utf-8", errors="ignore")
    block = build_articles_cards(articles)
    start = "<!-- ARTICLES_LIST_START -->"
    end = "<!-- ARTICLES_LIST_END -->"
    if start in html:
        html = update_block(html, start, end, block)
    ARTICLES_HTML.write_text(html, encoding="utf-8")


def sync_sitemap(articles: list[dict[str, str]]) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    tree = ET.parse(SITEMAP_XML)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    existing_urls = {loc.text for loc in root.findall("sm:url/sm:loc", ns)}

    # Always ensure homepage is fresh
    for url_elem in root.findall("sm:url", ns):
        loc = url_elem.find("sm:loc", ns)
        if loc is not None and loc.text == BASE_URL + "/":
            changefreq = url_elem.find("sm:changefreq", ns)
            if changefreq is not None:
                changefreq.text = "weekly"
            priority = url_elem.find("sm:priority", ns)
            if priority is not None:
                priority.text = "1.0"

    added = False
    for article in articles:
        url = normalize_url(article["url"])
        if url in existing_urls:
            continue
        url_elem = ET.SubElement(root, "url")
        ET.SubElement(url_elem, "loc").text = url
        ET.SubElement(url_elem, "lastmod").text = today
        ET.SubElement(url_elem, "changefreq").text = "monthly"
        ET.SubElement(url_elem, "priority").text = "0.7"
        added = True

    if added:
        tree.write(SITEMAP_XML, encoding="UTF-8", xml_declaration=True)
        raw = SITEMAP_XML.read_text(encoding="utf-8")
        if "  <url>" in raw and "\n  <url>" not in raw:
            raw = raw.replace("  <url>", "\n  <url>")
        SITEMAP_XML.write_text(raw, encoding="utf-8")


def run(target_paths: list[str] | None = None) -> list[dict[str, str]]:
    articles = update_article_records(target_paths)
    save_articles_json(articles)
    sync_home_latest(articles)
    sync_articles_listing(articles)
    sync_sitemap(articles)
    return articles


def git_capture(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)


def git_run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)


def is_git_repo() -> bool:
    result = git_capture(["git", "rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0


def git_status_has_changes() -> bool:
    result = git_run(["git", "status", "--porcelain"])
    return bool(result.stdout.strip())


def current_branch() -> str:
    result = git_capture(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip() or "HEAD"


def has_upstream() -> bool:
    result = git_capture(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    return result.returncode == 0


def git_publish(message: str | None = None, target_paths: list[str] | None = None) -> None:
    if not is_git_repo():
        raise SystemExit(
            "Git publish skipped: current workspace is not recognized as a Git repository.\n"
            "Run this script again in a terminal where `git status` works."
        )

    if not git_status_has_changes():
        print("No git changes detected, skipping git publish")
        return

    stage_targets = ["data/articles.json", "index.html", "articles.html", "sitemap.xml"]
    if target_paths:
        stage_targets.extend(target_paths)

    unique_targets: list[str] = []
    seen: set[str] = set()
    for target in stage_targets:
        if target not in seen:
            seen.add(target)
            unique_targets.append(target)

    for target in unique_targets:
        git_run(["git", "add", target])

    if not message:
        if target_paths:
            basenames = [Path(path).name for path in target_paths[:3]]
            suffix = ", ".join(basenames) + ("..." if len(target_paths) > 3 else "")
            message = f"publish: {suffix}"
        else:
            message = "publish: refresh article listings"

    try:
        git_run(["git", "commit", "-m", message])
    except subprocess.CalledProcessError as exc:
        if "nothing to commit" in (exc.stdout or "") or "nothing to commit" in (exc.stderr or ""):
            print("Nothing to commit after staging, skipping push")
            return
        raise

    try:
        if has_upstream():
            git_run(["git", "pull", "--rebase"])
            git_run(["git", "push"])
        else:
            git_run(["git", "push", "-u", "origin", "HEAD"])
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "Article content synced, but git push failed.\n"
            f"Command: {' '.join(exc.cmd)}\n"
            f"stdout: {exc.stdout.strip()}\n"
            f"stderr: {exc.stderr.strip()}"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish or refresh Mortal Shell II pages.")
    parser.add_argument("paths", nargs="*", help="Optional page paths to publish. If omitted, all pages are refreshed.")
    parser.add_argument("-m", "--message", help="Optional git commit message.")
    parser.add_argument("--no-git", action="store_true", help="Only refresh files and skip git add/commit/push.")
    args = parser.parse_args()
    target_paths = args.paths or None
    articles = run(target_paths)
    print(f"Synced {len(articles)} article records")
    if target_paths:
        print("Updated paths: " + ", ".join(target_paths))
    else:
        print("Updated all discoverable pages")
    print("Homepage latest refreshed")
    print("Articles listing refreshed")
    print("Sitemap refreshed")
    if not args.no_git:
        git_publish(message=args.message, target_paths=target_paths)
        print("Git add/commit/push completed")


if __name__ == "__main__":
    main()
