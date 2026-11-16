#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 RSS / Atom 源抓取最新内容，自动生成 content.md。

用法：
    python fetch_content.py

源地址在 sources.json 里配置。只用 Python 标准库，GitHub Actions 无需额外安装依赖。
"""

from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG_FILE = BASE / "sources.json"
CONTENT_FILE = BASE / "content.md"

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def clean(text: str | None, limit: int) -> str:
    """去掉 HTML 标签与多余空白，并截断到指定长度。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _loose_parse(text: str) -> ET.Element:
    """当 XML 严格解析失败时的兜底：正则抽取条目，构造成临时 XML。"""
    entries: list[str] = []
    for block in re.findall(r"<(item|entry)\b.*?</\1>", text, re.DOTALL):
        def grab(tag: str) -> str:
            m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", block, re.DOTALL)
            return m.group(1) if m else ""

        title = clean(grab("title"), 80)
        link_m = re.search(r"<link\b[^>]*>(.*?)</link>", block, re.DOTALL)
        link = clean(link_m.group(1), 200) if link_m else ""
        if not link:
            link_m = re.search(r'<link\b[^>]*href=["\']([^"\']+)', block)
            link = link_m.group(1) if link_m else ""
        summary = clean(grab("description") or grab("summary"), 100)
        entries.append(
            f"<item><title>{html_escape(title)}</title>"
            f"<link>{html_escape(link)}</link>"
            f"<description>{html_escape(summary)}</description></item>"
        )
    return ET.fromstring(f"<rss><channel>{''.join(entries)}</channel></rss>")


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fetch_feed(url: str, limit: int) -> list[dict]:
    """抓取一个 RSS / Atom 源，返回条目列表。"""
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; DailyBrief/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()

    # 部分源的 XML 含非法控制字符或未转义的 &，先清洗再解析
    text = data.decode("utf-8", errors="ignore")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"&(?!#\d+;|#x[0-9a-fA-F]+;|[a-zA-Z]+;)", "&amp;", text)
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        # 兜底：用正则直接抽取 item/entry，容忍不规范 XML
        root = _loose_parse(text)

    # RSS 2.0 用 <item>，Atom 用 <entry>
    items = root.findall(".//item")
    is_atom = False
    if not items:
        items = root.findall(".//atom:entry", ATOM_NS)
        is_atom = True

    results: list[dict] = []
    for item in items[:limit]:
        if is_atom:
            title = item.findtext("atom:title", default="", namespaces=ATOM_NS)
            link_el = item.find("atom:link", ATOM_NS)
            link = link_el.get("href", "") if link_el is not None else ""
            summary = item.findtext("atom:summary", default="", namespaces=ATOM_NS)
        else:
            title = item.findtext("title", default="")
            link = item.findtext("link", default="")
            summary = item.findtext("description", default="")

        results.append(
            {
                "title": clean(title, 80),
                "link": (link or "").strip(),
                "summary": clean(summary, 100),
            }
        )
    return results


def fetch_html(url: str, limit: int, keywords: list[str] | None = None,
               url_prefix: str = "") -> list[dict]:
    """抓取普通网页的新闻/政策列表：提取 <a> 标题+链接，按关键词过滤。

    用于没有 RSS 的政府网站。keywords 为空则取所有较长链接。
    url_prefix 用于把相对链接补全成绝对地址。
    """
    from urllib.parse import urljoin

    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; DailyBrief/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        page = resp.read().decode("utf-8", errors="ignore")

    results: list[dict] = []
    seen: set[str] = set()
    for href, raw in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
                                page, re.DOTALL):
        title = clean(raw, 80)
        if len(title) < 10:
            continue
        if keywords and not any(kw in title for kw in keywords):
            continue
        if title in seen:
            continue
        seen.add(title)
        full = urljoin(url_prefix or url, href)
        results.append({"title": title, "link": full, "summary": ""})
        if len(results) >= limit:
            break
    return results


def main() -> None:
    if not CONFIG_FILE.exists():
        raise SystemExit(f"找不到配置文件：{CONFIG_FILE}")

    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    lines = ["# 每日咨询 · 自动抓取", ""]

    for source in cfg.get("sources", []):
        lines.append(f"## {source.get('name', '资讯')}")
        url = source.get("url", "")
        limit = int(source.get("limit", 3))
        if not url or "example.com" in url:
            lines.append("- 源地址尚未配置，请在 sources.json 中填写真实地址")
        else:
            try:
                stype = source.get("type", "rss")
                if stype == "html":
                    items = fetch_html(
                        url,
                        limit,
                        keywords=source.get("keywords") or None,
                        url_prefix=source.get("url_prefix", ""),
                    )
                else:
                    items = fetch_feed(url, limit)
                for item in items:
                    title = item["title"] or "（无标题）"
                    if item["link"]:
                        lines.append(f"- [{title}]({item['link']})")
                    else:
                        lines.append(f"- {title}")
                    if item["summary"]:
                        lines.append(f"  {item['summary']}")
            except Exception as exc:  # 单个源失败不影响整体
                lines.append(f"- 抓取失败：{type(exc).__name__}: {exc}")
        lines.append("")

    note = cfg.get("note", "以上内容自动抓取自公开信息源，仅供参考，具体以官方发布为准。")
    lines.append(f"> {note}")

    CONTENT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成：{CONTENT_FILE}")
    print("下一步：python generate.py")


if __name__ == "__main__":
    main()
