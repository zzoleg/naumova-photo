#!/usr/bin/env python3
"""Check for new contact form submissions and forward to Telegram."""
import os
import json
import urllib.request
import urllib.parse

ENV_FILE = "/root/projects/pixel-site/.env"
CONTACT_LOG = "/var/www/site-ofskin/webroot/contact_requests.jsonl"
LAST_CHECK = "/tmp/naumova_contact_last_check"

def get_env(key):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1]
    return ""

def send_tg(text):
    token = get_env("CONTACT_BOT_TOKEN")
    chat_id = get_env("NAUMOVA_ALLOWED_USERS") or "387501011"
    if not token or token == "your_bot_token_here":
        return False
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id.split(",")[0].strip(),
            "text": text,
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

def main():
    if not os.path.exists(CONTACT_LOG):
        return
    
    last_pos = 0
    if os.path.exists(LAST_CHECK):
        with open(LAST_CHECK) as f:
            last_pos = int(f.read().strip() or "0")
    
    file_size = os.path.getsize(CONTACT_LOG)
    if file_size <= last_pos:
        return  # Nothing new
    
    # Read new lines
    new_lines = []
    with open(CONTACT_LOG) as f:
        f.seek(last_pos)
        new_lines = f.readlines()
    
    if not new_lines:
        # Still update position
        with open(LAST_CHECK, "w") as f:
            f.write(str(file_size))
        return
    
    for line in new_lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            text = (
                f"📸 <b>Новая заявка с сайта!</b>\n\n"
                f"👤 <b>Имя:</b> {data.get('name', '?')}\n"
                f"📞 <b>Контакты:</b> {data.get('contact', '?')}\n"
                f"💬 <b>Сообщение:</b>\n{data.get('message', '')}"
            )
            send_tg(text)
        except Exception as e:
            print(f"Error: {e}")
    
    with open(LAST_CHECK, "w") as f:
        f.write(str(file_size))

if __name__ == "__main__":
    main()