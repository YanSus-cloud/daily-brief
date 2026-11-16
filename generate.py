#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日咨询静态站点生成器。

用法：
    python generate.py

每天只需编辑 content.md，然后运行本脚本（或由定时任务自动运行）。
脚本会生成 output/index.html（最新一期）并归档到 output/archive/YYYY-MM-DD.html。
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONTENT_FILE = BASE / "content.md"
OUTPUT_DIR = BASE / "output"
ARCHIVE_DIR = OUTPUT_DIR / "archive"

CSS = """
:root {
  --bg: #f4f6fb;
  --card: #ffffff;
  --ink: #1f2937;
  --muted: #6b7280;
  --accent: #2563eb;
  --line: #e5e7eb;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  line-height: 1.7;
}
.wrap { max-width: 680px; margin: 0 auto; padding: 24px 16px 48px; }
header {
  background: linear-gradient(135deg, #2563eb, #38bdf8);
  color: #ffffff;
  border-radius: 16px;
  padding: 24px 20px;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.18);
}
.badge { font-size: 11px; letter-spacing: 2px; opacity: 0.85; }
h1 { margin: 6px 0 4px; font-size: 22px; }
.date { margin: 0; font-size: 13px; opacity: 0.92; }
main { margin-top: 18px; }
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.card h2 {
  margin: 0 0 10px;
  font-size: 16px;
  color: var(--accent);
  border-left: 3px solid var(--accent);
  padding-left: 8px;
}
ul { margin: 0; padding-left: 20px; }
li { margin: 6px 0; }
li a { color: var(--accent); text-decoration: none; }
li a:hover { text-decoration: underline; }
.para { margin: 8px 0; font-size: 14px; color: #374151; }
.note {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 13px;
}
.recent {
  margin-top: 20px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 18px;
  font-size: 13px;
}
.recent strong { color: var(--muted); }
.recent div { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px; }
.recent a {
  color: var(--accent);
  text-decoration: none;
  background: #eff6ff;
  border-radius: 8px;
  padding: 4px 10px;
}
.foot { text-align: center; color: var(--muted); font-size: 12px; margin-top: 22px; }
"""


def parse_content(raw: str):
    """解析极简 Markdown：# 主标题 / ## 章节 / - 要点 / > 备注 / 普通行＝段落。"""
    title = "每日咨询"
    sections: list[dict] = []
    notes: list[str] = []
    current: dict | None = None
    first_h1 = True

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# ") and first_h1:
            title = line[2:].strip()
            first_h1 = False
        elif line.startswith("## "):
            current = {"title": line[3:].strip(), "items": []}
            sections.append(current)
        elif line.startswith("- ") or line.startswith("* "):
            if current is not None:
                text = line[2:].strip()
                # 支持 [标题](链接) 语法，渲染成可点击的链接
                m = re.match(r"^\[(.*?)\]\((.*?)\)$", text)
                if m:
                    current["items"].append(
                        {"type": "link", "text": m.group(1), "url": m.group(2)}
                    )
                else:
                    current["items"].append({"type": "list", "text": text})
        elif line.startswith(">"):
            notes.append(line.lstrip("> ").strip())
        else:
            if current is not None:
                current["items"].append({"type": "para", "text": line})

    return title, sections, notes


def render_body(sections: list[dict], notes: list[str]) -> str:
    parts: list[str] = []
    for sec in sections:
        li_parts: list[str] = []
        for i in sec["items"]:
            if i["type"] == "list":
                li_parts.append(f"<li>{html.escape(i['text'])}</li>")
            elif i["type"] == "link":
                li_parts.append(
                    f"<li><a href='{html.escape(i['url'], quote=True)}' "
                    f"target='_blank' rel='noopener'>{html.escape(i['text'])}</a></li>"
                )
        lis = "".join(li_parts)
        paras = "".join(
            f"<p class='para'>{html.escape(i['text'])}</p>"
            for i in sec["items"]
            if i["type"] == "para"
        )
        parts.append(
            "<section class='card'>"
            f"<h2>{html.escape(sec['title'])}</h2>"
            f"<ul>{lis}</ul>{paras}"
            "</section>"
        )
    if notes:
        note_html = "<br>".join(html.escape(n) for n in notes)
        parts.append(f"<aside class='note'>{note_html}</aside>")
    return "\n".join(parts)


def render_recent() -> str:
    """首页底部展示最近 7 期归档链接。"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dates: list[date] = []
    for p in ARCHIVE_DIR.glob("*.html"):
        try:
            dates.append(date.fromisoformat(p.stem))
        except ValueError:
            continue
    dates = sorted(set(dates), reverse=True)[:7]
    if not dates:
        return ""
    links = "".join(
        f"<a href='archive/{d.isoformat()}.html'>{d.strftime('%m-%d')}</a>"
        for d in dates
    )
    return f"<footer class='recent'><strong>往期回顾</strong><div>{links}</div></footer>"


def main() -> None:
    if not CONTENT_FILE.exists():
        raise SystemExit(f"找不到内容文件：{CONTENT_FILE}")

    title, sections, notes = parse_content(
        CONTENT_FILE.read_text(encoding="utf-8")
    )
    # GitHub Actions 服务器是 UTC 时区，这里固定用北京时间（UTC+8）
    today = datetime.now(timezone(timedelta(hours=8))).date()
    date_str = today.strftime("%Y-%m-%d")
    date_cn = today.strftime("%Y年%m月%d日")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    body = render_body(sections, notes)
    recent = render_recent()

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · {date_str}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="badge">DAILY BRIEF</div>
    <h1>{html.escape(title)}</h1>
    <p class="date">{date_cn} · 每日更新</p>
  </header>
  <main>
{body}
  </main>
  {recent}
  <p class="foot">本页内容每日更新，收藏链接即可持续查看 · 生成于 {date_str}</p>
</div>
</body>
</html>
"""

    index_path = OUTPUT_DIR / "index.html"
    archive_path = ARCHIVE_DIR / f"{date_str}.html"
    index_path.write_text(page, encoding="utf-8")

    # 归档页位于 archive/ 子目录，去掉"往期回顾"避免相对链接错位
    archive_page = page.replace(recent, "") if recent else page
    archive_path.write_text(archive_page, encoding="utf-8")

    print(f"已生成：{index_path}")
    print(f"已归档：{archive_path}")
    print("下一步：把 output 目录整体上传到静态托管（GitHub Pages / Gitee Pages 等）")


if __name__ == "__main__":
    main()
