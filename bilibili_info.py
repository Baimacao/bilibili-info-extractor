# -*- coding: utf-8 -*-
import sys
import os
import datetime
import webbrowser
import requests
import urllib3
from PyQt5.QtWidgets import QApplication, QFileDialog, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qfluentwidgets import (
    FluentWindow, PushButton, LineEdit, InfoBar, InfoBarPosition,
    HyperlinkButton, BodyLabel, TitleLabel, setTheme, Theme, FluentIcon as FIF
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_VIDEO = "https://uapis.cn/api/v1/social/bilibili/videoinfo"
API_LIVE  = "https://uapis.cn/api/v1/social/bilibili/liveroom"
API_USER  = "https://uapis.cn/api/v1/social/bilibili/userinfo"
API_ARCHIVES = "https://uapis.cn/api/v1/social/bilibili/archives"
API_REPLIES = "https://uapis.cn/api/v1/social/bilibili/replies"

def get_video_info(value: str) -> dict:
    cleaned = value.strip()
    if cleaned.lower().startswith("av"):
        aid = cleaned[2:]
        if aid.isdigit():
            params = {"aid": aid}
        else:
            raise ValueError("AV 号格式不正确")
    elif cleaned.upper().startswith("BV"):
        params = {"bvid": cleaned}
    elif cleaned.isdigit():
        params = {"aid": cleaned}
    else:
        params = {"bvid": cleaned}

    response = requests.get(API_VIDEO, params=params, verify=False, timeout=10)
    if response.status_code != 200:
        raise ConnectionError(f"API 请求失败，状态码：{response.status_code}")

    data = response.json()
    if isinstance(data, dict) and data.get("code") is not None and data["code"] != 0:
        raise ValueError(f"API 返回错误：{data.get('message', '未知错误')}")
    return data

# ---------- 通用后台线程 ----------
class FetchThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api, params, save_dir, filename, html_builder):
        super().__init__()
        self.api = api
        self.params = params
        self.save_dir = save_dir
        self.filename = filename
        self.html_builder = html_builder

    def run(self):
        try:
            resp = requests.get(self.api, params=self.params, verify=False, timeout=10)
            if resp.status_code != 200:
                raise ConnectionError(f"API 请求失败，状态码：{resp.status_code}")
            data = resp.json()
            if isinstance(data, dict) and data.get("code") is not None and data["code"] != 0:
                raise ValueError(f"API 返回错误：{data.get('message', '未知错误')}")
            html = self.html_builder(data)
            path = os.path.join(self.save_dir, self.filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))

class RepliesThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, input_value, save_dir, sort_val, ps, pn):
        super().__init__()
        self.input_value = input_value
        self.save_dir = save_dir
        self.sort_val = sort_val
        self.ps = ps
        self.pn = pn

    def run(self):
        try:
            if self.input_value.upper().startswith("BV"):
                video_data = get_video_info(self.input_value)
                oid = str(video_data.get("aid", ""))
                if not oid:
                    raise ValueError("无法获取视频 AID，请检查 BV 号是否正确")
            else:
                oid = self.input_value

            params = {"oid": oid, "sort": self.sort_val, "ps": self.ps, "pn": self.pn}
            resp = requests.get(API_REPLIES, params=params, verify=False, timeout=10)
            if resp.status_code != 200:
                raise ConnectionError(f"API 请求失败，状态码：{resp.status_code}")
            data = resp.json()
            if isinstance(data, dict) and data.get("code") is not None and data["code"] != 0:
                raise ValueError(f"API 返回错误：{data.get('message', '未知错误')}")
            html = generate_replies_html(data)
            path = os.path.join(self.save_dir, "bilibili_replies.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))

# ---------- 工具函数 ----------
def format_timestamp(ts: int) -> str:
    if not ts: return "未知"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def format_duration(sec: int) -> str:
    if not sec: return "00:00"
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h: return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

# ==================== HTML 生成函数 ====================
def generate_video_html(info: dict) -> str:
    # 视频 HTML（与之前相同，完整 WinUI 风格）
    bvid = info.get("bvid", "")
    aid = info.get("aid", "")
    title = info.get("title", "无标题")
    pic = info.get("pic", "")
    desc = info.get("desc", "").replace("\n", "<br>")
    dynamic = info.get("dynamic", "").replace("\n", "<br>")
    pubdate = format_timestamp(info.get("pubdate"))
    ctime = format_timestamp(info.get("ctime"))
    duration = format_duration(info.get("duration", 0))
    videos_count = info.get("videos", 1)

    raw_tname = info.get("tname")
    tid = info.get("tid", "?")
    tname = raw_tname if raw_tname else f"分区ID: {tid}"

    raw_cp = info.get("copyright")
    if raw_cp == 1: copyright_type = "原创"
    elif raw_cp == 2: copyright_type = "转载"
    elif raw_cp == 3: copyright_type = "AI生成"
    else: copyright_type = f"未知({raw_cp})" if raw_cp is not None else "未知"

    owner = info.get("owner", {})
    stat = info.get("stat", {})
    pages = info.get("pages") or []
    staff = info.get("staff") or []
    subtitle = info.get("subtitle") or {}
    honor = (info.get("honor_reply") or {}).get("honor") or []
    dimension = info.get("dimension", {})

    up_name = owner.get("name", "未知")
    up_face = owner.get("face", "")
    up_mid = owner.get("mid", "")

    stat_view = stat.get("view", 0)
    stat_danmaku = stat.get("danmaku", 0)
    stat_reply = stat.get("reply", 0)
    stat_favorite = stat.get("favorite", 0)
    stat_coin = stat.get("coin", 0)
    stat_share = stat.get("share", 0)
    stat_like = stat.get("like", 0)

    width = dimension.get("width", "?")
    height = dimension.get("height", "?")
    res_text = f"{width}x{height}" if width and height else "未知"

    pages_rows = ""
    for p in pages:
        p_cid = p.get("cid", "")
        p_page = p.get("page", "")
        p_part = p.get("part", "")
        p_duration = format_duration(p.get("duration", 0))
        pd = p.get("dimension", {})
        p_res = f"{pd.get('width','?')}x{pd.get('height','?')}" if pd else ""
        pages_rows += f"<tr><td>{p_page}</td><td>{p_part}</td><td>{p_duration}</td><td>{p_res}</td><td><code>{p_cid}</code></td></tr>"

    staff_cards = "".join(
        f"<div class='staff-card'><img src='{s.get('face','')}' class='staff-face'><div><span class='staff-name'>{s.get('name','')}</span><br><span class='staff-role'>{s.get('title','')}</span></div></div>"
        for s in staff)

    honor_tags = "".join(f"<span class='tag honor'>{h.get('desc','')}</span>" for h in honor)
    subtitle_items = "".join(
        f"<li>{sub.get('lan_doc', sub.get('lan',''))}（{sub.get('author',{}).get('name','未知')}）</li>"
        for sub in subtitle.get("list", []))

    tags = []
    if info.get("is_upower_exclusive"): tags.append("<span class='tag exclusive'>充电专属</span>")
    if info.get("is_cooperation") or staff: tags.append("<span class='tag coop'>联合投稿</span>")
    if info.get("is_360"): tags.append("<span class='tag'>360°</span>")

    dynamic_html = f"<div class='meta-row' style='margin-top:8px;'><div class='meta-item' style='width:100%'><span class='meta-label'>📢 动态 / 曾用标题</span><span class='meta-value' style='white-space:pre-wrap;'>{dynamic}</span></div></div>" if dynamic else ""

    rights = info.get("rights") or {}
    rights_text = []
    if rights.get("no_reprint"): rights_text.append("禁止转载")
    if rights.get("download"): rights_text.append("允许下载")
    if rights.get("pay") or rights.get("arc_pay"): rights_text.append("付费视频")
    if rights.get("movie"): rights_text.append("电影")
    if rights.get("no_share"): rights_text.append("禁止分享")

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{title} - B站视频</title>
<style>
:root{{--accent:#0078D4;--bg:#F3F3F3;--surface:#FFF;--border:#E1E1E1;--text:#1E1E1E;--text-secondary:#5C5C5C;--radius:12px;--radius-sm:8px;--shadow:0 2px 6px rgba(0,0,0,.08);--shadow-lg:0 8px 24px rgba(0,0,0,.12)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Segoe UI Variable","Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);padding:24px;animation:fadeIn .4s ease-out}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.container{{max-width:960px;margin:0 auto;background:var(--surface);border-radius:16px;box-shadow:var(--shadow-lg);overflow:hidden;animation:slideUp .5s cubic-bezier(.16,1,.3,1)}}
@keyframes slideUp{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:translateY(0)}}}}
.header{{background:linear-gradient(135deg,var(--accent),#3A96DD);padding:32px 30px;color:#fff;position:relative;overflow:hidden}}
.header::after{{content:"";position:absolute;inset:0;background:radial-gradient(circle at 30% 40%,rgba(255,255,255,.2) 0%,transparent 60%)}}
.header h1{{font-size:28px;font-weight:600;margin-bottom:10px;position:relative;z-index:1}}
.header .id-line{{font-size:14px;display:flex;gap:16px;flex-wrap:wrap;position:relative;z-index:1}}
.header .id-line span{{background:rgba(255,255,255,.2);backdrop-filter:blur(4px);padding:4px 14px;border-radius:20px}}
.main{{display:flex;flex-wrap:wrap;gap:24px;padding:24px}}
.cover{{flex:1 1 300px;max-width:400px;aspect-ratio:16/9;border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow)}}
.cover img{{width:100%;height:100%;object-fit:cover}}
.info-panel{{flex:2 1 400px;display:flex;flex-direction:column;gap:16px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow)}}
.card h3{{font-size:16px;font-weight:600;margin-bottom:14px;color:var(--accent)}}
.meta-row{{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:10px}}
.meta-item{{display:flex;flex-direction:column;min-width:80px}}
.meta-label{{font-size:11px;color:#8A8A8A;text-transform:uppercase;letter-spacing:.3px}}
.meta-value{{font-size:15px;font-weight:500}}
.up-info{{display:flex;align-items:center;gap:14px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)}}
.up-avatar{{width:48px;height:48px;border-radius:50%;object-fit:cover}}
.up-name{{font-size:18px;font-weight:600}}
.up-mid{{font-size:13px;color:var(--text-secondary)}}
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:12px;margin-top:10px}}
.stat-item{{background:#F9F9F9;padding:14px 6px;border-radius:var(--radius-sm);text-align:center}}
.stat-number{{font-size:22px;font-weight:700;color:var(--accent)}}
.stat-desc{{font-size:12px;color:#8A8A8A}}
.description{{font-size:14px;color:var(--text-secondary);line-height:1.7;background:#F9F9F9;padding:16px;border-radius:var(--radius-sm);margin-top:12px}}
.section{{padding:0 24px 24px 24px}}
.section-title{{font-size:18px;font-weight:600;margin-bottom:14px;color:var(--accent)}}
table{{width:100%;border-collapse:collapse;border-radius:var(--radius-sm);overflow:hidden;box-shadow:var(--shadow)}}
th,td{{padding:12px 16px;text-align:left;border-bottom:1px solid var(--border)}}
th{{background:#F9F9F9;font-weight:600;color:var(--text-secondary)}}
.tags{{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}}
.tag{{display:inline-block;background:#F0F0F0;color:var(--text-secondary);padding:4px 12px;border-radius:20px;font-size:12px;font-weight:500}}
.tag.honor{{background:#FFF8E7;color:#B87B1B}}
.tag.exclusive{{background:#FDE7F3;color:#A94469}}
.tag.coop{{background:#E6F1FC;color:#1A5EAC}}
.staff-card{{display:flex;align-items:center;gap:10px;background:var(--surface);padding:10px 16px;border-radius:var(--radius-sm);border:1px solid var(--border)}}
.staff-face{{width:36px;height:36px;border-radius:50%}}
.subtitle-list{{list-style:none;margin-top:8px;font-size:14px}}
.footer{{text-align:center;padding:20px;color:#8A8A8A;border-top:1px solid var(--border);font-size:12px}}
</style></head>
<body><div class="container">
<div class="header"><h1>{title}</h1><div class="id-line"><span>AV{aid}</span><span>{bvid}</span></div></div>
<div class="main">
<div class="cover"><img src="{pic}" onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22320%22 height=%22180%22%3E%3Crect fill=%22%23F3F3F3%22 width=%22320%22 height=%22180%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%238A8A8A%22%3E暂无封面%3C/text%3E%3C/svg%3E';"></div>
<div class="info-panel">
<div class="card"><h3>基本信息</h3>
<div class="meta-row"><div class="meta-item"><span class="meta-label">分区</span><span class="meta-value">{tname}</span></div><div class="meta-item"><span class="meta-label">类型</span><span class="meta-value">{copyright_type}</span></div><div class="meta-item"><span class="meta-label">时长</span><span class="meta-value">{duration}</span></div><div class="meta-item"><span class="meta-label">分P数</span><span class="meta-value">{videos_count}</span></div><div class="meta-item"><span class="meta-label">分辨率</span><span class="meta-value">{res_text}</span></div></div>
<div class="meta-row"><div class="meta-item"><span class="meta-label">发布时间</span><span class="meta-value">{pubdate}</span></div><div class="meta-item"><span class="meta-label">投稿时间</span><span class="meta-value">{ctime}</span></div></div>
{dynamic_html}
<div class="tags">{honor_tags}{''.join(tags)}</div>
<div class="up-info"><img src="{up_face}" class="up-avatar" onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2248%22 height=%2248%22%3E%3Ccircle cx=%2224%22 cy=%2224%22 r=%2224%22 fill=%22%23E1E1E1%22/%3E%3C/svg%3E';"><div><div class="up-name">{up_name}</div><div class="up-mid">UID: {up_mid}</div></div></div>
</div>
<div class="card"><h3>数据统计</h3>
<div class="stat-grid">
<div class="stat-item"><div class="stat-number">{stat_view:,}</div><div class="stat-desc">播放</div></div>
<div class="stat-item"><div class="stat-number">{stat_danmaku:,}</div><div class="stat-desc">弹幕</div></div>
<div class="stat-item"><div class="stat-number">{stat_reply:,}</div><div class="stat-desc">评论</div></div>
<div class="stat-item"><div class="stat-number">{stat_like:,}</div><div class="stat-desc">点赞</div></div>
<div class="stat-item"><div class="stat-number">{stat_coin:,}</div><div class="stat-desc">硬币</div></div>
<div class="stat-item"><div class="stat-number">{stat_favorite:,}</div><div class="stat-desc">收藏</div></div>
<div class="stat-item"><div class="stat-number">{stat_share:,}</div><div class="stat-desc">分享</div></div>
</div></div>
</div></div>
<div class="section"><div class="section-title">简介</div><div class="description">{desc or "暂无简介"}</div></div>
"""
    if pages:
        html += f"<div class='section'><div class='section-title'>分P列表</div><table><tr><th>序号</th><th>标题</th><th>时长</th><th>分辨率</th><th>CID</th></tr>{pages_rows}</table></div>"
    if staff:
        html += f"<div class='section'><div class='section-title'>联合投稿</div><div style='display:flex;flex-wrap:wrap;gap:12px;'>{staff_cards}</div></div>"
    if subtitle.get("list"):
        html += f"<div class='section'><div class='section-title'>字幕</div><ul class='subtitle-list'>{subtitle_items}</ul></div>"
    if rights_text:
        html += f"<div class='section'><div class='section-title'>权限</div><div class='tags'>{''.join(f'<span class="tag">{t}</span>' for t in rights_text)}</div></div>"
    html += "<div class='footer'>Generated by Bilibili Video App</div></div></body></html>"
    return html

def generate_live_html(info: dict) -> str:
    uid = info.get("uid", "")
    room_id = info.get("room_id", "")
    short_id = info.get("short_id", 0)
    attention = info.get("attention", 0)
    online = info.get("online", 0)
    is_portrait = info.get("is_portrait", False)
    live_status = info.get("live_status", 0)
    area_name = info.get("area_name", "未知")
    parent_area_name = info.get("parent_area_name", "未知")
    title = info.get("title", "无标题")
    cover = info.get("user_cover") or info.get("background") or ""
    description = info.get("description", "").replace("\n", "<br>")
    live_time = info.get("live_time", "")
    tags = info.get("tags", "")
    hot_words = info.get("hot_words", [])

    status_map = {0: "未开播", 1: "直播中", 2: "轮播中"}
    status_text = status_map.get(live_status, f"未知({live_status})")
    status_color = "#107C10" if live_status == 1 else "#C42B1C" if live_status == 0 else "#FF8C00"
    hot_html = ", ".join(hot_words) if hot_words else "无"
    portrait_text = "竖屏" if is_portrait else "横屏"

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{title} - 直播间</title>
<style>
:root{{--accent:#0078D4;--bg:#F3F3F3;--surface:#FFF;--border:#E1E1E1;--text:#1E1E1E;--text-secondary:#5C5C5C;--radius:12px;--shadow:0 2px 6px rgba(0,0,0,.08);--shadow-lg:0 8px 24px rgba(0,0,0,.12)}}
body{{font-family:"Segoe UI Variable","Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);padding:24px;animation:fadeIn .4s}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.container{{max-width:800px;margin:0 auto;background:var(--surface);border-radius:16px;box-shadow:var(--shadow-lg);overflow:hidden}}
.header{{background:linear-gradient(135deg,var(--accent),#3A96DD);padding:32px 30px;color:#fff;position:relative}}
.header h1{{font-size:28px;font-weight:600}}
.id-line{{font-size:14px;margin-top:8px}}
.id-line span{{background:rgba(255,255,255,.2);padding:4px 12px;border-radius:20px;margin-right:10px}}
.content{{padding:24px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px;margin-bottom:16px;box-shadow:var(--shadow)}}
.card h3{{color:var(--accent);font-weight:600;margin-bottom:12px}}
.row{{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:8px}}
.item{{display:flex;flex-direction:column;min-width:100px}}
.label{{font-size:11px;color:#8A8A8A;text-transform:uppercase}}
.value{{font-size:15px;font-weight:500}}
.cover img{{width:100%;border-radius:var(--radius);max-height:300px;object-fit:cover}}
.status{{display:inline-block;padding:2px 12px;border-radius:20px;color:white;background:{status_color};font-weight:600;font-size:14px}}
.tags span{{display:inline-block;background:#F0F0F0;padding:2px 10px;border-radius:20px;font-size:12px;margin-right:6px}}
.footer{{text-align:center;padding:20px;color:#8A8A8A;border-top:1px solid var(--border);font-size:12px}}
</style></head>
<body><div class="container">
<div class="header"><h1>{title}</h1><div class="id-line"><span>UID: {uid}</span><span>房间号: {room_id}</span>{f'<span>短号: {short_id}</span>' if short_id else ''}</div></div>
<div class="content">
<div class="card"><h3>直播状态</h3>
<div class="row"><div class="item"><span class="label">状态</span><span class="value status">{status_text}</span></div><div class="item"><span class="label">人气</span><span class="value">{online:,}</span></div><div class="item"><span class="label">粉丝</span><span class="value">{attention:,}</span></div><div class="item"><span class="label">画面</span><span class="value">{portrait_text}</span></div><div class="item"><span class="label">开播时间</span><span class="value">{live_time or '未开播'}</span></div></div></div>
<div class="card"><h3>分区与标签</h3>
<div class="row"><div class="item"><span class="label">父分区</span><span class="value">{parent_area_name}</span></div><div class="item"><span class="label">子分区</span><span class="value">{area_name}</span></div></div>
<div class="tags" style="margin-top:10px">{''.join(f'<span>{t.strip()}</span>' for t in tags.split(',') if t.strip())}</div>
<div class="row" style="margin-top:10px"><div class="item"><span class="label">热词</span><span class="value">{hot_html}</span></div></div></div>
{f'<div class="card"><h3>封面</h3><div class="cover"><img src="{cover}" onerror="this.onerror=null;this.src=\'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22320%22 height=%22180%22%3E%3Crect fill=%22%23F3F3F3%22 width=%22320%22 height=%22180%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%238A8A8A%22%3E暂无封面%3C/text%3E%3C/svg%3E\'"></div></div>' if cover else ''}
<div class="card"><h3>简介</h3><div style="font-size:14px;color:var(--text-secondary);line-height:1.6">{description or '暂无简介'}</div></div>
</div>
<div class="footer">Generated by Bilibili Live App</div>
</div></body></html>"""
    return html

def generate_user_html(info: dict) -> str:
    mid = info.get("mid", "")
    name = info.get("name", "未知")
    sex = info.get("sex", "保密")
    face = info.get("face", "")
    sign = info.get("sign", "").replace("\n", "<br>")
    level = info.get("level", 0)
    birthday = info.get("birthday", "")
    vip_type = info.get("vip_type", 0)
    vip_status = info.get("vip_status", 0)
    following = info.get("following", 0)
    follower = info.get("follower", 0)
    archive_count = info.get("archive_count", 0)
    article_count = info.get("article_count", 0)

    if vip_status == 1:
        vip_text = "年度大会员" if vip_type == 2 else "月度大会员" if vip_type == 1 else "大会员"
    else:
        vip_text = "非大会员"

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{name} - 用户资料</title>
<style>
:root{{--accent:#0078D4;--bg:#F3F3F3;--surface:#FFF;--border:#E1E1E1;--text:#1E1E1E;--text-secondary:#5C5C5C;--radius:12px;--shadow:0 2px 6px rgba(0,0,0,.08);--shadow-lg:0 8px 24px rgba(0,0,0,.12)}}
body{{font-family:"Segoe UI Variable","Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);padding:24px;animation:fadeIn .4s}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.container{{max-width:600px;margin:0 auto;background:var(--surface);border-radius:16px;box-shadow:var(--shadow-lg);overflow:hidden}}
.header{{background:linear-gradient(135deg,var(--accent),#3A96DD);padding:30px;color:#fff;text-align:center}}
.avatar{{width:80px;height:80px;border-radius:50%;border:3px solid rgba(255,255,255,.5);margin-bottom:12px;object-fit:cover}}
.name{{font-size:24px;font-weight:600}}
.uid{{font-size:14px;opacity:.9;margin-top:4px}}
.content{{padding:24px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px;margin-bottom:16px;box-shadow:var(--shadow)}}
.card h3{{color:var(--accent);font-weight:600;margin-bottom:12px}}
.row{{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:8px}}
.item{{display:flex;flex-direction:column;min-width:100px}}
.label{{font-size:11px;color:#8A8A8A;text-transform:uppercase}}
.value{{font-size:15px;font-weight:500}}
.level{{display:inline-block;background:var(--accent);color:#fff;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:600;margin-left:8px}}
.signature{{font-size:14px;color:var(--text-secondary);line-height:1.6;margin-top:8px}}
.footer{{text-align:center;padding:20px;color:#8A8A8A;border-top:1px solid var(--border);font-size:12px}}
</style></head>
<body><div class="container">
<div class="header">
<img class="avatar" src="{face}" onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2280%22 height=%2280%22%3E%3Ccircle cx=%2240%22 cy=%2240%22 r=%2240%22 fill=%22%23E1E1E1%22/%3E%3C/svg%3E';">
<div class="name">{name} <span class="level">LV{level}</span></div>
<div class="uid">UID: {mid}</div>
</div>
<div class="content">
<div class="card"><h3>基本信息</h3>
<div class="row"><div class="item"><span class="label">性别</span><span class="value">{sex}</span></div><div class="item"><span class="label">生日</span><span class="value">{birthday or '未填写'}</span></div><div class="item"><span class="label">会员</span><span class="value">{vip_text}</span></div></div>
<div class="signature">{sign or '这个人很懒，什么都没写'}</div>
</div>
<div class="card"><h3>统计数据</h3>
<div class="row"><div class="item"><span class="label">关注</span><span class="value">{following:,}</span></div><div class="item"><span class="label">粉丝</span><span class="value">{follower:,}</span></div><div class="item"><span class="label">视频</span><span class="value">{archive_count:,}</span></div><div class="item"><span class="label">专栏</span><span class="value">{article_count:,}</span></div></div>
</div>
</div>
<div class="footer">Generated by Bilibili User App</div>
</div></body></html>"""
    return html

def generate_archives_html(data: dict) -> str:
    total = data.get("total", 0)
    page = data.get("page", 1)
    size = data.get("size", 0)
    videos = data.get("videos", [])

    items_html = ""
    for v in videos:
        aid = v.get("aid", "")
        bvid = v.get("bvid", "")
        title = v.get("title", "无标题")
        cover = v.get("cover", "")
        duration = format_duration(v.get("duration", 0))
        play_count = v.get("play_count", 0)
        pub_time = format_timestamp(v.get("publish_time"))
        state = "正常" if v.get("state") == 0 else "异常"
        ugc_pay = "付费" if v.get("is_ugc_pay") == 1 else "免费"
        interactive = "互动" if v.get("is_interactive") else "普通"

        items_html += f"""
        <div class="video-item">
            <div class="cover">
                <img src="{cover}" onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22160%22 height=%2290%22%3E%3Crect fill=%22%23E1E1E1%22 width=%22160%22 height=%2290%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%238A8A8A%22%3E无封面%3C/text%3E%3C/svg%3E';">
            </div>
            <div class="info">
                <div class="title">{title}</div>
                <div class="meta">
                    <span>AV{aid}</span>
                    <span>{bvid}</span>
                    <span>{duration}</span>
                    <span>{play_count} 播放</span>
                    <span>{pub_time}</span>
                </div>
                <div class="tags">
                    <span class="tag">{state}</span>
                    <span class="tag">{ugc_pay}</span>
                    <span class="tag">{interactive}</span>
                </div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>投稿列表 - 第{page}页</title>
<style>
:root{{--accent:#0078D4;--bg:#F3F3F3;--surface:#FFF;--border:#E1E1E1;--text:#1E1E1E;--text-secondary:#5C5C5C;--radius:12px;--radius-sm:8px;--shadow:0 2px 6px rgba(0,0,0,.08);--shadow-lg:0 8px 24px rgba(0,0,0,.12)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Segoe UI Variable","Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);padding:24px;animation:fadeIn .4s}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.container{{max-width:1000px;margin:0 auto;background:var(--surface);border-radius:16px;box-shadow:var(--shadow-lg);overflow:hidden}}
.header{{background:linear-gradient(135deg,var(--accent),#3A96DD);padding:24px 30px;color:#fff}}
.header h1{{font-size:24px;font-weight:600}}
.header .summary{{font-size:14px;opacity:.9;margin-top:8px}}
.video-list{{padding:20px;display:flex;flex-direction:column;gap:16px}}
.video-item{{display:flex;gap:16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:12px;box-shadow:var(--shadow);transition:box-shadow .2s}}
.video-item:hover{{box-shadow:var(--shadow-lg)}}
.cover{{flex:0 0 160px;height:90px;border-radius:8px;overflow:hidden}}
.cover img{{width:100%;height:100%;object-fit:cover}}
.info{{flex:1;display:flex;flex-direction:column;justify-content:space-between}}
.title{{font-size:16px;font-weight:600;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.meta{{font-size:13px;color:var(--text-secondary);display:flex;flex-wrap:wrap;gap:12px;margin-top:4px}}
.meta span{{background:#F0F0F0;padding:2px 8px;border-radius:12px;font-size:12px}}
.tags{{display:flex;gap:6px;margin-top:4px}}
.tag{{font-size:11px;background:#E6F1FC;color:#1A5EAC;padding:2px 8px;border-radius:10px}}
.footer{{text-align:center;padding:20px;color:#8A8A8A;border-top:1px solid var(--border);font-size:12px}}
</style></head>
<body><div class="container">
<div class="header">
    <h1>UP 主投稿列表</h1>
    <div class="summary">共 {total} 个视频 · 第 {page} 页 / 每页 {size} 条</div>
</div>
<div class="video-list">
    {items_html if items_html else '<div style="text-align:center;color:#8A8A8A;padding:40px;">暂无视频</div>'}
</div>
<div class="footer">Generated by Bilibili Archives App</div>
</div></body></html>"""
    return html

def generate_replies_html(data: dict) -> str:
    page_info = data.get("page", {})
    num = page_info.get("num", 1)
    size = page_info.get("size", 0)
    count = page_info.get("count", 0)
    acount = page_info.get("acount", 0)

    hots = data.get("hots") or []
    replies = data.get("replies") or []

    def render_comments(comments):
        items = ""
        for c in comments:
            rpid = c.get("rpid", "")
            oid = c.get("oid", "")
            mid = c.get("mid", "")
            root = c.get("root", 0)
            parent = c.get("parent", 0)
            count = c.get("count", 0)
            ctime = format_timestamp(c.get("ctime"))
            like = c.get("like", 0)
            member = c.get("member", {})
            uname = member.get("uname", "未知")
            avatar = member.get("avatar", "")
            level = member.get("level_info", {}).get("current_level", 0)
            content = c.get("content", {})
            message = content.get("message", "").replace("\n", "<br>")

            items += f"""
            <div class="comment">
                <div class="comment-header">
                    <img class="avatar" src="{avatar}" onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2232%22 height=%2232%22%3E%3Ccircle cx=%2216%22 cy=%2216%22 r=%2216%22 fill=%22%23E1E1E1%22/%3E%3C/svg%3E';">
                    <div class="user-info">
                        <span class="uname">{uname}</span>
                        <span class="level">Lv{level}</span>
                        <span class="time">{ctime}</span>
                    </div>
                </div>
                <div class="body">{message}</div>
                <div class="footer">
                    <span>👍 {like}</span>
                    <span>💬 {count} 回复</span>
                    <span>ID: {rpid}</span>
                </div>
            </div>
            """
        return items

    hot_html = ""
    if hots:
        hot_html = "<div class='section'><div class='section-title'>🔥 热门评论</div><div class='comment-list'>" + render_comments(hots) + "</div></div>"

    reply_html = ""
    if replies:
        reply_html = "<div class='section'><div class='section-title'>📝 最新评论（第 {} 页）</div><div class='comment-list'>".format(num) + render_comments(replies) + "</div></div>"
    else:
        reply_html = "<div class='section'><div class='section-title'>📝 评论列表</div><p style='text-align:center;color:#8A8A8A;padding:20px;'>暂无评论</p></div>"

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>评论区 - 第{num}页</title>
<style>
:root{{--accent:#0078D4;--bg:#F3F3F3;--surface:#FFF;--border:#E1E1E1;--text:#1E1E1E;--text-secondary:#5C5C5C;--radius:12px;--radius-sm:8px;--shadow:0 2px 6px rgba(0,0,0,.08)}}
body{{font-family:"Segoe UI Variable","Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--text);padding:24px;animation:fadeIn .4s}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.container{{max-width:800px;margin:0 auto;background:var(--surface);border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,.12);overflow:hidden}}
.header{{background:linear-gradient(135deg,var(--accent),#3A96DD);padding:24px 30px;color:#fff}}
.header h1{{font-size:24px;font-weight:600}}
.header .stats{{font-size:14px;opacity:.9;margin-top:8px}}
.section{{padding:0 20px 20px 20px}}
.section-title{{font-size:18px;font-weight:600;margin:20px 0 14px 0;color:var(--accent);border-left:4px solid var(--accent);padding-left:12px}}
.comment-list{{display:flex;flex-direction:column;gap:12px}}
.comment{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;box-shadow:var(--shadow)}}
.comment-header{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.avatar{{width:36px;height:36px;border-radius:50%;object-fit:cover}}
.user-info{{display:flex;align-items:center;gap:8px;font-size:14px}}
.uname{{font-weight:600}}
.level{{background:var(--accent);color:#fff;padding:1px 6px;border-radius:10px;font-size:11px}}
.time{{color:var(--text-secondary);font-size:12px}}
.body{{font-size:14px;color:var(--text-secondary);line-height:1.6;margin-bottom:8px}}
.footer{{display:flex;gap:16px;font-size:12px;color:#8A8A8A}}
.footer span{{display:flex;align-items:center;gap:4px}}
.footer-main{{text-align:center;padding:20px;color:#8A8A8A;border-top:1px solid var(--border);font-size:12px}}
</style></head>
<body><div class="container">
<div class="header">
    <h1>视频评论区</h1>
    <div class="stats">总评论数 {acount} · 根评论 {count} · 第 {num} 页 / 每页 {size} 条</div>
</div>
{hot_html}
{reply_html}
<div class="footer-main">Generated by Bilibili Replies App</div>
</div></body></html>"""
    return html

# ==================== 页面类 ====================
class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("aboutPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # 标题
        title = TitleLabel("关于 B站信息提取器", self)
        layout.addWidget(title, alignment=Qt.AlignLeft)

        # 简介
        desc = BodyLabel(
            "本工具集成 B站 视频、直播、用户、投稿、评论查询功能，\n"
            "基于 UAPIS 开放接口，采用 Fluent Design 界面设计。\n"
            "所有数据均为公开信息，仅供学习交流使用。",
            self
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 作者链接
        authorLayout = QHBoxLayout()
        authorLayout.addWidget(BodyLabel("作者：", self))
        authorLink = HyperlinkButton("https://space.bilibili.com/1329200878", "Baimaco", self)
        authorLayout.addWidget(authorLink)
        authorLayout.addStretch(1)
        layout.addLayout(authorLayout)

        # API 来源链接
        apiLayout = QHBoxLayout()
        apiLayout.addWidget(BodyLabel("数据来源：", self))
        apiLink = HyperlinkButton("https://uapis.cn/", "UAPIS", self)
        apiLayout.addWidget(apiLink)
        apiLayout.addStretch(1)
        layout.addLayout(apiLayout)

        layout.addStretch(1)

class VideoPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("videoPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(TitleLabel("B站视频信息提取", self))

        hbox = QHBoxLayout()
        self.inputEdit = LineEdit(self)
        self.inputEdit.setPlaceholderText("输入 AV号 或 BV号")
        self.inputEdit.setFixedHeight(42)
        self.queryBtn = PushButton(FIF.SEARCH, "查询并生成", self)
        self.queryBtn.setFixedHeight(42)
        self.queryBtn.clicked.connect(self.start)
        self.inputEdit.returnPressed.connect(self.start)
        hbox.addWidget(self.inputEdit, 1)
        hbox.addWidget(self.queryBtn, 0)
        layout.addLayout(hbox)

        hbox2 = QHBoxLayout()
        self.pathEdit = LineEdit(self)
        self.pathEdit.setText(os.getcwd())
        self.pathEdit.setFixedHeight(36)
        self.pathEdit.setReadOnly(True)
        self.browseBtn = PushButton(FIF.FOLDER, "选择目录", self)
        self.browseBtn.setFixedHeight(36)
        self.browseBtn.clicked.connect(self.selectFolder)
        hbox2.addWidget(self.pathEdit, 1)
        hbox2.addWidget(self.browseBtn, 0)
        layout.addLayout(hbox2)

        self.statusLabel = BodyLabel("", self)
        layout.addWidget(self.statusLabel)

    def selectFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存目录", self.pathEdit.text())
        if folder:
            self.pathEdit.setText(folder)

    def start(self):
        value = self.inputEdit.text().strip()
        if not value:
            InfoBar.warning(title="提示", content="请输入 AV 号或 BV 号", parent=self.window())
            return
        save_dir = self.pathEdit.text()
        if not os.path.isdir(save_dir):
            InfoBar.error(title="错误", content=f"保存路径不存在：{save_dir}", parent=self.window())
            return

        # 构建参数
        cleaned = value.lower()
        if cleaned.startswith("av"):
            if cleaned[2:].isdigit():
                params = {"aid": cleaned[2:]}
            else:
                InfoBar.error(title="错误", content="AV 号格式不正确", parent=self.window())
                return
        elif cleaned.startswith("bv"):
            params = {"bvid": value}
        elif cleaned.isdigit():
            params = {"aid": value}
        else:
            params = {"bvid": value}

        self.queryBtn.setEnabled(False)
        self.queryBtn.setText("查询中...")
        self.statusLabel.setText("正在获取数据...")
        self.statusLabel.setStyleSheet("color: #0078D4;")

        self.thread = FetchThread(API_VIDEO, params, save_dir, "bilibili_video_info.html", generate_video_html)
        self.thread.finished.connect(self.onSuccess)
        self.thread.error.connect(self.onError)
        self.thread.start()

    def onSuccess(self, path):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询并生成")
        self.statusLabel.setText("生成成功！")
        self.statusLabel.setStyleSheet("color: #107C10;")
        InfoBar.success(title="完成", content=f"HTML 报告已保存至：{path}", parent=self.window())
        webbrowser.open("file://" + os.path.abspath(path))

    def onError(self, err):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询并生成")
        self.statusLabel.setText("查询失败")
        self.statusLabel.setStyleSheet("color: #C42B1C;")
        InfoBar.error(title="操作失败", content=err, parent=self.window())
class RepliesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("repliesPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        layout.addWidget(TitleLabel("B站视频评论查询", self))

        # OID 输入
        midLayout = QHBoxLayout()
        self.oidEdit = LineEdit(self)
        self.oidEdit.setPlaceholderText("输入视频 AID 或 BV号")
        self.oidEdit.setFixedHeight(42)
        self.queryBtn = PushButton(FIF.SEARCH, "查询", self)
        self.queryBtn.setFixedHeight(42)
        self.queryBtn.clicked.connect(self.start)
        self.oidEdit.returnPressed.connect(self.start)
        midLayout.addWidget(self.oidEdit, 1)
        midLayout.addWidget(self.queryBtn, 0)
        layout.addLayout(midLayout)

        # 排序方式
        sortLayout = QHBoxLayout()
        sortLayout.addWidget(BodyLabel("排序：", self))
        self.sortTimeBtn = PushButton("时间", self)
        self.sortTimeBtn.setCheckable(True)
        self.sortTimeBtn.setChecked(True)
        self.sortLikeBtn = PushButton("点赞", self)
        self.sortLikeBtn.setCheckable(True)
        self.sortReplyBtn = PushButton("回复数", self)
        self.sortReplyBtn.setCheckable(True)
        self.sortHotBtn = PushButton("最热", self)
        self.sortHotBtn.setCheckable(True)
        for btn in [self.sortTimeBtn, self.sortLikeBtn, self.sortReplyBtn, self.sortHotBtn]:
            btn.setFixedHeight(32)
            sortLayout.addWidget(btn)
        # 互斥逻辑
        def make_exclusive(current):
            others = [b for b in [self.sortTimeBtn, self.sortLikeBtn, self.sortReplyBtn, self.sortHotBtn] if b != current]
            return lambda: [b.setChecked(False) for b in others] or current.setChecked(True)
        self.sortTimeBtn.clicked.connect(make_exclusive(self.sortTimeBtn))
        self.sortLikeBtn.clicked.connect(make_exclusive(self.sortLikeBtn))
        self.sortReplyBtn.clicked.connect(make_exclusive(self.sortReplyBtn))
        self.sortHotBtn.clicked.connect(make_exclusive(self.sortHotBtn))
        sortLayout.addStretch(1)
        layout.addLayout(sortLayout)

        # 每页条数 + 页码
        optLayout = QHBoxLayout()
        optLayout.addWidget(BodyLabel("每页条数：", self))
        self.psEdit = LineEdit(self)
        self.psEdit.setText("10")
        self.psEdit.setFixedWidth(60)
        self.psEdit.setFixedHeight(36)
        optLayout.addWidget(self.psEdit)

        optLayout.addWidget(BodyLabel("页码：", self))
        self.pnEdit = LineEdit(self)
        self.pnEdit.setText("1")
        self.pnEdit.setFixedWidth(60)
        self.pnEdit.setFixedHeight(36)
        optLayout.addWidget(self.pnEdit)
        optLayout.addStretch(1)
        layout.addLayout(optLayout)

        # 路径
        pathLayout = QHBoxLayout()
        self.pathEdit = LineEdit(self)
        self.pathEdit.setText(os.getcwd())
        self.pathEdit.setFixedHeight(36)
        self.pathEdit.setReadOnly(True)
        self.browseBtn = PushButton(FIF.FOLDER, "选择目录", self)
        self.browseBtn.setFixedHeight(36)
        self.browseBtn.clicked.connect(self.selectFolder)
        pathLayout.addWidget(self.pathEdit, 1)
        pathLayout.addWidget(self.browseBtn, 0)
        layout.addLayout(pathLayout)

        self.statusLabel = BodyLabel("", self)
        layout.addWidget(self.statusLabel)

    def selectFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存目录", self.pathEdit.text())
        if folder:
            self.pathEdit.setText(folder)

    def start(self):
        oid = self.oidEdit.text().strip()
        if not oid:
            InfoBar.warning(title="提示", content="请输入视频 AID 或 BV号", parent=self.window())
            return

        save_dir = self.pathEdit.text()
        if not os.path.isdir(save_dir):
            InfoBar.error(title="错误", content=f"保存路径不存在：{save_dir}", parent=self.window())
            return

        # 确定排序值
        if self.sortTimeBtn.isChecked():
            sort_val = "time"
        elif self.sortLikeBtn.isChecked():
            sort_val = "like"
        elif self.sortReplyBtn.isChecked():
            sort_val = "reply"
        else:
            sort_val = "hot"

        try:
            ps = int(self.psEdit.text()) if self.psEdit.text().strip() else 10
            pn = int(self.pnEdit.text()) if self.pnEdit.text().strip() else 1
        except ValueError:
            InfoBar.error(title="错误", content="每页条数或页码必须为数字", parent=self.window())
            return

        self.queryBtn.setEnabled(False)
        self.queryBtn.setText("查询中...")
        self.statusLabel.setText("正在获取评论...")
        self.statusLabel.setStyleSheet("color: #0078D4;")

        # 使用专用线程，支持 BV 自动转换
        self.thread = RepliesThread(oid, save_dir, sort_val, ps, pn)
        self.thread.finished.connect(self.onSuccess)
        self.thread.error.connect(self.onError)
        self.thread.start()

    def onSuccess(self, path):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询")
        self.statusLabel.setText("生成成功！")
        self.statusLabel.setStyleSheet("color: #107C10;")
        InfoBar.success(title="完成", content=f"HTML 报告已保存至：{path}", parent=self.window())
        webbrowser.open("file://" + os.path.abspath(path))

    def onError(self, err):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询")
        self.statusLabel.setText("查询失败")
        self.statusLabel.setStyleSheet("color: #C42B1C;")
        InfoBar.error(title="操作失败", content=err, parent=self.window())
class LivePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("livePage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(TitleLabel("B站直播间信息查询", self))

        hbox = QHBoxLayout()
        self.inputEdit = LineEdit(self)
        self.inputEdit.setPlaceholderText("输入主播 MID 或房间号")
        self.inputEdit.setFixedHeight(42)
        self.queryBtn = PushButton(FIF.SEARCH, "查询", self)
        self.queryBtn.setFixedHeight(42)
        self.queryBtn.clicked.connect(self.start)
        self.inputEdit.returnPressed.connect(self.start)
        hbox.addWidget(self.inputEdit, 1)
        hbox.addWidget(self.queryBtn, 0)
        layout.addLayout(hbox)

        modelayout = QHBoxLayout()
        self.midBtn = PushButton(FIF.PEOPLE, "MID", self)
        self.midBtn.setCheckable(True); self.midBtn.setChecked(True)
        self.roomBtn = PushButton(FIF.HOME, "房间号", self)
        self.roomBtn.setCheckable(True)
        self.midBtn.clicked.connect(lambda: [self.roomBtn.setChecked(False), self.midBtn.setChecked(True)])
        self.roomBtn.clicked.connect(lambda: [self.midBtn.setChecked(False), self.roomBtn.setChecked(True)])
        modelayout.addWidget(self.midBtn)
        modelayout.addWidget(self.roomBtn)
        modelayout.addStretch(1)
        layout.addLayout(modelayout)

        hbox2 = QHBoxLayout()
        self.pathEdit = LineEdit(self)
        self.pathEdit.setText(os.getcwd())
        self.pathEdit.setFixedHeight(36)
        self.pathEdit.setReadOnly(True)
        self.browseBtn = PushButton(FIF.FOLDER, "选择目录", self)
        self.browseBtn.setFixedHeight(36)
        self.browseBtn.clicked.connect(self.selectFolder)
        hbox2.addWidget(self.pathEdit, 1)
        hbox2.addWidget(self.browseBtn, 0)
        layout.addLayout(hbox2)

        self.statusLabel = BodyLabel("", self)
        layout.addWidget(self.statusLabel)

    def selectFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存目录", self.pathEdit.text())
        if folder:
            self.pathEdit.setText(folder)

    def start(self):
        value = self.inputEdit.text().strip()
        if not value:
            InfoBar.warning(title="提示", content="请输入 MID 或房间号", parent=self.window())
            return
        save_dir = self.pathEdit.text()
        if not os.path.isdir(save_dir):
            InfoBar.error(title="错误", content=f"保存路径不存在：{save_dir}", parent=self.window())
            return

        is_mid = self.midBtn.isChecked()
        params = {"mid": value} if is_mid else {"room_id": value}

        self.queryBtn.setEnabled(False)
        self.queryBtn.setText("查询中...")
        self.statusLabel.setText("正在获取数据...")
        self.statusLabel.setStyleSheet("color: #0078D4;")
        self.thread = FetchThread(API_LIVE, params, save_dir, "bilibili_live_info.html", generate_live_html)
        self.thread.finished.connect(self.onSuccess)
        self.thread.error.connect(self.onError)
        self.thread.start()

    def onSuccess(self, path):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询")
        self.statusLabel.setText("生成成功！")
        self.statusLabel.setStyleSheet("color: #107C10;")
        InfoBar.success(title="完成", content=f"HTML 报告已保存至：{path}", parent=self.window())
        webbrowser.open("file://" + os.path.abspath(path))

    def onError(self, err):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询")
        self.statusLabel.setText("查询失败")
        self.statusLabel.setStyleSheet("color: #C42B1C;")
        InfoBar.error(title="操作失败", content=err, parent=self.window())

class UserPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("userPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(TitleLabel("B站用户信息查询", self))

        hbox = QHBoxLayout()
        self.inputEdit = LineEdit(self)
        self.inputEdit.setPlaceholderText("输入用户 UID")
        self.inputEdit.setFixedHeight(42)
        self.queryBtn = PushButton(FIF.SEARCH, "查询", self)
        self.queryBtn.setFixedHeight(42)
        self.queryBtn.clicked.connect(self.start)
        self.inputEdit.returnPressed.connect(self.start)
        hbox.addWidget(self.inputEdit, 1)
        hbox.addWidget(self.queryBtn, 0)
        layout.addLayout(hbox)

        hbox2 = QHBoxLayout()
        self.pathEdit = LineEdit(self)
        self.pathEdit.setText(os.getcwd())
        self.pathEdit.setFixedHeight(36)
        self.pathEdit.setReadOnly(True)
        self.browseBtn = PushButton(FIF.FOLDER, "选择目录", self)
        self.browseBtn.setFixedHeight(36)
        self.browseBtn.clicked.connect(self.selectFolder)
        hbox2.addWidget(self.pathEdit, 1)
        hbox2.addWidget(self.browseBtn, 0)
        layout.addLayout(hbox2)

        self.statusLabel = BodyLabel("", self)
        layout.addWidget(self.statusLabel)

    def selectFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存目录", self.pathEdit.text())
        if folder:
            self.pathEdit.setText(folder)

    def start(self):
        value = self.inputEdit.text().strip()
        if not value:
            InfoBar.warning(title="提示", content="请输入 UID", parent=self.window())
            return
        save_dir = self.pathEdit.text()
        if not os.path.isdir(save_dir):
            InfoBar.error(title="错误", content=f"保存路径不存在：{save_dir}", parent=self.window())
            return
        if not value.isdigit():
            InfoBar.error(title="错误", content="UID 必须为纯数字", parent=self.window())
            return

        params = {"uid": value}
        self.queryBtn.setEnabled(False)
        self.queryBtn.setText("查询中...")
        self.statusLabel.setText("正在获取数据...")
        self.statusLabel.setStyleSheet("color: #0078D4;")
        self.thread = FetchThread(API_USER, params, save_dir, "bilibili_user_info.html", generate_user_html)
        self.thread.finished.connect(self.onSuccess)
        self.thread.error.connect(self.onError)
        self.thread.start()

    def onSuccess(self, path):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询")
        self.statusLabel.setText("生成成功！")
        self.statusLabel.setStyleSheet("color: #107C10;")
        InfoBar.success(title="完成", content=f"HTML 报告已保存至：{path}", parent=self.window())
        webbrowser.open("file://" + os.path.abspath(path))

    def onError(self, err):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询")
        self.statusLabel.setText("查询失败")
        self.statusLabel.setStyleSheet("color: #C42B1C;")
        InfoBar.error(title="操作失败", content=err, parent=self.window())

class ArchivesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("archivesPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        layout.addWidget(TitleLabel("B站 UP 主投稿查询", self))

        # MID 输入
        midLayout = QHBoxLayout()
        self.midEdit = LineEdit(self)
        self.midEdit.setPlaceholderText("输入 UP 主 MID")
        self.midEdit.setFixedHeight(42)
        self.queryBtn = PushButton(FIF.SEARCH, "查询", self)
        self.queryBtn.setFixedHeight(42)
        self.queryBtn.clicked.connect(self.start)
        self.midEdit.returnPressed.connect(self.start)
        midLayout.addWidget(self.midEdit, 1)
        midLayout.addWidget(self.queryBtn, 0)
        layout.addLayout(midLayout)

        # 高级选项行1：关键词 + 排序
        optLayout1 = QHBoxLayout()
        optLayout1.addWidget(BodyLabel("关键词：", self))
        self.kwEdit = LineEdit(self)
        self.kwEdit.setPlaceholderText("可选")
        self.kwEdit.setFixedHeight(36)
        optLayout1.addWidget(self.kwEdit, 1)

        optLayout1.addWidget(BodyLabel("排序：", self))
        self.orderNewBtn = PushButton("最新发布", self)
        self.orderNewBtn.setCheckable(True)
        self.orderNewBtn.setChecked(True)
        self.orderViewBtn = PushButton("最多播放", self)
        self.orderViewBtn.setCheckable(True)
        self.orderNewBtn.clicked.connect(lambda: [self.orderViewBtn.setChecked(False), self.orderNewBtn.setChecked(True)])
        self.orderViewBtn.clicked.connect(lambda: [self.orderNewBtn.setChecked(False), self.orderViewBtn.setChecked(True)])
        optLayout1.addWidget(self.orderNewBtn)
        optLayout1.addWidget(self.orderViewBtn)
        layout.addLayout(optLayout1)

        # 高级选项行2：每页条数 + 页码
        optLayout2 = QHBoxLayout()
        optLayout2.addWidget(BodyLabel("每页条数：", self))
        self.psEdit = LineEdit(self)
        self.psEdit.setText("20")
        self.psEdit.setFixedWidth(60)
        self.psEdit.setFixedHeight(36)
        optLayout2.addWidget(self.psEdit)

        optLayout2.addWidget(BodyLabel("页码：", self))
        self.pnEdit = LineEdit(self)
        self.pnEdit.setText("1")
        self.pnEdit.setFixedWidth(60)
        self.pnEdit.setFixedHeight(36)
        optLayout2.addWidget(self.pnEdit)
        optLayout2.addStretch(1)
        layout.addLayout(optLayout2)

        # 路径选择
        pathLayout = QHBoxLayout()
        self.pathEdit = LineEdit(self)
        self.pathEdit.setText(os.getcwd())
        self.pathEdit.setFixedHeight(36)
        self.pathEdit.setReadOnly(True)
        self.browseBtn = PushButton(FIF.FOLDER, "选择目录", self)
        self.browseBtn.setFixedHeight(36)
        self.browseBtn.clicked.connect(self.selectFolder)
        pathLayout.addWidget(self.pathEdit, 1)
        pathLayout.addWidget(self.browseBtn, 0)
        layout.addLayout(pathLayout)

        self.statusLabel = BodyLabel("", self)
        layout.addWidget(self.statusLabel)

    def selectFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存目录", self.pathEdit.text())
        if folder:
            self.pathEdit.setText(folder)

    def start(self):
        mid = self.midEdit.text().strip()
        if not mid:
            InfoBar.warning(title="提示", content="请输入 UP 主 MID", parent=self.window())
            return
        if not mid.isdigit():
            InfoBar.error(title="错误", content="MID 必须为纯数字", parent=self.window())
            return

        save_dir = self.pathEdit.text()
        if not os.path.isdir(save_dir):
            InfoBar.error(title="错误", content=f"保存路径不存在：{save_dir}", parent=self.window())
            return

        # 构建参数
        params = {"mid": mid}
        keywords = self.kwEdit.text().strip()
        if keywords:
            params["keywords"] = keywords
        params["orderby"] = "pubdate" if self.orderNewBtn.isChecked() else "views"

        try:
            ps = int(self.psEdit.text()) if self.psEdit.text().strip() else 20
            pn = int(self.pnEdit.text()) if self.pnEdit.text().strip() else 1
        except ValueError:
            InfoBar.error(title="错误", content="每页条数或页码必须为数字", parent=self.window())
            return
        params["ps"] = ps
        params["pn"] = pn

        self.queryBtn.setEnabled(False)
        self.queryBtn.setText("查询中...")
        self.statusLabel.setText("正在获取数据...")
        self.statusLabel.setStyleSheet("color: #0078D4;")
        self.thread = FetchThread(API_ARCHIVES, params, save_dir, "bilibili_archives.html", generate_archives_html)
        self.thread.finished.connect(self.onSuccess)
        self.thread.error.connect(self.onError)
        self.thread.start()

    def onSuccess(self, path):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询")
        self.statusLabel.setText("生成成功！")
        self.statusLabel.setStyleSheet("color: #107C10;")
        InfoBar.success(title="完成", content=f"HTML 报告已保存至：{path}", parent=self.window())
        webbrowser.open("file://" + os.path.abspath(path))

    def onError(self, err):
        self.queryBtn.setEnabled(True)
        self.queryBtn.setText("查询")
        self.statusLabel.setText("查询失败")
        self.statusLabel.setStyleSheet("color: #C42B1C;")
        InfoBar.error(title="操作失败", content=err, parent=self.window())

# ==================== 主窗口 ====================
class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("B站信息提取器")
        self.setWindowIcon(QIcon("app_icon.svg"))
        self.resize(720, 560)
        self.setMinimumSize(600, 460)
        self.setMicaEffectEnabled(True)

        # 各功能页面（已移除底部链接）
        self.videoPage = VideoPage()
        self.livePage = LivePage()
        self.userPage = UserPage()
        self.archivesPage = ArchivesPage()
        self.repliesPage = RepliesPage()
        self.aboutPage = AboutPage()                          # 新增

        self.addSubInterface(self.videoPage, FIF.VIDEO, "视频查询")
        self.addSubInterface(self.livePage, FIF.CAMERA, "直播查询")
        self.addSubInterface(self.userPage, FIF.PEOPLE, "用户查询")
        self.addSubInterface(self.archivesPage, FIF.FOLDER, "投稿查询")
        self.addSubInterface(self.repliesPage, FIF.MESSAGE, "评论查询")
        self.addSubInterface(self.aboutPage, FIF.INFO, "关于") # 新增

        self._center()
        self.show()

    def _center(self):
        frame = self.frameGeometry()
        center = QApplication.primaryScreen().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)
    window = MainWindow()
    sys.exit(app.exec_())
