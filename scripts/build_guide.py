from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Panthera-HT SDK 目录结构说明及技术说明.md"
TARGET = ROOT / "guide.html"


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


def render_sidebar_nodes(nodes: list[dict[str, object]], depth: int = 0) -> str:
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
                f'aria-controls="{node_id}-children" aria-label="展开子章节">'
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
                f"{render_sidebar_nodes(children, depth + 1)}"
                "</div>"
            )

        parts.append(
            f'                <div class="{node_class}" data-depth="{depth}" data-level="{level}">'
            f"{row}"
            f"{children_html}"
            "</div>"
        )

    return "\n".join(parts)


def build_page() -> str:
    source_text = SOURCE.read_text(encoding="utf-8")
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

    def replace_heading(match: re.Match[str]) -> str:
        nonlocal heading_index
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
        return f'<h{level} id="{section_id}" tabindex="-1">{inner_html}</h{level}>'

    article_html = re.sub(
        r"<h([1-6])>(.*?)</h\1>",
        replace_heading,
        rendered,
        flags=re.S,
    )

    sidebar_links = render_sidebar_nodes(build_heading_tree(headings))

    heading_data = json.dumps(headings, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panthera-HT 指南</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
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
            display: flex;
            flex-direction: column;
            gap: 8px;
            min-width: 0;
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
            background: var(--accent-soft);
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
        }}

        .toc-node:not(.is-open) > .toc-children {{
            display: none;
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
            padding-top: 0.1em;
            font-size: clamp(24px, 2.4vw, 32px);
            border-top: 1px solid rgba(30, 31, 26, 0.08);
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
            line-height: 1.9;
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
    <main class="docs-shell">
        <button class="mobile-sidebar-toggle" type="button" aria-expanded="false" aria-controls="guide-sidebar">查看章节目录</button>
        <aside class="sidebar" id="guide-sidebar">
            <nav class="toc" aria-label="文档目录">
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

                const opened = node.classList.toggle("is-open");
                button.setAttribute("aria-expanded", String(opened));
                button.setAttribute("aria-label", opened ? "收起子章节" : "展开子章节");
            }});
        }});

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
                    owner.classList.add("is-open");
                    const button = owner.querySelector(":scope > .toc-row .toc-toggle");
                    if (button) {{
                        button.setAttribute("aria-expanded", "true");
                        button.setAttribute("aria-label", "收起子章节");
                    }}
                }}
                parent = owner ? owner.closest(".toc-children") : null;
            }}
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

        if (location.hash) {{
            const current = document.getElementById(location.hash.slice(1));
            if (current) {{
                setActiveLink(current.id);
            }}
        }}
    </script>
</body>
</html>
"""


def main() -> None:
    TARGET.write_text(build_page(), encoding="utf-8")
    print(f"Wrote {TARGET}")


if __name__ == "__main__":
    main()
