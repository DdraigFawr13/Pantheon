"""Render docs/BUILD_PLAN.md and docs/roadmap.md to one HTML page for the owner (D-018).

Standard library only. Usage: python3 scripts/render_plan.py OUT.html
Handles the Markdown these two files use: headings, paragraphs, bullet and
numbered lists (one nesting level), tables, code fences, **bold**, *italic*, `code`.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [("plan", "Build plan", ROOT / "docs/BUILD_PLAN.md"), ("roadmap", "Roadmap", ROOT / "docs/roadmap.md")]


def inline(text: str) -> str:
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        s = html.escape(part)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        out.append(s)
    return "".join(out)


def render(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    list_stack: list[str] = []

    def close_lists(depth: int = 0) -> None:
        while len(list_stack) > depth:
            out.append(f"</li></{list_stack.pop()}>")

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            close_lists()
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            out.append(f'<pre><code>{html.escape(chr(10).join(code))}</code></pre>')
            i += 1
            continue
        m = re.match(r"^(#{1,4}) (.*)$", line)
        if m:
            close_lists()
            level = len(m.group(1)) + 1
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue
        if line.startswith("|"):
            close_lists()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            trs = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(f'<div class="table"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
            continue
        m = re.match(r"^(\s*)(- |\d+\. )(.*)$", line)
        if m:
            depth = 1 + len(m.group(1)) // 2
            kind = "ol" if m.group(2)[0].isdigit() else "ul"
            if len(list_stack) < depth:
                list_stack.append(kind)
                out.append(f"<{kind}><li>")
            else:
                close_lists(depth)
                out.append("</li><li>")
            out.append(inline(m.group(3)))
            i += 1
            continue
        if not line.strip():
            close_lists()
            i += 1
            continue
        close_lists()
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||```|\s*- |\s*\d+\. )", lines[i]):
            para.append(lines[i])
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    close_lists()
    return "\n".join(out)


STYLE = """
:root { --bg:#f3f1ec; --surface:#fbfaf7; --ink:#1d2326; --muted:#5a6266; --line:#d9d4c8; --accent:#7a3b1d; --code:#ece7dc;
  --display:"Cormorant Garamond", Georgia, serif; --body:"Source Sans 3", system-ui, sans-serif; --mono:ui-monospace, Menlo, Consolas, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#15191b; --surface:#1c2124; --ink:#e6e2d9; --muted:#9aa1a4; --line:#30373a; --accent:#e0956a; --code:#252b2e; color-scheme:dark } }
:root[data-theme="dark"] { --bg:#15191b; --surface:#1c2124; --ink:#e6e2d9; --muted:#9aa1a4; --line:#30373a; --accent:#e0956a; --code:#252b2e; color-scheme:dark }
body { background:var(--bg); color:var(--ink); font:16px/1.55 var(--body); }
header { padding-block:20px 8px; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); max-width:760px; margin:0 auto; }
header h1 { font:600 2rem/1.1 var(--display); margin:0; letter-spacing:.01em; }
header p { color:var(--muted); margin:6px 0 0; font-size:.9rem; }
nav { display:flex; gap:8px; margin-top:12px; }
nav a { font-weight:600; font-size:.9rem; color:var(--accent); text-decoration:none; border:1px solid var(--line); border-radius:999px; padding:5px 12px; background:var(--surface); }
main { max-width:760px; margin:0 auto; padding-block:8px 64px; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }
section { background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:4px 18px 14px; margin-top:18px; min-width:0; }
h2 { font:600 1.6rem/1.2 var(--display); text-wrap:balance; color:var(--accent); }
h3 { font:600 1.3rem/1.25 var(--display); text-wrap:balance; margin:22px 0 6px; }
h4 { font-size:1rem; margin:16px 0 4px; }
p, li { max-width:68ch; } ul, ol { padding-left:22px; } li { margin:3px 0; }
code { font:.86em var(--mono); background:var(--code); border-radius:4px; padding:1px 4px; overflow-wrap:anywhere; }
pre { background:var(--code); border-radius:6px; padding:12px; overflow-x:auto; } pre code { background:none; padding:0; }
.table { overflow-x:auto; } table { border-collapse:collapse; font-size:.9rem; width:100%; }
th, td { text-align:left; vertical-align:top; padding:6px 8px; border-bottom:1px solid var(--line); } th { color:var(--muted); font-weight:600; }
strong { font-weight:700; }
"""


def main() -> None:
    out_path = Path(sys.argv[1])
    commit = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h %cs"], capture_output=True, text=True).stdout.strip()
    nav = "".join(f'<a href="#{slug}">{title}</a>' for slug, title, _ in SOURCES)
    body = "".join(f'<section id="{slug}">{render(path.read_text())}</section>' for slug, _, path in SOURCES)
    page = f"""<title>Pantheon Build Plan</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600&family=Source+Sans+3:wght@400;600;700&display=swap">
<style>{STYLE}</style>
<header><h1>Pantheon build plan</h1><p>Rendered from <code>docs/BUILD_PLAN.md</code> and <code>docs/roadmap.md</code> at {html.escape(commit)}.</p><nav>{nav}</nav></header>
<main>{body}</main>
"""
    out_path.write_text(page)


if __name__ == "__main__":
    main()
