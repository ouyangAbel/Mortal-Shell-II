# Mortal Shell II Article Publishing Workflow

This project now uses a single script to keep the homepage, article listing, and sitemap in sync, and to publish changes through Git.

## One-command publish

```powershell
python scripts/publish_article.py <new-or-updated-page.html>
```

Example:

```powershell
python scripts/publish_article.py articles/new-build-guide.html
```

This will:
1. Read the target page metadata (`datePublished`, `dateModified`, title, description).
2. Update `data/articles.json` with the latest article list.
3. Refresh the homepage latest-articles section (`index.html`).
4. Refresh the full articles listing (`articles.html`).
5. Add missing URLs to `sitemap.xml`.
6. Run `git add`, `git commit`, and `git push` automatically.

## Refresh all pages

If you only changed metadata or summary text across multiple pages, you can refresh everything at once:

```powershell
python scripts/publish_article.py
```

## Custom commit message

```powershell
python scripts/publish_article.py articles/new-build-guide.html -m "publish: add new build guide"
```

## Skip Git

```powershell
python scripts/publish_article.py --no-git
```

## Notes

- Homepage always shows the newest 6 entries from `data/articles.json`.
- Article listing shows all discoverable entries from the same JSON source.
- Keep `datePublished` in the page JSON-LD so the script can sort correctly.
- If a page has no `datePublished`/`dateModified`, it will not appear in the article list.
- If Git publishing fails because the current directory is not recognized as a Git repository in this environment, run the script again in your normal terminal.
