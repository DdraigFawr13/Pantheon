"""Render one docs Markdown file to a phone page in the Pantheon Table's style, for publishing as an artifact.

Usage: uv run python scripts/render_doc.py docs/specs/m2c-story-tools.md out.html
Uses markdown-it-py, which rich already depends on (no new dependency, SAFE-01).
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt

_STYLE = """
:root { --bg: #e8e4ec; --page: #f8f6fa; --ink: #211b27; --muted: #6a6072; --line: #d6cfdc; --brass: #8a5a12;
  --brass-soft: #f3e7d2; --glow: rgb(214 160 70 / .22);
  --display: "Alegreya SC", "Palatino Linotype", Georgia, serif; --prose: "Spectral", Georgia, serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #16111a; --page: #211a26;
  --ink: #efe6dc; --muted: #ab9db0; --line: #3b2f42; --brass: #e3b562; --brass-soft: #34281b;
  --glow: rgb(227 181 98 / .13); color-scheme: dark } }
:root[data-theme="dark"] { --bg: #16111a; --page: #211a26; --ink: #efe6dc; --muted: #ab9db0; --line: #3b2f42;
  --brass: #e3b562; --brass-soft: #34281b; --glow: rgb(227 181 98 / .13); color-scheme: dark }
* { box-sizing: border-box; }
body { background: radial-gradient(120% 60% at 50% 0%, var(--glow), transparent 70%) fixed, var(--bg);
  color: var(--ink); font: 16px/1.6 var(--prose); margin: 0; }
.wrap { max-width: 720px; margin: 0 auto; padding: 24px max(16px, env(safe-area-inset-left, 0px)) 64px; }
h1 { font: 700 1.9rem/1.15 var(--display); letter-spacing: .03em; margin: 0 0 12px; }
h2 { font: 700 1.2rem/1.2 var(--display); letter-spacing: .04em; color: var(--brass); margin: 32px 0 8px;
  border-bottom: 1px solid var(--line); padding-bottom: 4px; }
h3 { font: 700 1.02rem/1.25 var(--display); margin: 22px 0 6px; }
p, li { overflow-wrap: anywhere; }
ul, ol { padding-left: 1.2em; }
li { margin: 4px 0; }
code { font: .82em var(--mono); background: var(--page); border: 1px solid var(--line); border-radius: 4px;
  padding: 0 4px; }
pre { font: .78rem/1.45 var(--mono); background: var(--page); border: 1px solid var(--line);
  border-radius: 10px; padding: 12px; overflow-x: auto; }
pre code { border: 0; padding: 0; background: none; }
table { border-collapse: collapse; width: 100%; font: .84rem/1.45 var(--prose); display: block;
  overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: 6px 8px; vertical-align: top; text-align: left; }
th { background: var(--brass-soft); font-family: var(--display); color: var(--brass); }
blockquote { border-left: 3px solid var(--brass); margin: 0; padding-left: 12px; color: var(--muted); }
a { color: var(--brass); }
.meta { font: .78rem var(--mono); color: var(--muted); margin-bottom: 20px; }
"""


def render(source: Path) -> str:
    text = source.read_text(encoding="utf-8")
    title_match = re.search(r"^# (.+)$", text, re.M)
    title = title_match.group(1).strip() if title_match else source.stem
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(text)
    fonts = (
        "https://fonts.googleapis.com/css2?family=Alegreya+SC:wght@500;700"
        "&family=Spectral:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;600&display=swap"
    )
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"<title>{html.escape(title)}</title>\n"
        '<meta name="description" content="Pantheon document '
        f'{html.escape(source.name)}, rendered from the repo.">\n'
        f'<link rel="stylesheet" href="{fonts}">\n<style>{_STYLE}</style>\n</head>\n<body>\n'
        '<div class="wrap">\n'
        f'<p class="meta">{html.escape(str(source))}</p>\n{body}\n</div>\n</body>\n</html>\n'
    )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    out = Path(argv[2])
    out.write_text(render(Path(argv[1])), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
