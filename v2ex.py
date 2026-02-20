#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, time, random, base64
from datetime import date
import requests
from lxml import html

COOKIES_FALLBACK = '''null'''
BOT_TOKEN_FALLBACK = '''null'''
CHAT_ID_FALLBACK = '''null'''

COOKIES = os.getenv("V2EX_COOKIES") or COOKIES_FALLBACK
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or BOT_TOKEN_FALLBACK
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or CHAT_ID_FALLBACK

_d = lambda s: base64.b64decode(s).decode()

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

def fix_cookies(raw):
    s = raw.strip().strip("'\"")
    s = re.sub(r'(?i)V2EX_LANG=[^;]*', 'V2EX_LANG=zhcn', s)
    if 'V2EX_LANG=zhcn' not in s:
        s += '; V2EX_LANG=zhcn'
    return s

def tg_push(text):
    if BOT_TOKEN == "null" or CHAT_ID == "null":
        return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def main():
    cookie = fix_cookies(COOKIES)
    if cookie == "null":
        print("没有配置 Cookie，检查环境变量 V2EX_COOKIES")
        return

    sess = requests.Session()
    hdr = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cookie": cookie,
        "Referer": _d(b"aHR0cHM6Ly93d3cudjJleC5jb20v"),
        "User-Agent": random.choice(UA_LIST),
    }
    log = []

    # 随机延时
    wait = random.uniform(2, 6)
    print(f"等待 {wait:.1f}s ...")
    time.sleep(wait)

    # 拿 once token
    r = sess.get(_d(b"aHR0cHM6Ly93d3cudjJleC5jb20vbWlzc2lvbi9kYWlseQ=="), headers=hdr, timeout=10)
    page = r.text

    if _d(b"5L2g6KaB5p+l55yL55qE6aG16Z2i6ZyA6KaB5YWI55m75b2V") in page or "Sign in" in page:
        log.append("❌ Cookie 失效，需要重新获取")
    elif _d(b"5q+P5pel55m75b2V5aWW5Yqx5bey6aKG5Y+W") in page:
        m = re.search(r"已连续登录 (\d+) 天", page)
        log.append(f"✅ 已签到，连续 {m.group(1) if m else '?'} 天")
    else:
        m = re.search(r"once=(\d+)", page)
        if not m:
            log.append("❌ 找不到 once，页面结构可能变了")
        else:
            once = m.group(1)
            time.sleep(random.uniform(1, 3))
            h2 = hdr.copy()
            h2["Referer"] = _d(b"aHR0cHM6Ly93d3cudjJleC5jb20vbWlzc2lvbi9kYWlseQ==")
            r2 = sess.get(_d(b"aHR0cHM6Ly93d3cudjJleC5jb20vbWlzc2lvbi9kYWlseS9yZWRlZW0/b25jZT0=") + once,
                          headers=h2, allow_redirects=True, timeout=10)
            if _d(b"5q+P5pel55m75b2V5aWW5Yqx5bey6aKG5Y+W") in r2.text:
                log.append("✅ 签到成功")
            else:
                log.append(f"⚠️ 签到请求已发，状态未确认 (HTTP {r2.status_code})")

    # 查余额
    try:
        rb = sess.get(_d(b"aHR0cHM6Ly93d3cudjJleC5jb20vYmFsYW5jZQ=="), headers=hdr, timeout=10)
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
            log.append(f"🏦 余额 {g} 金 {s} 银 {b} 铜")
    except:
        pass

    result = "\n".join(log)
    print(result)
    tg_push(f"*V2EX 签到*\n\n{result}")

if __name__ == '__main__':
    main()