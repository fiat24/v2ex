import os
import re
import time
from datetime import date, datetime

import requests
from lxml import html

# -------------------------- 配置变量 --------------------------
# 若设置了环境变量，将覆盖下方值
COOKIES_FALLBACK = 'null'  # ← 在此粘贴你的Cookie
BOT_TOKEN_FALLBACK = "null"  # ← 在此粘贴 Telegram Bot Token
CHAT_ID_FALLBACK = "null"  # ← 在此粘贴 Telegram Chat ID

# 若设置了环境变量，将覆盖上方值
COOKIES = os.getenv("V2EX_COOKIES") or COOKIES_FALLBACK
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or BOT_TOKEN_FALLBACK
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or CHAT_ID_FALLBACK

SESSION = requests.Session()
msg = []

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    # "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cookie": COOKIES,
    "DNT": "1",
    "Priority": "u=0, i",
    "Referer": "https://www.v2ex.com/",
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
}

# ------------------------ Telegram 推送 ------------------------

def send_telegram(msg: str):
    """使用 Telegram Bot 发送 Markdown 消息"""
    if not (BOT_TOKEN and CHAT_ID):
        print("未配置 Telegram Bot Token / Chat ID，跳过推送…")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    })
    if resp.status_code == 200 and resp.json().get("ok"):
        print("Telegram 推送成功")
    else:
        print("Telegram 推送失败：", resp.text)

# 获取 once
def get_once():
    url = "https://www.v2ex.com/mission/daily"
    r = SESSION.get(url, headers=HEADERS)

    global msg
    if "你要查看的页面需要先登录" in r.text:
        msg += [
            {"name": "登录信息", "value": "登录失败，Cookie 可能已经失效"}
        ]
        return "", False
    elif "每日登录奖励已领取" in r.text:
        msg += [
            {"name": "登录信息", "value": "每日登录奖励已领取，" + re.search(r"已连续登录 \d+ 天", r.text)[0]}
        ]
        return "", True

    match = re.search(r"once=(\d+)", r.text)
    if match:
        try:
            once = match.group(1)
            msg += [{"name": "登录信息", "value": "登录成功"}]
            return once, True
        except IndexError:
            return "", False
    else:
        return "", False


# 签到
def check_in(once):
    url = "https://www.v2ex.com/mission/daily/redeem?once=" + once
    headers = HEADERS.copy()
    headers["Referer"] = "https://www.v2ex.com/mission/daily"
    
    # 发送签到请求，允许跟随重定向（302 -> /mission/daily）
    r = SESSION.get(url, headers=headers, allow_redirects=True)
    
    # 验证签到结果
    if r.status_code == 200:
        if "每日登录奖励已领取" in r.text:
            print("✓ 签到请求成功（已领取）")
        elif "你要查看的页面需要先登录" in r.text:
            print("✗ 签到失败（未登录）")
        else:
            print("✓ 签到请求已发送")
    else:
        print(f"✗ 签到请求失败（状态码: {r.status_code}）")
    
    return r


# 查询
def query_balance():
    url = "https://www.v2ex.com/balance"
    r = SESSION.get(url, headers=HEADERS)
    tree = html.fromstring(r.content)

    # 签到结果
    global msg
    
    # 方法1: 直接从页面文本中查找今日签到奖励信息
    today_str = date.today().strftime('%Y-%m-%d')
    bonus_match = re.search(rf'{today_str} \d+:\d+:\d+ \+\d+ 每日登录奖励 (\d+) 铜币', r.text)
    
    if bonus_match:
        msg += [
            {"name": "签到信息", "value": f"今日签到成功，获得 {bonus_match.group(1)} 铜币"}
        ]
    else:
        # 方法2: 尝试用旧的匹配逻辑作为备用
        try:
            checkin_day_list = tree.xpath('//small[@class="gray"]/text()')
            if checkin_day_list:
                checkin_day_str = checkin_day_list[0]
                # 修复: 使用 datetime.strptime() 而不是 datetime.now().strptime()
                checkin_day = datetime.strptime(checkin_day_str, '%Y-%m-%d %H:%M:%S %z')
                if checkin_day.date() == date.today():
                    bonus = re.search(r'每日登录奖励 \d+ 铜币', r.text)
                    if bonus:
                        msg += [{"name": "签到信息", "value": bonus.group(0)}]
                    else:
                        msg += [{"name": "签到信息", "value": "签到成功（未找到奖励详情）"}]
                else:
                    msg += [{"name": "签到信息", "value": f"签到失败（最近签到: {checkin_day_str}）"}]
            else:
                msg += [{"name": "签到信息", "value": "签到失败（无法获取签到记录）"}]
        except Exception as e:
            msg += [{"name": "签到信息", "value": f"签到验证异常: {str(e)}"}]

    # 余额
    balance = tree.xpath('//div[@class="balance_area bigger"]/text()')
    if len(balance) == 2:
        balance = ['0'] + balance
    
    if len(balance) >= 3:
        golden, silver, bronze = [s.strip() for s in balance[:3]]
        msg += [
            {"name": "账户余额", "value": f"{golden} 金币，{silver} 银币，{bronze} 铜币"}
        ]
    else:
        msg += [{"name": "账户余额", "value": "无法获取余额信息"}]


def main():
    for i in range(3):
        try:
            once, success = get_once()
            if once:
                check_in(once)
            if success:
                query_balance()
        except AttributeError:
            if i < 3:
                time.sleep(3)
                print("checkin failed, try #{}".format(i + 1))
                continue
            else:
                raise
        break

    global msg
    result = "\n".join([f"{one.get('name')}: {one.get('value')}" for one in msg])
    
    # 构建 Telegram 消息
    telegram_msg = f"*V2EX 签到结果*\n\n{result}"
    send_telegram(telegram_msg)
    
    return result


if __name__ == '__main__':
    print(" V2EX 签到开始 ".center(60, "="))
    result = main()
    print(result)
    print(" V2EX 签到结束 ".center(60, "="), "\n")