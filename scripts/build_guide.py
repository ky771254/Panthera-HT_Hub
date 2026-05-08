from __future__ import annotations

import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parent.parent
GUIDE_CONFIGS = {
    "zh": {
        "source": ROOT / "guide.md",
        "target": ROOT / "guide.html",
        "lang": "zh-CN",
        "title": "Panthera-HT SDK 目录结构说明",
        "font_link": (
            "https://fonts.googleapis.com/css2?"
            "family=Outfit:wght@400;500;600;700&"
            "family=Noto+Sans+SC:wght@400;500;700&display=swap"
        ),
        "body_font": '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
        "mobile_open": "查看章节目录",
        "mobile_close": "收起章节目录",
        "toc_aria_label": "文档目录",
        "expand_children": "展开子章节",
        "collapse_children": "收起子章节",
    },
    "en": {
        "source": ROOT / "guide_en.md",
        "target": ROOT / "guide_en.html",
        "lang": "en",
        "title": "Panthera-HT SDK Guide",
        "font_link": (
            "https://fonts.googleapis.com/css2?"
            "family=Inter:wght@400;500;600;700&"
            "family=Outfit:wght@400;500;600;700&display=swap"
        ),
        "body_font": '"Inter", "Segoe UI", sans-serif',
        "mobile_open": "View Contents",
        "mobile_close": "Hide Contents",
        "toc_aria_label": "Table of contents",
        "expand_children": "Expand subsection",
        "collapse_children": "Collapse subsection",
    },
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


def strip_tags(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value)
    return parser.get_text()


MATH_PH = "@@MATH__"


def protect_math(text: str) -> tuple[str, list[str]]:
    """Replace $..$ / $$..$$ with safe placeholders so markdown-it doesn't mangle underscores."""
    exprs: list[str] = []

    def unescape(s: str) -> str:
        return s.replace(r"\_", "_").replace(r"\[", "[").replace(r"\]", "]")

    def repl(m: re.Match[str]) -> str:
        exprs.append(unescape(m.group(1)))
        return f"{MATH_PH}{len(exprs) - 1}__"

    text = re.sub(r"\$\$(.+?)\$\$", repl, text, flags=re.DOTALL)
    text = re.sub(r"\$(.+?)\$", repl, text)
    return text, exprs


def restore_math(html: str, exprs: list[str]) -> str:
    """Restore placeholders as \\(...\\) for KaTeX auto-render."""
    for i, expr in enumerate(exprs):
        html = html.replace(f"{MATH_PH}{i}__", f"\\({expr}\\)")
    return html


def build_heading_tree(headings: list[dict[str, str | int]]) -> list[dict[str, object]]:
    roots: list[dict[str, object]] = []
    stack: list[dict[str, object]] = []

    for item in headings:
        node: dict[str, object] = {
            "id": item["id"],
            "level": item["level"],
            "label": item["label"],
            "children": [],
        }

        while stack and int(stack[-1]["level"]) >= int(node["level"]):
            stack.pop()

        if stack:
            children = stack[-1]["children"]
            assert isinstance(children, list)
            children.append(node)
        else:
            roots.append(node)

        stack.append(node)

    return roots


def render_sidebar_nodes(
    nodes: list[dict[str, object]],
    labels: dict[str, str | Path],
    depth: int = 0,
) -> str:
    parts: list[str] = []

    for node in nodes:
        node_id = str(node["id"])
        level = int(node["level"])
        label = html.escape(str(node["label"]))
        children = node["children"]
        assert isinstance(children, list)
        has_children = bool(children)
        node_class = "toc-node" if has_children else "toc-node"

        toggle = ""
        if has_children:
            toggle = (
                f'<button class="toc-toggle" type="button" aria-expanded="false" '
                f'aria-controls="{node_id}-children" aria-label="{labels["expand_children"]}">'
                '<span class="toc-toggle-icon" aria-hidden="true"></span>'
                "</button>"
            )

        row = (
            f'<div class="toc-row">'
            f'<a class="toc-link toc-level-{level}" href="#{node_id}">{label}</a>'
            f"{toggle}"
            "</div>"
        )

        children_html = ""
        if has_children:
            children_html = (
                f'<div class="toc-children" id="{node_id}-children">'
                f"{render_sidebar_nodes(children, labels, depth + 1)}"
                "</div>"
            )

        parts.append(
            f'                <div class="{node_class}" data-depth="{depth}" data-level="{level}">'
            f"{row}"
            f"{children_html}"
            "</div>"
        )

    return "\n".join(parts)


def build_page(config: dict[str, str | Path]) -> str:
    source = config["source"]
    assert isinstance(source, Path)
    source_text = source.read_text(encoding="utf-8")
    source_text, math_exprs = protect_math(source_text)
    markdown = MarkdownIt(
        "commonmark",
        {
            "html": False,
            "linkify": False,
            "typographer": False,
        },
    ).enable("table")
    rendered = markdown.render(source_text)

    headings: list[dict[str, str | int]] = []
    heading_index = 0
    prev_heading_level = 0

    def replace_heading(match: re.Match[str]) -> str:
        nonlocal heading_index, prev_heading_level
        level = int(match.group(1))
        inner_html = match.group(2)
        heading_index += 1
        section_id = f"section-{heading_index:03d}"
        headings.append(
            {
                "id": section_id,
                "level": level,
                "label": strip_tags(inner_html),
            }
        )
        result = f'<h{level} id="{section_id}" tabindex="-1">{inner_html}</h{level}>'
        if level == 2 and prev_heading_level not in (0, 1):
            result = "<hr />\n" + result
        prev_heading_level = level
        return result

    article_html = re.sub(
        r"<h([1-6])>(.*?)</h\1>",
        replace_heading,
        rendered,
        flags=re.S,
    )
    article_html = restore_math(article_html, math_exprs)

    sidebar_links = render_sidebar_nodes(build_heading_tree(headings), config)

    heading_data = json.dumps(headings, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="{config["lang"]}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config["title"]}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{config["font_link"]}" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
    <style>

        :root {{
            --bg: #f5f7fb;
            --panel: rgba(255, 255, 255, 0.92);
            --panel-strong: #ffffff;
            --ink: #1d2733;
            --muted: #6f7b88;
            --line: rgba(110, 130, 155, 0.16);
            --accent: #7db9f8;
            --accent-soft: rgba(125, 185, 248, 0.18);
            --shadow: 0 18px 36px rgba(82, 110, 144, 0.08);
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            color: var(--ink);
            font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
            background:
                radial-gradient(circle at top left, rgba(255, 255, 255, 0.96), transparent 24%),
                linear-gradient(180deg, #fafcff 0%, #f2f5f9 100%);
            transition: background 220ms ease, color 220ms ease;
        }}

        a {{
            color: inherit;
        }}

        .docs-shell {{
            max-width: 1440px;
            margin: 0 auto;
            padding: 24px;
            display: grid;
            grid-template-columns: 360px minmax(0, 1fr);
            gap: 24px;
        }}

        .sidebar {{
            position: sticky;
            top: 24px;
            align-self: start;
            max-height: calc(100vh - 48px);
            overflow: auto;
            border: 1px solid var(--line);
            border-radius: 28px;
            background: var(--panel);
            box-shadow: var(--shadow);
            padding: 22px 18px 20px;
            overflow-x: hidden;
            scrollbar-width: none;
            -ms-overflow-style: none;
        }}

        .sidebar::-webkit-scrollbar {{
            width: 0;
            height: 0;
            display: none;
        }}

        .toc {{
            position: relative;
            display: flex;
            flex-direction: column;
            gap: 8px;
            min-width: 0;
        }}

        .toc-active-indicator {{
            position: absolute;
            top: 0;
            left: 0;
            width: 0;
            height: 0;
            border-radius: 14px;
            background: var(--accent-soft);
            opacity: 0;
            pointer-events: none;
            z-index: 0;
            transition:
                transform 260ms cubic-bezier(0.22, 1, 0.36, 1),
                width 260ms cubic-bezier(0.22, 1, 0.36, 1),
                height 260ms cubic-bezier(0.22, 1, 0.36, 1),
                opacity 180ms ease;
        }}

        .toc-node {{
            min-width: 0;
        }}

        .toc-row {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            min-width: 0;
        }}

        .toc-link {{
            position: relative;
            display: block;
            flex: 1;
            min-width: 0;
            padding: 8px 12px;
            border-radius: 14px;
            color: #526170;
            text-decoration: none;
            line-height: 1.45;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
            z-index: 1;
            transition: color 180ms ease;
        }}

        .toc-link:hover {{
            background: rgba(255, 255, 255, 0.96);
            color: var(--ink);
        }}

        .toc-link:focus-visible {{
            outline: 2px solid rgba(125, 185, 248, 0.75);
            outline-offset: 2px;
            background: rgba(255, 255, 255, 0.98);
        }}

        .toc-link.is-active {{
            background: transparent;
            color: #2e6fab;
            font-weight: 700;
        }}

        .toc-level-1 {{
            font-weight: 700;
            font-size: 14px;
        }}

        .toc-level-2 {{
            font-size: 13px;
        }}

        .toc-level-3,
        .toc-level-4,
        .toc-level-5,
        .toc-level-6 {{
            font-size: 13px;
            color: #7c8894;
        }}

        .toc-toggle {{
            position: relative;
            width: 18px;
            height: 18px;
            margin-top: 9px;
            flex: 0 0 auto;
            border: 0;
            padding: 0;
            background: transparent;
            color: #5f8fbe;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1;
        }}

        .toc-toggle:hover {{
            color: #2e6fab;
        }}

        .toc-toggle-icon {{
            width: 8px;
            height: 8px;
            border-right: 2px solid currentColor;
            border-bottom: 2px solid currentColor;
            transform: rotate(45deg) translateY(-1px);
        }}

        .toc-node.is-open > .toc-row .toc-toggle-icon {{
            transform: rotate(45deg) translateY(-1px);
        }}

        .toc-node:not(.is-open) > .toc-row .toc-toggle-icon {{
            transform: rotate(-45deg) translate(-1px, 1px);
        }}

        .toc-children {{
            margin: 6px 0 0 14px;
            padding-left: 10px;
            border-left: 1px solid rgba(125, 185, 248, 0.18);
            display: block;
            min-width: 0;
            overflow: hidden;
            height: 0;
            opacity: 0;
            transition:
                height 240ms cubic-bezier(0.22, 1, 0.36, 1),
                opacity 180ms ease;
        }}

        .toc-node.is-open > .toc-children {{
            opacity: 1;
        }}

        .content-wrap {{
            min-width: 0;
        }}

        .content-card {{
            border: 1px solid var(--line);
            border-radius: 32px;
            background: var(--panel-strong);
            box-shadow: var(--shadow);
            padding: 42px 48px 56px;
        }}

        .doc-body {{
            min-width: 0;
        }}

        .doc-body > :first-child {{
            margin-top: 0;
        }}

        .doc-body h1,
        .doc-body h2,
        .doc-body h3,
        .doc-body h4,
        .doc-body h5,
        .doc-body h6 {{
            scroll-margin-top: 24px;
            color: #1d2733;
            line-height: 1.25;
        }}

        .doc-body h1 {{
            margin: 1.8em 0 0.7em;
            font-size: clamp(30px, 3vw, 42px);
            font-family: "Outfit", "Noto Sans SC", sans-serif;
        }}

        .doc-body h2 {{
            margin: 1.9em 0 0.8em;
            font-size: clamp(24px, 2.4vw, 32px);
        }}

        .doc-body h3 {{
            margin: 1.7em 0 0.75em;
            font-size: clamp(20px, 2vw, 24px);
        }}

        .doc-body h4,
        .doc-body h5,
        .doc-body h6 {{
            margin: 1.4em 0 0.65em;
            font-size: 18px;
        }}

        .doc-body p,
        .doc-body li,
        .doc-body blockquote {{
            font-size: 16px;
            line-height: 1.5;
        }}

        .doc-body p,
        .doc-body ul,
        .doc-body ol,
        .doc-body blockquote,
        .doc-body pre,
        .doc-body table,
        .doc-body hr {{
            margin: 0 0 1.2em;
        }}

        .doc-body ul,
        .doc-body ol {{
            padding-left: 1.5em;
        }}

        .doc-body li + li {{
            margin-top: 0.35em;
        }}

        .doc-body code {{
            font-family: "SFMono-Regular", "Consolas", "Liberation Mono", monospace;
            font-size: 0.94em;
            background: #eef4fb;
            border-radius: 6px;
            padding: 0.18em 0.36em;
        }}

        .doc-body pre {{
            overflow: auto;
            padding: 18px 20px;
            border-radius: 20px;
            background: #f4f7fb;
            color: #294056;
            border: 1px solid rgba(125, 185, 248, 0.18);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
        }}

        .doc-body pre code {{
            padding: 0;
            border-radius: 0;
            background: transparent;
            color: inherit;
            font-size: 14px;
            line-height: 1.7;
        }}

        .doc-body blockquote {{
            margin-left: 0;
            padding: 14px 18px;
            border-left: 4px solid var(--accent);
            background: #f4f8fd;
            color: #4f6377;
            border-radius: 0 16px 16px 0;
        }}

        .doc-body hr {{
            border: 0;
            border-top: 1px solid rgba(30, 31, 26, 0.1);
        }}

        .doc-body table {{
            width: 100%;
            border-collapse: collapse;
            overflow: hidden;
            border-radius: 18px;
            border: 1px solid rgba(30, 31, 26, 0.1);
            display: block;
            overflow-x: auto;
        }}

        .doc-body thead {{
            background: #edf4fb;
        }}

        .doc-body th,
        .doc-body td {{
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid rgba(30, 31, 26, 0.08);
            vertical-align: top;
            min-width: 160px;
        }}

        .doc-body tr:last-child td {{
            border-bottom: 0;
        }}

        .doc-body strong {{
            color: #1c2630;
        }}

        .mobile-sidebar-toggle {{
            display: none;
            width: 100%;
            margin-bottom: 14px;
            padding: 12px 14px;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.96);
            color: var(--ink);
            font-size: 15px;
            font-weight: 700;
            text-align: left;
        }}

        .theme-toggle {{
            position: fixed;
            top: 20px;
            right: 24px;
            z-index: 30;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 11px;
            border: 1px solid var(--line);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.9);
            color: var(--ink);
            box-shadow: 0 12px 28px rgba(82, 110, 144, 0.12);
            backdrop-filter: blur(14px);
            cursor: pointer;
            transition: background 180ms ease, border-color 180ms ease, transform 180ms ease, color 180ms ease;
        }}

        .theme-toggle:hover {{
            transform: translateY(-1px);
        }}

        .theme-toggle:focus-visible {{
            outline: 2px solid rgba(125, 185, 248, 0.75);
            outline-offset: 2px;
        }}

        .theme-toggle-knob {{
            width: 32px;
            height: 18px;
            border-radius: 999px;
            background: rgba(125, 185, 248, 0.22);
            position: relative;
            flex: 0 0 auto;
        }}

        .theme-toggle-knob::after {{
            content: "";
            position: absolute;
            top: 2px;
            left: 2px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #7db9f8;
            transition: transform 220ms cubic-bezier(0.22, 1, 0.36, 1), background 180ms ease;
        }}

        .theme-toggle-label {{
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.02em;
        }}

        html[data-theme="dark"] body {{
            color: #e8ebef;
            background: #1C1C1C;
        }}

        html[data-theme="dark"] .sidebar,
        html[data-theme="dark"] .content-card,
        html[data-theme="dark"] .mobile-sidebar-toggle {{
            background: #212121;
            border-color: rgba(255, 255, 255, 0.08);
            box-shadow: 0 22px 44px rgba(0, 0, 0, 0.34);
        }}

        html[data-theme="dark"] .theme-toggle {{
            background: #1b1f24;
            color: #eef1f5;
            border-color: rgba(255, 255, 255, 0.08);
            box-shadow: 0 14px 28px rgba(0, 0, 0, 0.4);
        }}

        html[data-theme="dark"] .theme-toggle-knob {{
            background: rgba(125, 185, 248, 0.22);
        }}

        html[data-theme="dark"] .theme-toggle-knob::after {{
            transform: translateX(14px);
            background: #7db9f8;
        }}

        html[data-theme="dark"] .toc-link {{
            color: #c9d0d8;
        }}

        html[data-theme="dark"] .toc-link:hover,
        html[data-theme="dark"] .toc-link:focus-visible {{
            background: rgba(255, 255, 255, 0.06);
            color: #f3f5f7;
            outline-color: rgba(125, 185, 248, 0.75);
        }}

        html[data-theme="dark"] .toc-link.is-active {{
            color: #9fd0ff;
        }}

        html[data-theme="dark"] .toc-level-3,
        html[data-theme="dark"] .toc-level-4,
        html[data-theme="dark"] .toc-level-5,
        html[data-theme="dark"] .toc-level-6 {{
            color: #9ca6b1;
        }}

        html[data-theme="dark"] .toc-toggle {{
            color: #7db9f8;
        }}

        html[data-theme="dark"] .toc-toggle:hover {{
            color: #9fd0ff;
        }}

        html[data-theme="dark"] .toc-active-indicator {{
            background: rgba(125, 185, 248, 0.18);
        }}

        html[data-theme="dark"] .doc-body h1,
        html[data-theme="dark"] .doc-body h2,
        html[data-theme="dark"] .doc-body h3,
        html[data-theme="dark"] .doc-body h4,
        html[data-theme="dark"] .doc-body h5,
        html[data-theme="dark"] .doc-body h6,
        html[data-theme="dark"] .doc-body strong {{
            color: #f3f5f7;
        }}

        html[data-theme="dark"] .doc-body p,
        html[data-theme="dark"] .doc-body li,
        html[data-theme="dark"] .doc-body blockquote,
        html[data-theme="dark"] .doc-body td,
        html[data-theme="dark"] .doc-body th {{
            color: #d9dee5;
        }}

        html[data-theme="dark"] .doc-body code {{
            background: #232830;
            color: #eef1f5;
        }}

        html[data-theme="dark"] .doc-body pre {{
            /* background: #232830; */
            background: #232830;
            color: #e8ebef;
            border-color: rgba(255, 255, 255, 0.08);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }}

        html[data-theme="dark"] .doc-body blockquote {{
            background: #20252c;
            color: #d9dee5;
            border-left-color: rgba(255, 255, 255, 0.2);
        }}

        html[data-theme="dark"] .doc-body hr {{
            border-top-color: rgba(255, 255, 255, 0.1);
        }}

        html[data-theme="dark"] .doc-body table {{
            border-color: rgba(255, 255, 255, 0.1);
        }}

        html[data-theme="dark"] .doc-body thead {{
            background: #232830;
        }}

        html[data-theme="dark"] .doc-body th,
        html[data-theme="dark"] .doc-body td {{
            border-bottom-color: rgba(255, 255, 255, 0.08);
        }}

        @media (max-width: 1080px) {{
            .docs-shell {{
                grid-template-columns: 1fr;
            }}

            .sidebar {{
                position: static;
                max-height: none;
                display: none;
            }}

            .sidebar.is-open {{
                display: block;
            }}

            .mobile-sidebar-toggle {{
                display: block;
            }}
        }}

        @media (max-width: 720px) {{
            .docs-shell {{
                padding: 18px;
            }}

            .theme-toggle {{
                top: 14px;
                right: 18px;
                padding: 8px 10px;
            }}

            .content-card {{
                padding: 28px 22px 40px;
                border-radius: 24px;
            }}

            .doc-body p,
            .doc-body li,
            .doc-body blockquote {{
                font-size: 15px;
            }}
        }}
    </style>
</head>
<body>
    <button class="theme-toggle" type="button" aria-pressed="false">
    </button>
    <main class="docs-shell">
        <button class="mobile-sidebar-toggle" type="button" aria-expanded="false" aria-controls="guide-sidebar">{config["mobile_open"]}</button>
        <aside class="sidebar" id="guide-sidebar">
            <nav class="toc" aria-label="{config["toc_aria_label"]}">
                <div class="toc-active-indicator" aria-hidden="true"></div>
{sidebar_links}
            </nav>
        </aside>

        <section class="content-wrap">
            <article class="content-card">
                <div class="doc-body">
{article_html}
                </div>
            </article>
        </section>
    </main>

    <script>
        const headingMeta = {heading_data};
        const sidebar = document.getElementById("guide-sidebar");
        const toggle = document.querySelector(".mobile-sidebar-toggle");
        const tocLinks = Array.from(document.querySelectorAll(".toc-link"));
        const treeToggles = Array.from(document.querySelectorAll(".toc-toggle"));

        if (toggle && sidebar) {{
            toggle.addEventListener("click", () => {{
                const opened = sidebar.classList.toggle("is-open");
                toggle.setAttribute("aria-expanded", String(opened));
                toggle.textContent = opened ? "{config["mobile_close"]}" : "{config["mobile_open"]}";
            }});

            tocLinks.forEach((link) => {{
                link.addEventListener("click", () => {{
                    if (window.innerWidth <= 1080) {{
                        sidebar.classList.remove("is-open");
                        toggle.setAttribute("aria-expanded", "false");
                        toggle.textContent = "{config["mobile_open"]}";
                    }}
                }});
            }});
        }}

        treeToggles.forEach((button) => {{
            button.addEventListener("click", (event) => {{
                event.preventDefault();
                event.stopPropagation();
                const node = button.closest(".toc-node");
                if (!node) {{
                    return;
                }}

                const opened = node.classList.toggle("is-open");
                button.setAttribute("aria-expanded", String(opened));
                button.setAttribute("aria-label", opened ? "{config["collapse_children"]}" : "{config["expand_children"]}");
            }});
        }});

        const sectionIds = headingMeta.map((item) => item.id);
        const sections = sectionIds
            .map((id) => document.getElementById(id))
            .filter(Boolean);
        let activeSectionId = "";

        const headingMeta = Array.from(
            document.querySelectorAll(".doc-body h1[id], .doc-body h2[id], .doc-body h3[id], .doc-body h4[id], .doc-body h5[id], .doc-body h6[id]")
        ).map((heading) => ({{
            id: heading.id,
            label: heading.textContent ? heading.textContent.trim() : "",
        }}));
        const root = document.documentElement;
        const sidebar = document.getElementById("guide-sidebar");
        const toc = document.querySelector(".toc");
        const activeIndicator = document.querySelector(".toc-active-indicator");
        const themeToggle = document.querySelector(".theme-toggle");
        const themeToggleLabel = document.querySelector(".theme-toggle-label");
        const toggle = document.querySelector(".mobile-sidebar-toggle");
        const tocLinks = Array.from(document.querySelectorAll(".toc-link"));
        const treeToggles = Array.from(document.querySelectorAll(".toc-toggle"));
        const treeNodes = Array.from(document.querySelectorAll(".toc-node"))
            .filter((node) => node.querySelector(":scope > .toc-children"));

        function applyTheme(theme) {{
            root.dataset.theme = theme;
            if (themeToggle) {{
                themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
            }}
            if (themeToggleLabel) {{
                themeToggleLabel.textContent = theme === "dark" ? "浅色" : "深色";
            }}
        }}

        if (themeToggle) {{
            applyTheme(root.dataset.theme || "light");
            themeToggle.addEventListener("click", () => {{
                const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
                applyTheme(nextTheme);
                try {{
                    localStorage.setItem("panthera-guide-theme", nextTheme);
                }} catch (error) {{
                    // Ignore storage failures and still switch theme for this session.
                }}
            }});
        }}

        function setNodeOpen(node, opened, immediate = false) {{
            if (!node) {{
                return;
            }}

            const children = node.querySelector(":scope > .toc-children");
            const button = node.querySelector(":scope > .toc-row .toc-toggle");
            if (!children) {{
                return;
            }}

            if (button) {{
                button.setAttribute("aria-expanded", String(opened));
                button.setAttribute("aria-label", opened ? "收起子章节" : "展开子章节");
            }}

            if (opened) {{
                node.classList.add("is-open");
                if (immediate) {{
                    children.style.height = "auto";
                    return;
                }}

                children.style.height = "0px";
                void children.offsetHeight;
                children.style.height = `${{children.scrollHeight}}px`;

                const handleOpenEnd = (event) => {{
                    if (event.propertyName !== "height") {{
                        return;
                    }}
                    children.style.height = "auto";
                    children.removeEventListener("transitionend", handleOpenEnd);
                }};

                children.addEventListener("transitionend", handleOpenEnd);
                return;
            }}

            const currentHeight = children.scrollHeight;
            if (immediate) {{
                node.classList.remove("is-open");
                children.style.height = "0px";
                return;
            }}

            children.style.height = `${{currentHeight}}px`;
            void children.offsetHeight;
            node.classList.remove("is-open");
            children.style.height = "0px";
        }}

        function syncTreeHeights() {{
            treeNodes.forEach((node) => {{
                const children = node.querySelector(":scope > .toc-children");
                if (!children) {{
                    return;
                }}

                if (node.classList.contains("is-open")) {{
                    children.style.height = "auto";
                }} else {{
                    children.style.height = "0px";
                }}
            }});
        }}

        if (toggle && sidebar) {{
            toggle.addEventListener("click", () => {{
                const opened = sidebar.classList.toggle("is-open");
                toggle.setAttribute("aria-expanded", String(opened));
                toggle.textContent = opened ? "收起章节目录" : "查看章节目录";
            }});

            tocLinks.forEach((link) => {{
                link.addEventListener("click", () => {{
                    if (window.innerWidth <= 1080) {{
                        sidebar.classList.remove("is-open");
                        toggle.setAttribute("aria-expanded", "false");
                        toggle.textContent = "查看章节目录";
                    }}
                }});
            }});
        }}

        treeToggles.forEach((button) => {{
            button.addEventListener("click", (event) => {{
                event.preventDefault();
                event.stopPropagation();
                const node = button.closest(".toc-node");
                if (!node) {{
                    return;
                }}

                const opened = !node.classList.contains("is-open");
                setNodeOpen(node, opened);
                syncVisibleActiveIndicator();
            }});
        }});

        syncTreeHeights();

        const sectionIds = headingMeta.map((item) => item.id);
        const sections = sectionIds
            .map((id) => document.getElementById(id))
            .filter(Boolean);
        let activeSectionId = "";

        function expandAncestorNodes(link) {{
            let parent = link.closest(".toc-children");
            while (parent) {{
                const owner = parent.parentElement;
                if (owner && owner.classList.contains("toc-node")) {{
                    setNodeOpen(owner, true, true);
                }}
                parent = owner ? owner.closest(".toc-children") : null;
            }}
        }}

        function syncSidebarScroll(link) {{
            if (!sidebar || !link || window.innerWidth <= 1080) {{
                return;
            }}

            const sidebarRect = sidebar.getBoundingClientRect();
            const linkRect = link.getBoundingClientRect();
            const margin = 24;
            const hiddenAbove = linkRect.top < sidebarRect.top + margin;
            const hiddenBelow = linkRect.bottom > sidebarRect.bottom - margin;

            if (hiddenAbove || hiddenBelow) {{
                const targetTop =
                    link.offsetTop - sidebar.clientHeight / 2 + link.clientHeight / 2;
                const maxScrollTop = sidebar.scrollHeight - sidebar.clientHeight;
                const nextScrollTop = Math.max(0, Math.min(targetTop, maxScrollTop));
                sidebar.scrollTo({{ top: nextScrollTop, behavior: "smooth" }});
            }}
        }}

        function syncActiveIndicator(link) {{
            if (!toc || !activeIndicator || !link || window.innerWidth <= 1080) {{
                if (activeIndicator) {{
                    activeIndicator.style.opacity = "0";
                }}
                return;
            }}

            const tocRect = toc.getBoundingClientRect();
            const linkRect = link.getBoundingClientRect();
            const top = linkRect.top - tocRect.top + toc.scrollTop;
            const left = linkRect.left - tocRect.left + toc.scrollLeft;

            activeIndicator.style.width = `${{linkRect.width}}px`;
            activeIndicator.style.height = `${{linkRect.height}}px`;
            activeIndicator.style.transform = `translate(${{left}}px, ${{top}}px)`;
            activeIndicator.style.opacity = "1";
        }}

        function getVisibleActiveLink() {{
            const activeLink = tocLinks.find((link) => link.classList.contains("is-active"));
            if (!activeLink) {{
                return null;
            }}

            let visibleLink = activeLink;
            let parent = activeLink.closest(".toc-children");

            while (parent) {{
                const owner = parent.parentElement;
                if (owner && owner.classList.contains("toc-node") && !owner.classList.contains("is-open")) {{
                    const ownerLink = owner.querySelector(":scope > .toc-row .toc-link");
                    if (ownerLink) {{
                        visibleLink = ownerLink;
                    }}
                }}
                parent = owner ? owner.closest(".toc-children") : null;
            }}

            return visibleLink;
        }}

        function syncVisibleActiveIndicator() {{
            syncActiveIndicator(getVisibleActiveLink());
        }}

        function setActiveLink(id) {{
            if (!id || id === activeSectionId) {{
                return;
            }}

            activeSectionId = id;
            tocLinks.forEach((link) => {{
                const active = link.getAttribute("href") === `#${{id}}`;
                link.classList.toggle("is-active", active);
                if (active) {{
                    expandAncestorNodes(link);
                    syncSidebarScroll(link);
                    syncVisibleActiveIndicator();
                }}
            }});
        }}

        function updateActiveSectionFromScroll() {{
            if (!sections.length) {{
                return;
            }}

            const offset = 120;
            const scrollMarker = window.scrollY + offset;
            let current = sections[0];

            for (const section of sections) {{
                if (section.offsetTop <= scrollMarker) {{
                    current = section;
                }} else {{
                    break;
                }}
            }}

            setActiveLink(current.id);
        }}

        window.addEventListener("scroll", updateActiveSectionFromScroll, {{ passive: true }});
        window.addEventListener("load", updateActiveSectionFromScroll);
        window.addEventListener("resize", () => {{
            syncTreeHeights();
            const activeLink = getVisibleActiveLink();
            if (activeLink) {{
                syncActiveIndicator(activeLink);
            }}
        }});

        if (location.hash) {{
            const current = document.getElementById(location.hash.slice(1));
            if (current) {{
                setActiveLink(current.id);
            }}
        }}
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function () {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: '\\\\(', right: '\\\\)', display: false}},
                    {{left: '\\\\[', right: '\\\\]', display: true}}
                ],
                throwOnError: false
            }});
        }});
    </script>
</body>
</html>
"""


def main() -> None:
    locale = sys.argv[1] if len(sys.argv) > 1 else "zh"
    if locale not in GUIDE_CONFIGS:
        raise SystemExit(f"Unsupported locale: {locale}")

    config = GUIDE_CONFIGS[locale]
    target = config["target"]
    assert isinstance(target, Path)
    target.write_text(build_page(config), encoding="utf-8")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
