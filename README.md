# 每日咨询 · 固定链接 + GitHub 全自动方案

一个链接长期有效，内容每天自动从 RSS 信息源抓取、自动生成页面并发布。**配好之后不用每天做任何事**，群里那条置顶消息永远指向最新版。

## 原理

```
GitHub Actions 每天北京时间 08:30 自动触发
        ↓
fetch_content.py 从 sources.json 里的 RSS 源抓取最新条目 → 写入 content.md
        ↓
generate.py 生成网页 → 提交回仓库 → GitHub Pages 自动更新
        ↓
群成员点开置顶链接 = 当天抓取的最新内容
```

也可以随时手动改 `content.md` 并 push，会立即触发一次生成（此时以手动内容为准，直到下次定时任务重新抓取）。

## 文件说明

| 文件 | 作用 | 需要改吗 |
|---|---|---|
| `sources.json` | 你的 RSS 信息源地址与每期条数 | ✅ 换成你自己的源 |
| `content.md` | 当天内容（由抓取脚本自动生成） | 否（特殊时手动改） |
| `fetch_content.py` | 抓取 RSS 并生成 content.md | 否 |
| `generate.py` | 生成网页并归档，固定用北京时间 | 否 |
| `.github/workflows/daily-brief.yml` | 自动化工作流 | 否 |
| `.gitignore` | 排除本地 output 目录 | 否 |
| `setup_scheduler.bat` | 本地定时任务（用了 GitHub 后可不用） | 否 |
| `output/` | 本地预览产物，不上传 | 否 |

## 配置你的信息源

编辑 `sources.json`：

```json
{
  "sources": [
{
  "name": "行业动态",
  "url": "https://你的信息源/feed.xml",
  "limit": 3
},
{
  "name": "政策法规",
  "type": "html",
  "url": "https://某政府网站/",
  "url_prefix": "https://某政府网站/",
  "keywords": ["通知", "公告", "办法"],
  "limit": 3
}
  ],
  "note": "以上内容仅供参考，具体以官方发布为准。"
}
```

- `name`：页面上显示的章节标题
- `url`：RSS / Atom 地址（不是网页首页）
- `limit`：该源每期取几条

支持多个源，脚本会按配置顺序生成多个章节。当前配置已内置 9 个**实测可用**的信息源，聚焦你的关注方向：

| 章节 | 来源 | 类型 | 语言 |
|---|---|---|---|
| 政策法规 · 国家能源局文件 | nea.gov.cn 首页 | HTML | 中文 |
| 政策法规 · 国务院最新政策 | gov.cn/zhengce | HTML | 中文 |
| 政策解读 · 产经观察 | 经济观察报 | RSS | 中文 |
| 能源行业 · 天然气与油气 | naturalgasworld.com | RSS | 英文 |
| 能源行业 · 油气工程 | offshore-energy.biz | RSS | 英文 |
| 能源行业 · 储能技术 | energy-storage.news | RSS | 英文 |
| 科技创新 · 创投动态 | 36氪 | RSS | 中文 |
| 科技创新 · AI 前沿 | 量子位 | RSS | 中文 |
| 科技创新 · 技术资讯 | Solidot | RSS | 中文 |

**两种抓取模式**（在 `sources.json` 里用 `type` 区分）：

- `type: "rss"`（默认）：标准 RSS/Atom feed，配置 `url` 和 `limit` 即可
- `type: "html"`：抓取普通网页的链接列表，用于没有 RSS 的政府网站，额外支持：
  - `keywords`：只保留标题含这些词的条目（如"通知/公告/指导意见"）
  - `url_prefix`：把相对链接补全成绝对地址

抓取器已做 XML 容错（非法字符清洗 + 宽松解析兜底），能处理 36氪这类不规范 feed。政策法规栏目页是 JS 渲染的抓不到，所以改为抓首页的静态政策链接并关键词过滤，实测能稳定抓到"十五五新型储能实施方案"等文件。想增删源、调整条数，直接改 `sources.json` 即可。

## 首次部署（只做一次）

### 1. 创建仓库

GitHub 右上角 `New repository`，仓库名填 `daily-brief`，可见性选 Public（Pages 免费版需要公开仓库），**不要**勾选 README / .gitignore / License（保持空仓库）。

### 2. 上传代码

在本目录打开 Git Bash，执行：

```bash
git init
git add content.md generate.py fetch_content.py sources.json .github .gitignore README.md
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/daily-brief.git
git push -u origin main
```

> 也可以用 GitHub Desktop 把本目录拖进去，勾选同样几个文件后 Commit & Push。

### 3. 开启 Pages

仓库页面 → Settings → Pages → Build and deployment：

- Source: **Deploy from a branch**
- Branch: **main** / **/ (root)**
- Save

稍等片刻，得到固定网址：`https://你的用户名.github.io/daily-brief/`

### 4. 验证自动化

仓库页面 → Actions 标签 → 左侧选 **Daily Brief** → 右侧 `Run workflow` → 手动点一次。

等几十秒刷新，如果看到多了一条 `Update daily brief ...` 提交，说明全自动已打通。

> 如果提交失败：Settings → Actions → General → Workflow permissions → 选 **Read and write permissions** → Save，再重跑一次。

## 每天怎么用

**什么都不用做。** 每天北京时间 08:30，Actions 自动抓取 RSS → 生成页面 → 发布，固定链接点开就是当天最新内容。

如果某天想临时插一条自己的内容：到 GitHub 网页编辑 `content.md` 并 Commit，等 1—2 分钟即生效。下次定时任务会按 RSS 源重新生成（手动内容会被覆盖）。

想手动立即跑一次：Actions 标签 → **Daily Brief** → `Run workflow`。

## content.md 写法（仅供手动调整时参考）

```
# 主标题
## 章节名
- 要点一
- [标题](https://原文链接)
普通段落会显示成正文
> 备注/免责声明
```

## 本地预览

```bash
python fetch_content.py   # 从 RSS 抓取内容
python generate.py        # 生成页面
python -m http.server 8000 --directory output
```

浏览器打开 `http://localhost:8000`。本地预览产物在 `output/`，已被 `.gitignore` 排除，不会上传；线上以仓库根目录的 `index.html` 为准。

## 最后一步

把 `https://你的用户名.github.io/daily-brief/` 发到微信群，让群主设为**群置顶**。以后内容每天自动更新，链接永远不变。
