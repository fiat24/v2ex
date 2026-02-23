#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2EX 自动签到脚本（Telegram 推送版）
================================================
一次性配置区（最简用法）
------------------------
只需在本文件顶部填入 **三项信息** 即可运行；如不想把敏感信息写在文件里，也可改用环境变量覆盖。

* `COOKIES_FALLBACK` —— 必填，V2EX 的完整 Cookie 字符串。
* `BOT_TOKEN` —— Telegram Bot Token，可在 [@BotFather](https://t.me/BotFather) 获取。
* `CHAT_ID` —— Telegram Chat ID，可通过 `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` 或 `@userinfobot` 查询。

> **覆写逻辑**：脚本会先读取环境变量 `V2EX_COOKIES`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`；如未设置，则使用本区填写的值。
"""

import os, re, time, random, base64
from datetime import date
from requests import Session, post
from lxml import html

# -------------------------- 配置变量 --------------------------
COOKIES_FALLBACK = ''''''  # ← 在三引号之间粘贴 V2EX Cookie
BOT_TOKEN        = ''''''  # ← 在三引号之间粘贴 Telegram Bot Token
CHAT_ID          = ''''''  # ← 在三引号之间粘贴 Telegram Chat ID

# 若设置了环境变量，将覆盖上方值
COOKIES   = os.getenv("V2EX_COOKIES")        or COOKIES_FALLBACK
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")   or BOT_TOKEN
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")     or CHAT_ID

# -------------------------- 常量定义 --------------------------
_d = lambda s: base64.b64decode(s).decode()

# URLs
_URL_BASE    = _d(b"aHR0cHM6Ly93d3cudjJleC5jb20v")
_URL_DAILY   = _d(b"aHR0cHM6Ly93d3cudjJleC5jb20vbWlzc2lvbi9kYWlseQ==")
_URL_REDEEM  = _d(b"aHR0cHM6Ly93d3cudjJleC5jb20vbWlzc2lvbi9kYWlseS9yZWRlZW0/b25jZT0=")
_URL_BALANCE = _d(b"aHR0cHM6Ly93d3cudjJleC5jb20vYmFsYW5jZQ==")

# 页面关键文本
_TEXT_NEED_LOGIN = _d(b"5L2g6KaB5p+l55yL55qE6aG16Z2i6ZyA6KaB5YWI55m75b2V")
_TEXT_SIGNED     = _d(b"5q+P5pel55m75b2V5aWW5Yqx5bey6aKG5Y+W")

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# ------------------------ Telegram 推送 ------------------------

def send_telegram(msg: str):
    """使用 Telegram Bot 发送 Markdown 消息"""
    if not (BOT_TOKEN and CHAT_ID):
        print("未配置 Telegram Bot Token / Chat ID，跳过推送…")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = post(url, data={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
    })
    if resp.status_code == 200 and resp.json().get("ok"):
        print("Telegram 推送成功")
    else:
        print("Telegram 推送失败：", resp.text)

# -------------------------- 工具函数 --------------------------

def fix_cookies(raw: str) -> str:
    """确保 Cookie 中 V2EX_LANG 为 zhcn，以便页面返回中文"""
    s = raw.strip().strip("'\"")
    s = re.sub(r'(?i)V2EX_LANG=[^;]*', 'V2EX_LANG=zhcn', s)
    if 'V2EX_LANG=zhcn' not in s:
        s += '; V2EX_LANG=zhcn'
    return s

# -------------------------- 签到核心 --------------------------

def main():
    cookie = fix_cookies(COOKIES)
    if not cookie:
        raise SystemExit("未检测到 Cookie，请在顶部 COOKIES_FALLBACK 或环境变量 V2EX_COOKIES 中设置！")

    sess = Session()
    hdr = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cookie": cookie,
        "Referer": _URL_BASE,
        "User-Agent": random.choice(UA_LIST),
    }
    log = []

    # ---- 随机延时 ----
    wait = random.uniform(2, 6)
    print(f"等待 {wait:.1f}s ...")
    time.sleep(wait)

    # ---- 访问签到页面，获取 once token ----
    r = sess.get(_URL_DAILY, headers=hdr, timeout=10)
    page = r.text

    if _TEXT_NEED_LOGIN in page or "Sign in" in page:
        log.append("❌ Cookie 失效，需要重新获取")
    elif _TEXT_SIGNED in page:
        m = re.search(r"已连续登录 (\d+) 天", page)
        log.append(f"✅ 今日已签到，连续 {m.group(1) if m else '?'} 天")
    else:
        m = re.search(r"once=(\d+)", page)
        if not m:
            log.append("❌ 找不到 once，页面结构可能变了")
        else:
            once = m.group(1)
            time.sleep(random.uniform(1, 3))
            h2 = hdr.copy()
            h2["Referer"] = _URL_DAILY
            r2 = sess.get(_URL_REDEEM + once, headers=h2, allow_redirects=True, timeout=10)

            # 重新访问签到页面来确认最终状态
            time.sleep(random.uniform(1, 2))
            r3 = sess.get(_URL_DAILY, headers=hdr, timeout=10)
            verified_page = r3.text

            if _TEXT_SIGNED in verified_page:
                mc = re.search(r"已连续登录 (\d+) 天", verified_page)
                log.append(f"✅ 签到成功，连续 {mc.group(1) if mc else '?'} 天")
            elif _TEXT_SIGNED in r2.text:
                log.append("✅ 签到成功")
            else:
                log.append(f"⚠️ 签到请求已发 (HTTP {r2.status_code})，验证页返回 HTTP {r3.status_code}")

    # ---- 查询余额 ----
    try:
        rb = sess.get(_URL_BALANCE, headers=hdr, timeout=10)
        today = date.today().strftime('%Y-%m-%d')
        bm = re.search(rf'{today} \d+:\d+:\d+ \+\d+ .*?(\d+)\s*铜币', rb.text)
        if bm:
            log.append(f"💰 今日奖励 {bm.group(1)} 铜币")
        tree = html.fromstring(rb.text)
        bal = tree.xpath('//div[@class="balance_area bigger"]/text()')
        if len(bal) == 2:
            bal = ['0'] + bal
        if len(bal) >= 3:
            g, s, b = [x.strip() for x in bal[:3]]
            log.append(f"🏦 当前总余额：{g} 金币，{s} 银币，{b} 铜币")
    except Exception:
        pass

    # ---- 输出 & 推送 ----
    result = "\n".join(log)
    print(result)
    send_telegram(f"*V2EX 自动签到*\n\n{result}")


# -------------------------- 入口 --------------------------
if __name__ == "__main__":
    main()