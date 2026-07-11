#!/usr/bin/env python3
"""Generate docs/index.html from README.md.

README.md is the source of truth. This script parses its markdown structure
(headings, bullet lists, inline **bold** / _italic_ / [links]()) and renders
a styled, single-page, print-friendly resume to docs/index.html for GitHub
Pages. Run after every README.md edit:

    python3 scripts/generate_page.py
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
OUT = ROOT / "docs" / "index.html"

INLINE_PATTERNS = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"_(.+?)_"), r"<em>\1</em>"),
    (
        re.compile(r"\[(.+?)\]\((.+?)\)"),
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
    ),
]

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE0E-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text):
    return EMOJI_RE.sub("", text).strip()


def inline(text):
    # Markdown syntax chars (* _ [ ] ( )) are not HTML-special, so escaping
    # first and then applying markdown->tag substitutions is safe.
    text = html.escape(text)
    for pattern, repl in INLINE_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def parse_readme(md_text):
    lines = md_text.splitlines()
    doc = {"name": "", "contact": "", "sections": []}
    current_section = None
    current_sub = None
    i = 0

    def flush_sub():
        nonlocal current_sub
        if current_sub is not None and current_section is not None:
            current_section["items"].append(current_sub)
            current_sub = None

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1
        if not line:
            continue

        if line.startswith("# "):
            doc["name"] = strip_emoji(line[2:].strip())
            continue

        if line.startswith("## "):
            flush_sub()
            current_sub = None
            title = strip_emoji(line[3:].strip())
            current_section = {"title": title, "intro": [], "items": []}
            doc["sections"].append(current_section)
            continue

        if line.startswith("### "):
            flush_sub()
            heading = line[4:].strip()
            current_sub = {
                "heading": inline(heading),
                "meta": "",
                "bullets": [],
                "text": [],
            }
            continue

        if line.startswith("- "):
            bullet = inline(line[2:].strip())
            if current_sub is not None:
                current_sub["bullets"].append(bullet)
            elif current_section is not None:
                current_section["items"].append(
                    {"heading": None, "meta": "", "bullets": [bullet], "text": []}
                )
            continue

        # plain paragraph line: contact line (right after H1), a subsection meta
        # line (location/dates), or free-text intro/paragraph.
        if doc["name"] and not doc["contact"] and current_section is None:
            doc["contact"] = inline(line)
            continue

        looks_like_meta = (
            current_sub is not None
            and not current_sub["bullets"]
            and re.match(r"^[\U0001F300-\U0001FAFF].*\|", line)
        )
        if looks_like_meta:
            current_sub["meta"] = inline(strip_emoji(line))
            continue

        if current_sub is not None:
            current_sub["text"].append(inline(line))
            continue

        if current_section is not None:
            current_section["intro"].append(inline(line))

    flush_sub()
    return doc


def render_items(items):
    out = []
    for item in items:
        out.append('<div class="entry">')
        if item["heading"]:
            out.append(f'<div class="entry-head"><h3>{item["heading"]}</h3>')
            if item["meta"]:
                out.append(f'<span class="meta">{item["meta"]}</span>')
            out.append("</div>")
        for para in item["text"]:
            out.append(f'<p class="entry-text">{para}</p>')
        if item["bullets"]:
            out.append("<ul>")
            out.extend(f"<li>{b}</li>" for b in item["bullets"])
            out.append("</ul>")
        out.append("</div>")
    return "\n".join(out)


def render_section(section):
    body = []
    for para in section["intro"]:
        body.append(f'<p class="intro">{para}</p>')
    body.append(render_items(section["items"]))
    slug = re.sub(r"[^a-z0-9]+", "-", section["title"].lower()).strip("-")
    return f'''<section class="card" id="{slug}">
<h2>{section["title"]}</h2>
{"".join(body)}
</section>'''


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — CV</title>
<meta name="description" content="{tagline}">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="hero">
  <div class="hero-inner">
    <h1>{name}</h1>
    <p class="contact">{contact}</p>
    <button class="print-btn" onclick="window.print()">Download / Print PDF</button>
  </div>
</header>
<main>
{sections}
</main>
<footer>
  <p>
    Generated from
    <a href="https://github.com/hardkoro/cv/blob/main/README.md">README.md</a>
    — the source of truth for this page.
  </p>
</footer>
</body>
</html>
"""


def build():
    md_text = README.read_text(encoding="utf-8")
    doc = parse_readme(md_text)
    sections_html = "\n".join(render_section(s) for s in doc["sections"])
    page = PAGE_TEMPLATE.format(
        name=doc["name"],
        tagline=f"CV of {doc['name']}",
        contact=doc["contact"],
        sections=sections_html,
    )
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
