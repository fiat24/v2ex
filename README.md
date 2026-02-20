# V2EX 签到

青龙面板用的 V2EX 每日签到脚本，支持 Telegram 推送。

## 用法

### 1. 拿 Cookie

浏览器登录 [V2EX](https://www.v2ex.com/)，`F12` 打开开发者工具，Network 里随便点一个请求，把 Request Headers 里的 `Cookie` 整行复制出来。

### 2. 青龙面板配环境变量

| 变量名 | 值 | 必填 |
|---|---|---|
| `V2EX_COOKIES` | 上面复制的 Cookie | ✅ |
| `TELEGRAM_BOT_TOKEN` | TG 机器人 Token | 可选 |
| `TELEGRAM_CHAT_ID` | TG 聊天 ID | 可选 |

### 3. 建定时任务

- 命令：`task v2ex.py`
- 定时：`0 9 * * *`
