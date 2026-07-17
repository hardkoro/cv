#!/usr/bin/env python3
"""Generate docs/index.html from README.md.

README.md is the source of truth. This script parses its markdown structure
(headings, bullet lists, inline **bold** / _italic_ / [links]()) and renders
a styled, two-column, print-friendly (single A4 page) resume to
docs/index.html for GitHub Pages. Run after every README.md edit:

    python3 scripts/generate_page.py
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
OUT = ROOT / "docs" / "index.html"

# Section titles (post emoji-strip) routed to the narrow sidebar column;
# everything else renders in the main column, in README order. Certifications
# stays in main so the two columns end up closer in height.
SIDEBAR_TITLES = {"skills", "education", "publications"}

IMAGE_RE = re.compile(r'<img\s+[^>]*src="([^"]+)"[^>]*>|!\[[^\]]*\]\(([^)]+)\)')

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
    doc = {"name": "", "contact": "", "photo": "", "sections": []}
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

        if doc["name"] and not doc["photo"] and current_section is None:
            image_match = IMAGE_RE.search(line)
            if image_match:
                doc["photo"] = image_match.group(1) or image_match.group(2)
                continue

        # plain paragraph line: contact line (right after H1), a subsection meta
        # line (location/dates), or free-text intro/paragraph.
        if doc["name"] and not doc["contact"] and current_section is None:
            doc["contact"] = inline(line)
            continue

        # A "Location | date range" line, with or without a leading emoji.
        is_meta_line = bool(re.match(r"^[^|]+\|.*\d{4}", strip_emoji(line)))

        if current_sub is not None and is_meta_line and not current_sub["bullets"]:
            current_sub["meta"] = inline(strip_emoji(line))
            continue

        if current_sub is not None:
            current_sub["text"].append(inline(line))
            continue

        if current_section is not None:
            current_section["intro"].append(
                {"text": inline(line), "meta": is_meta_line}
            )

    flush_sub()
    return doc


def strip_brackets(text):
    return re.sub(r"\s*\([^)]*\)", "", text).strip()


def render_items(items):
    out = []
    for item in items:
        flat = item["heading"] is None
        out.append(f'<div class="entry{" flat" if flat else ""}">')
        heading_text = re.sub(r"<[^>]+>", "", item["heading"] or "")
        if item["heading"]:
            out.append(f'<div class="entry-head"><h3>{item["heading"]}</h3>')
            if item["meta"]:
                out.append(f'<span class="meta">{item["meta"]}</span>')
            out.append("</div>")
        for para in item["text"]:
            out.append(f'<p class="entry-text">{para}</p>')
        if item["bullets"]:
            is_stack = heading_text.strip() == "Technical Stack"
            out.append("<ul>")
            out.extend(
                f"<li>{strip_brackets(b) if is_stack else b}</li>"
                for b in item["bullets"]
            )
            out.append("</ul>")
        out.append("</div>")
    return "\n".join(out)


def render_section(section):
    body = []
    for para in section["intro"]:
        cls = "intro meta-line" if para["meta"] else "intro"
        body.append(f'<p class="{cls}">{para["text"]}</p>')
    body.append(render_items(section["items"]))
    slug = re.sub(r"[^a-z0-9]+", "-", section["title"].lower()).strip("-")
    return f'''<section class="block" id="{slug}">
<h2>{section["title"]}</h2>
{"".join(body)}
</section>'''


def render_contact(contact):
    items = [item.strip() for item in contact.split(" | ") if item.strip()]
    if len(items) <= 1:
        return contact
    return "".join(f'<span class="contact-item">{item}</span>' for item in items)


def extract_role(doc):
    for section in doc["sections"]:
        if section["title"].strip().lower() == "experience":
            for item in section["items"]:
                if item["heading"]:
                    match = re.search(r"<em>(.+?)</em>", item["heading"])
                    if match:
                        return match.group(1)
    return ""


def initials(name):
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    return "".join(p[0].upper() for p in parts[:2])


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
<div class="page">
  <header class="masthead">
    {badge}
    <div class="id-text">
      <h1>{name}</h1>
      <p class="role">{role}</p>
      <p class="contact">{contact}</p>
    </div>
    <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
  </header>
  <div class="layout">
    <aside class="sidebar">
{sidebar}
    </aside>
    <div class="main-col">
{main}
    </div>
  </div>
</div>
</body>
</html>
"""


def render_badge(doc):
    name = html.escape(doc["name"])
    if doc["photo"]:
        src_path = ROOT / doc["photo"]
        dest = OUT.parent / src_path.name
        dest.write_bytes(src_path.read_bytes())
        return f'<img class="id-badge" src="{dest.name}" alt="{name}">'
    return f'<div class="id-badge">{initials(doc["name"])}</div>'


def build():
    md_text = README.read_text(encoding="utf-8")
    doc = parse_readme(md_text)

    sidebar_html, main_html = [], []
    for section in doc["sections"]:
        rendered = render_section(section)
        if section["title"].strip().lower() in SIDEBAR_TITLES:
            sidebar_html.append(rendered)
        else:
            main_html.append(rendered)

    OUT.parent.mkdir(exist_ok=True)
    page = PAGE_TEMPLATE.format(
        name=doc["name"],
        tagline=f"CV of {doc['name']}",
        role=extract_role(doc),
        badge=render_badge(doc),
        contact=render_contact(doc["contact"]),
        sidebar="\n".join(sidebar_html),
        main="\n".join(main_html),
    )
    OUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
