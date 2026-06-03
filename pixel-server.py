#!/usr/bin/env python3
"""HTTPS server for Alena Naumova photographer site.
Serves static files + contact form + admin panel for bot token setup."""

import http.server
import ssl
import os
import sys
import signal
import json
import urllib.request
import urllib.parse
import subprocess
import secrets
import time

PORT = 8444
WEBROOT = "/var/www/site-ofskin/webroot"
CERT = "/etc/letsencrypt/live/148.222.186.199.nip.io/fullchain.pem"
KEY = "/etc/letsencrypt/live/148.222.186.199.nip.io/privkey.pem"
ENV_FILE = "/root/projects/pixel-site/.env"
BOT_SERVICE = "naumova-admin-bot.service"

def load_env_var(key, default=""):
    """Read a single variable from .env file."""
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + "="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val
    except Exception:
        pass
    return default

def save_env_var(key, value):
    """Update a single variable in .env file (replaces or appends)."""
    lines = []
    found = False
    try:
        with open(ENV_FILE) as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass
    
    with open(ENV_FILE, "w") as f:
        for line in lines:
            if line.startswith(key + "="):
                f.write(f"{key}={value}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key}={value}\n")


ADMIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Naumova — Админ-панель</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700&family=EB+Garamond:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root { --bg: #0a0a0a; --text: #e5dfd3; --muted: #8a857b; --accent: #d4883a; --accent-light: #e8a74d; --font-serif: 'EB Garamond', serif; --font-sans: 'Barlow', sans-serif; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--text); font-family: var(--font-sans); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.container { max-width: 500px; width: 100%; padding: 40px 24px; text-align: center; }
.logo { font-family: var(--font-serif); font-size: 1.5rem; letter-spacing: .15em; margin-bottom: 8px; }
.subtitle { color: var(--muted); font-size: .85rem; margin-bottom: 40px; }
.card { background: #111; border: 1px solid #222; border-radius: 12px; padding: 32px; text-align: left; }
h2 { font-family: var(--font-serif); font-size: 1.3rem; margin-bottom: 20px; text-align: center; }
label { display: block; font-size: .8rem; color: var(--muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: .1em; }
input { width: 100%; padding: 12px 16px; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: var(--text); font-family: var(--font-sans); font-size: .95rem; outline: none; transition: border .3s; margin-bottom: 16px; }
input:focus { border-color: var(--accent); }
.btn { width: 100%; padding: 12px; background: var(--accent); color: #0a0a0a; border: none; border-radius: 8px; font-family: var(--font-sans); font-size: .9rem; font-weight: 600; cursor: pointer; transition: background .3s; }
.btn:hover { background: var(--accent-light); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.status { margin-top: 16px; padding: 12px 16px; border-radius: 8px; font-size: .85rem; display: none; }
.status.info { display: block; background: rgba(212, 136, 58, .15); border: 1px solid var(--accent); color: var(--accent); }
.status.ok { display: block; background: rgba(76, 175, 80, .15); border: 1px solid #4caf50; color: #4caf50; }
.status.err { display: block; background: rgba(244, 67, 54, .15); border: 1px solid #f44336; color: #f44336; }
.step { transition: opacity .3s; }
.step-hidden { display: none; }
.spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(10,10,10,.3); border-top-color: #0a0a0a; border-radius: 50%; animation: spin .6s linear infinite; vertical-align: middle; margin-right: 8px; }
@keyframes spin { to { transform: rotate(360deg); } }
.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0; }
.stat-box { background: #1a1a1a; border: 1px solid #222; border-radius: 8px; padding: 16px; text-align: center; }
.stat-num { font-size: 1.6rem; font-weight: 700; color: var(--accent); }
.stat-label { font-size: .75rem; color: var(--muted); margin-top: 4px; }
.back-link { display: inline-block; margin-top: 24px; color: var(--muted); text-decoration: none; font-size: .85rem; }
.back-link:hover { color: var(--accent); }
</style>
</head>
<body>
<div class="container">
  <div class="logo">Naumova</div>
  <div class="subtitle">Админ-панель</div>

  <!-- Step 1: Password -->
  <div class="card" id="step1">
    <h2>🔐 Вход</h2>
    <label for="pwd">Пароль администратора</label>
    <input type="password" id="pwd" placeholder="Введите пароль" onkeydown="if(event.key==='Enter') verifyPwd()">
    <button class="btn" id="loginBtn" onclick="verifyPwd()">Войти</button>
    <div class="status" id="pwdStatus"></div>
  </div>

  <!-- Step 2: Token setup (hidden initially) -->
  <div class="card step-hidden" id="step2">
    <h2>🤖 Telegram-бот</h2>

    <div id="botStatusPanel"></div>

    <div id="tokenSetup">
      <p style="color:var(--muted);font-size:.85rem;margin-bottom:20px;line-height:1.5">
        Создай бота в <a href="https://t.me/BotFather" target="_blank" style="color:var(--accent)">@BotFather</a>,
        скопируй токен и вставь ниже.
      </p>
      <label for="token">Токен бота</label>
      <input type="text" id="token" placeholder="1234567890:ABCdefGHIjklmNOPqrstUVwxyz" onkeydown="if(event.key==='Enter') saveToken()">
      <button class="btn" id="saveBtn" onclick="saveToken()">💾 Сохранить и запустить</button>
      <div class="status" id="tokenStatus"></div>
    </div>
  </div>

  <a href="/" class="back-link">← На сайт</a>
</div>

<script>
let verified = false;

function setStatus(el, type, msg) {
  el.className = 'status ' + type;
  el.textContent = msg;
  el.style.display = 'block';
}

async function verifyPwd() {
  const pwd = document.getElementById('pwd').value;
  const btn = document.getElementById('loginBtn');
  const status = document.getElementById('pwdStatus');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Проверка...';
  try {
    const resp = await fetch('/api/admin/verify-password', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({password: pwd})
    });
    const data = await resp.json();
    if (data.success) {
      verified = true;
      document.getElementById('step1').style.display = 'none';
      document.getElementById('step2').classList.remove('step-hidden');
      checkBotStatus();
    } else {
      setStatus(status, 'err', '❌ Неверный пароль');
    }
  } catch(e) {
    setStatus(status, 'err', '❌ Ошибка соединения: ' + e.message);
  }
  btn.disabled = false;
  btn.textContent = 'Войти';
}

async function checkBotStatus() {
  const panel = document.getElementById('botStatusPanel');
  const setup = document.getElementById('tokenSetup');
  try {
    const resp = await fetch('/api/admin/status');
    const data = await resp.json();
    if (data.token_set) {
      panel.innerHTML = '<div class="status ok">✅ Бот настроен</div>';
      if (data.bot_running) {
        panel.innerHTML += '<div class="status ok">🟢 Бот запущен</div>';
        setup.style.display = 'none';
      } else {
        panel.innerHTML += '<div class="status err">🔴 Бот не запущен</div>';
      }
    } else {
      panel.innerHTML = '<div class="status info">⚙️ Требуется настройка токена</div>';
    }
  } catch(e) {
    panel.innerHTML = '<div class="status info">⚙️ Проверка статуса...</div>';
  }
}

async function saveToken() {
  const token = document.getElementById('token').value.trim();
  const btn = document.getElementById('saveBtn');
  const status = document.getElementById('tokenStatus');
  if (!token || token.length < 20) {
    setStatus(status, 'err', '❌ Токен выглядит некорректным');
    return;
  }
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Проверка токена...';
  try {
    const resp = await fetch('/api/admin/set-token', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        password: document.getElementById('pwd').value,
        token: token,
        contact_token: token
      })
    });
    const data = await resp.json();
    if (data.success) {
      setStatus(status, 'ok', '✅ ' + data.message);
      setTimeout(() => checkBotStatus(), 2000);
    } else {
      setStatus(status, 'err', '❌ ' + data.message);
    }
  } catch(e) {
    setStatus(status, 'err', '❌ Ошибка: ' + e.message);
  }
  btn.disabled = false;
  btn.textContent = '💾 Сохранить и запустить';
}
</script>
</body>
</html>"""


def send_telegram_message(text):
    """Send a message to the admin's Telegram."""
    token = load_env_var("CONTACT_BOT_TOKEN")
    if not token:
        return False
    try:
        data = urllib.parse.urlencode({
            "chat_id": "387501011",
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
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to send Telegram: {e}\n")
        return False


def test_telegram_token(token):
    """Test if a Telegram bot token is valid using getMe."""
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            method="GET",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        if data.get("ok"):
            bot_info = data.get("result", {})
            return True, bot_info.get("first_name", "Bot"), bot_info.get("username", "")
        return False, data.get("description", "Invalid token"), ""
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err_data = json.loads(body)
            return False, err_data.get("description", f"HTTP {e.code}"), ""
        except:
            return False, f"HTTP {e.code}: {body}", ""
    except Exception as e:
        return False, str(e), ""


def restart_bot_service():
    """Restart the naumova admin bot systemd service."""
    try:
        subprocess.run(
            ["systemctl", "restart", BOT_SERVICE],
            capture_output=True, timeout=15,
        )
        # Wait a moment and check if it started
        time.sleep(2)
        result = subprocess.run(
            ["systemctl", "is-active", BOT_SERVICE],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() == "active"
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to restart bot service: {e}\n")
        return False


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBROOT, **kwargs)

    def do_GET(self):
        if self.path == "/admin":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(ADMIN_HTML.encode("utf-8"))
            return
        if self.path == "/api/admin/status":
            self.handle_admin_status()
            return
        super().do_GET()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")

        if self.path == "/api/admin/verify-password":
            self.handle_verify_password(body)
        elif self.path == "/api/admin/set-token":
            self.handle_set_token(body)
        elif self.path == "/api/admin/status":
            self.handle_admin_status()
        elif self.path == "/api/contact":
            self.handle_contact(body)
        elif self.path == "/api/upload" and self.headers.get("X-Admin-Key", "") == load_env_var("ADMIN_API_KEY"):
            self.handle_upload(body)
        else:
            self.send_json(404, {"error": "Not found"})

    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def handle_verify_password(self, body):
        try:
            data = json.loads(body)
            pwd = data.get("password", "")
            expected = load_env_var("ADMIN_PASSWORD")
            if not expected:
                self.send_json(200, {"success": False, "message": "Пароль не настроен в .env"})
                return
            self.send_json(200, {"success": pwd == expected})
        except Exception as e:
            self.send_json(200, {"success": False, "message": str(e)})

    def handle_admin_status(self):
        token = load_env_var("NAUMOVA_BOT_TOKEN")
        token_set = bool(token)
        bot_running = False
        if token_set:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", BOT_SERVICE],
                    capture_output=True, text=True, timeout=10,
                )
                bot_running = result.stdout.strip() == "active"
            except:
                pass
        self.send_json(200, {
            "token_set": token_set,
            "bot_running": bot_running,
        })

    def handle_set_token(self, body):
        try:
            data = json.loads(body)
            # Verify password
            pwd = data.get("password", "")
            expected = load_env_var("ADMIN_PASSWORD")
            if not expected or pwd != expected:
                self.send_json(200, {"success": False, "message": "Неверный пароль"})
                return

            token = data.get("token", "").strip()
            contact_token = data.get("contact_token", "").strip()

            if not token:
                self.send_json(200, {"success": False, "message": "Токен не может быть пустым"})
                return

            # Test the token with Telegram API
            valid, name, username = test_telegram_token(token)
            if not valid:
                self.send_json(200, {"success": False, "message": f"Токен недействителен: {name}"})
                return

            # Save to .env
            save_env_var("NAUMOVA_BOT_TOKEN", token)
            if contact_token:
                save_env_var("CONTACT_BOT_TOKEN", contact_token)

            # Restart the bot service
            started = restart_bot_service()
            msg = f"🤖 Бот @{username} ({name}) настроен!"
            if started:
                msg += " Бот запущен и работает. Открой Telegram и напиши /start."
            else:
                msg += " Бот не запустился автоматически — проверь systemctl status naumova-admin-bot"

            self.send_json(200, {"success": True, "message": msg, "bot_name": name, "bot_username": username})
        except Exception as e:
            self.send_json(200, {"success": False, "message": f"Ошибка: {str(e)}"})

    def handle_contact(self, body):
        """Handle contact form submission."""
        try:
            data = json.loads(body)
            name = data.get("name", "Не указано")
            contact = data.get("contact", "Не указано")
            message = data.get("message", "")

            # Send to Telegram
            text = (
                f"📸 <b>Новая заявка с сайта Naumova</b>\n\n"
                f"👤 <b>Имя:</b> {name}\n"
                f"📞 <b>Контакты:</b> {contact}\n"
                f"💬 <b>Сообщение:</b>\n{message}"
            )
            sent = send_telegram_message(text)

            # Also log to file
            log_entry = json.dumps({
                "name": name, "contact": contact, "message": message,
                "time": __import__("datetime").datetime.now().isoformat(),
                "ip": self.client_address[0],
            }, ensure_ascii=False)
            log_file = os.path.join(WEBROOT, "contact_requests.jsonl")
            with open(log_file, "a") as f:
                f.write(log_entry + "\n")

            self.send_json(200, {
                "success": True,
                "message": "Спасибо! Ваше сообщение отправлено. Я свяжусь с вами в ближайшее время."
            })
        except Exception as e:
            self.send_json(400, {"error": str(e)})

    def handle_upload(self, body):
        """Handle file upload from admin bot."""
        try:
            data = json.loads(body)
            url = data.get("url", "")
            file_type = data.get("type", "photo")
            title = data.get("title", "")
            category = data.get("category", "")
            file_id = data.get("file_id", "")

            if not url and not file_id:
                self.send_json(400, {"error": "No URL or file_id"})
                return

            self.send_json(200, {"success": True, "message": "File queued for processing"})
        except Exception as e:
            self.send_json(400, {"error": str(e)})

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s - %s\n" % (self.log_date_time_string(), self.client_address[0], fmt % args))


def run():
    try:
        server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
        server.socket = ssl.wrap_socket(
            server.socket,
            certfile=CERT,
            keyfile=KEY,
            server_side=True,
        )
        print(f"Serving pixel-site on https://0.0.0.0:{PORT}")
        print(f"Admin panel: https://0.0.0.0:{PORT}/admin")
        sys.stdout.flush()
        server.serve_forever()
    except OSError as e:
        print(f"ERROR: {e}")
        if "Address already in use" in str(e):
            print("Port already in use - another server is running")
        sys.exit(1)


if __name__ == "__main__":
    run()