#!/usr/bin/env python3
"""
Telegram Admin Bot for Alena Naumova photographer site.
Allows uploading photos/videos, managing reviews, gallery, and settings.

Commands:
  /start - Приветствие и список команд
  /help - Справка
  /stats - Статистика сайта
  /gallery - Просмотр галереи фото
  /reviews - Управление отзывами
  /add_review <имя>|<текст> - Добавить отзыв
  /del_review <id> - Удалить отзыв
  /contacts - Показать контакты
  /set_contact <key>|<value> - Изменить контакт
  /upload - Загрузить фото/видео (отправьте файл после команды)
  
Simply send a photo or video file - it gets saved to the site automatically.
"""

import os
import sys
import json
import sqlite3
import requests
import time
import hashlib
import logging
import signal
from datetime import datetime
from pathlib import Path

# ========== CONFIG ==========
WEB_ROOT = "/var/www/site-ofskin/webroot"
PHOTOS_DIR = os.path.join(WEB_ROOT, "photos")
WFOLIO_DIR = os.path.join(WEB_ROOT, "wfolio-assets")
DB_PATH = os.path.join(WEB_ROOT, "media.db")
CONTACT_LOG = os.path.join(WEB_ROOT, "contact_requests.jsonl")

# Load bot token from environment
BOT_TOKEN = os.environ.get("NAUMOVA_BOT_TOKEN", "")
ALLOWED_USERS = os.environ.get("NAUMOVA_ALLOWED_USERS", "387501011")  # Oleg's chat ID

# ========== SETUP ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/var/log/naumova-bot.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("naumova-bot")

os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(WFOLIO_DIR, exist_ok=True)

def init_db():
    """Ensure database tables exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('photo', 'video')),
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sort_order INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            social_link TEXT DEFAULT '',
            avatar TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sort_order INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_reviews():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, author, text, created_at FROM reviews WHERE is_published=1 ORDER BY sort_order, id")
    rows = c.fetchall()
    conn.close()
    return rows

def add_review(author, text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM reviews")
    next_order = c.fetchone()[0]
    c.execute(
        "INSERT INTO reviews (author, text, sort_order) VALUES (?, ?, ?)",
        (author, text, next_order)
    )
    conn.commit()
    conn.close()
    return c.lastrowid

def del_review(review_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM reviews WHERE id=?", (review_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_media_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(CASE WHEN type='photo' THEN 1 ELSE 0 END) FROM media")
    total, photos = c.fetchone()
    c.execute("SELECT COUNT(*) FROM reviews WHERE is_published=1")
    reviews_count = c.fetchone()[0]
    conn.close()
    return total or 0, photos or 0, reviews_count or 0

def save_media_file(file_path, file_type="photo", title="", category=""):
    """Register a media file in the database."""
    if not os.path.exists(file_path):
        return False
    size = os.path.getsize(file_path)
    rel_path = os.path.relpath(file_path, WEB_ROOT)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO media (file_path, type, title, category, file_size, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
            (rel_path, file_type, title, category, size, int(time.time()))
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB error saving media: {e}")
        return False
    finally:
        conn.close()

def download_telegram_file(file_id, save_dir):
    """Download a file from Telegram. Returns full save path or None."""
    if not BOT_TOKEN:
        return None
    try:
        # Get file path
        resp = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=10
        )
        data = resp.json()
        if not data.get("ok"):
            log.error(f"getFile failed: {data}")
            return None
        
        file_path = data["result"]["file_path"]
        ext = file_path.split(".")[-1] if "." in file_path else "jpg"
        
        # Generate unique filename
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(file_path.encode()).hexdigest()[:8]
        filename = f"upload_{ts}_{hash_suffix}.{ext}"
        save_path = os.path.join(save_dir, filename)
        
        # Download file
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        resp = requests.get(download_url, timeout=60)
        with open(save_path, "wb") as f:
            f.write(resp.content)
        
        log.info(f"Downloaded {file_path} -> {save_path} ({len(resp.content)} bytes)")
        return save_path
    except Exception as e:
        log.error(f"Failed to download file: {e}")
        return None

# ========== TELEGRAM API ==========
def tg_send(chat_id, text, parse_mode="HTML", reply_markup=None):
    if not BOT_TOKEN:
        return None
    try:
        data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=data,
            timeout=10
        )
        return resp.json()
    except Exception as e:
        log.error(f"sendMessage error: {e}")
        return None

def tg_send_photo(chat_id, photo_path, caption=""):
    if not BOT_TOKEN:
        return None
    try:
        with open(photo_path, "rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                files={"photo": f},
                timeout=30
            )
        return resp.json()
    except Exception as e:
        log.error(f"sendPhoto error: {e}")
        return None

def tg_send_document(chat_id, doc_path, caption=""):
    if not BOT_TOKEN:
        return None
    try:
        with open(doc_path, "rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                files={"document": f},
                timeout=30
            )
        return resp.json()
    except Exception as e:
        log.error(f"sendDocument error: {e}")
        return None

# ========== COMMAND HANDLERS ==========
def cmd_start(chat_id):
    text = (
        "👋 <b>Админ-панель Naumova Photo</b>\n\n"
        "Управляй сайтом прямо из Telegram!\n\n"
        "📸 <b>Фото:</b>\n"
        "• Отправь фото — оно сохранится на сайт\n"
        "• Отправь альбом — сохранятся все фото\n\n"
        "🎥 <b>Видео:</b>\n"
        "• Отправь видео — сохранится на сайт\n\n"
        "📋 <b>Команды:</b>\n"
        "/stats — статистика сайта\n"
        "/gallery — последние загруженные фото\n"
        "/reviews — список отзывов\n"
        "/add_review Имя|Текст — добавить отзыв\n"
        "/del_review ID — удалить отзыв\n"
        "/contacts — контакты на сайте\n"
        "/set_contact телефон|+375XX — изменить контакт\n"
        "/help — подробная справка"
    )
    tg_send(chat_id, text)

def cmd_help(chat_id):
    text = (
        "📚 <b>Подробная справка</b>\n\n"
        "<b>Статистика:</b>\n"
        "/stats — статистика сайта (фото, видео, отзывы)\n"
        "/gallery — последние загруженные фото\n"
        "/requests — новые заявки с сайта\n\n"
        "<b>Загрузка фото:</b>\n"
        "1. Отправь фото в этот чат\n"
        "2. Бот сам сохранит его в /photos/ на сайте\n"
        "3. Фото появится в базе данных\n"
        "4. Чтобы добавить на сайт — обнови index.html\n\n"
        "<b>Загрузка нескольких фото:</b>\n"
        "Отправь альбом (несколько фото сразу)\n\n"
        "<b>Загрузка видео:</b>\n"
        "Отправь видеофайл — сохранится в /photos/\n\n"
        "<b>Управление отзывами:</b>\n"
        "/reviews — показать все отзывы\n"
        "/add_review Анастасия|Отличная съёмка!\n"
        "/del_review 3 — удалить отзыв #3\n\n"
        "<b>Контакты:</b>\n"
        "/contacts — показать контакты\n"
        "/set_contact телефон|+375****7202\n\n"
        "<b>Прочее:</b>\n"
        "/help — эта справка"
    )
    tg_send(chat_id, text)

def cmd_stats(chat_id):
    total, photos, reviews_count = get_media_stats()
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    # Count actual files
    real_photos = len([f for f in os.listdir(PHOTOS_DIR) if f.endswith(('.jpg','.jpeg','.png','.webp'))]) if os.path.exists(PHOTOS_DIR) else 0
    real_videos = len([f for f in os.listdir(PHOTOS_DIR) if f.endswith(('.mp4','.mov','.avi'))]) if os.path.exists(PHOTOS_DIR) else 0
    wfolio_photos = len(os.listdir(WFOLIO_DIR)) if os.path.exists(WFOLIO_DIR) else 0
    
    text = (
        "📊 <b>Статистика сайта</b>\n\n"
        f"📸 Фото на сервере: {real_photos}\n"
        f"🎥 Видео на сервере: {real_videos}\n"
        f"🖼 Wfolio-ассеты: {wfolio_photos}\n"
        f"📦 В БД media: {total}\n"
        f"⭐ Отзывов: {reviews_count}\n"
        f"🗄 БД: {db_size/1024:.0f} KB\n"
        f"📄 Заявок: {sum(1 for _ in open(CONTACT_LOG)) if os.path.exists(CONTACT_LOG) else 0}\n\n"
        f"🔗 <a href='https://148.222.186.199.nip.io:8444'>Открыть сайт</a>"
    )
    tg_send(chat_id, text)

def cmd_gallery(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT file_path, title, type, created_at FROM media ORDER BY created_at DESC LIMIT 10")
    items = c.fetchall()
    conn.close()
    
    if not items:
        tg_send(chat_id, "📭 Галерея пуста. Отправь фото, чтобы добавить!")
        return
    
    text = "🖼 <b>Последние загруженные:</b>\n\n"
    for i, (path, title, ftype, ts) in enumerate(items, 1):
        short = title or os.path.basename(path)
        icon = "🎥" if ftype == "video" else "📸"
        text += f"{i}. {icon} {short}\n   <code>{path}</code>\n"
    
    # Send the most recent photo preview
    recent_photo = items[0][0] if items else None
    if recent_photo:
        full_path = os.path.join(WEB_ROOT, recent_photo)
        if os.path.exists(full_path):
            tg_send_photo(chat_id, full_path, text[:1024])
            return
    tg_send(chat_id, text)

def cmd_reviews(chat_id):
    reviews = get_reviews()
    if not reviews:
        tg_send(chat_id, "⭐ Отзывов пока нет.")
        return
    
    text = "⭐ <b>Отзывы:</b>\n\n"
    for rid, author, rtext, ts in reviews:
        short = rtext[:80] + "..." if len(rtext) > 80 else rtext
        text += f"#{rid} <b>{author}</b>: {short}\n"
    text += "\n/add_review Имя|Текст — добавить\n/del_review ID — удалить"
    tg_send(chat_id, text)

def cmd_add_review(chat_id, args):
    if "|" not in args:
        tg_send(chat_id, "❌ Формат: /add_review Имя|Текст отзыва")
        return
    author, text = args.split("|", 1)
    author = author.strip()
    text = text.strip()
    if not author or not text:
        tg_send(chat_id, "❌ Имя и текст не могут быть пустыми")
        return
    rid = add_review(author, text)
    tg_send(chat_id, f"✅ Отзыв #{rid} добавлен:\n<b>{author}</b>: {text[:100]}")

def cmd_del_review(chat_id, args):
    try:
        rid = int(args.strip())
        if del_review(rid):
            tg_send(chat_id, f"✅ Отзыв #{rid} удалён")
        else:
            tg_send(chat_id, f"❌ Отзыв #{rid} не найден")
    except ValueError:
        tg_send(chat_id, "❌ Укажите ID отзыва: /del_review 3")

def cmd_contacts(chat_id):
    contacts = []
    for key in ["phone", "whatsapp", "telegram", "instagram", "email", "city"]:
        val = get_setting(key)
        if val:
            contacts.append(f"{key}: {val}")
    
    text = "📞 <b>Контакты на сайте:</b>\n\n" + "\n".join(contacts) if contacts else "📞 Контакты не настроены"
    text += "\n\n/set_contact ключ|значение — изменить"
    tg_send(chat_id, text)

def cmd_set_contact(chat_id, args):
    if "|" not in args:
        tg_send(chat_id, "❌ Формат: /set_contact ключ|значение\nКлючи: phone, whatsapp, telegram, instagram, email, city")
        return
    key, value = args.split("|", 1)
    key = key.strip().lower()
    value = value.strip()
    set_setting(key, value)
    tg_send(chat_id, f"✅ Контакт <b>{key}</b> обновлён: {value}")

def cmd_requests(chat_id):
    if not os.path.exists(CONTACT_LOG):
        tg_send(chat_id, "📭 Новых заявок нет")
        return
    
    with open(CONTACT_LOG) as f:
        lines = f.readlines()
    
    if not lines:
        tg_send(chat_id, "📭 Новых заявок нет")
        return
    
    # Show last 5 requests
    text = "📬 <b>Последние заявки с сайта:</b>\n\n"
    for line in lines[-5:]:
        try:
            data = json.loads(line.strip())
            text += f"👤 {data['name']} ({data['contact']})\n💬 {data['message'][:60]}\n🕐 {data['time'][:16]}\n\n"
        except:
            pass
    
    tg_send(chat_id, text)

# ========== MAIN BOT LOOP ==========
def process_update(update):
    """Process a single Telegram update."""
    if "message" not in update:
        return
    
    msg = update["message"]
    chat_id = str(msg["chat"]["id"])
    user_id = str(msg["from"]["id"])
    
    # Check access
    allowed = [u.strip() for u in ALLOWED_USERS.split(",")]
    if allowed and user_id not in allowed:
        log.warning(f"Blocked user {user_id}")
        return
    
    # Handle photo upload
    if "photo" in msg:
        # Get the largest photo
        photos = msg["photo"]
        best = photos[-1]["file_id"]
        file_path = download_telegram_file(best, PHOTOS_DIR)
        if file_path:
            caption = msg.get("caption", "")
            save_media_file(file_path, "photo", caption)
            tg_send_photo(chat_id, file_path, 
                f"✅ Фото сохранено!\n📁 {os.path.relpath(file_path, WEB_ROOT)}")
        else:
            tg_send(chat_id, "❌ Не удалось загрузить фото")
        return
    
    # Handle video upload
    if "video" in msg:
        video = msg["video"]
        file_id = video["file_id"]
        file_path = download_telegram_file(file_id, PHOTOS_DIR)
        if file_path:
            caption = msg.get("caption", "")
            save_media_file(file_path, "video", caption)
            rel = os.path.relpath(file_path, WEB_ROOT)
            tg_send(chat_id, 
                f"✅ Видео сохранено!\n📁 {rel}\n\nЧтобы оно появилось на сайте, обнови портфолио")
        else:
            tg_send(chat_id, "❌ Не удалось загрузить видео")
        return
    
    # Handle document upload (could be video too)
    if "document" in msg:
        doc = msg["document"]
        mime = doc.get("mime_type", "")
        file_id = doc["file_id"]
        
        if "video" in mime or "mp4" in mime:
            file_path = download_telegram_file(file_id, PHOTOS_DIR)
            if file_path:
                save_media_file(file_path, "video", msg.get("caption", ""))
                tg_send(chat_id, f"✅ Видео-файл сохранён в /photos/")
            else:
                tg_send(chat_id, "❌ Не удалось загрузить видео")
        else:
            tg_send(chat_id, "📄 Документ получен, но поддерживаются только фото и видео")
        return
    
    # Handle text commands
    if "text" not in msg:
        return
    
    text = msg["text"].strip()
    
    if text == "/start":
        cmd_start(chat_id)
    elif text == "/help":
        cmd_help(chat_id)
    elif text == "/stats":
        cmd_stats(chat_id)
    elif text == "/gallery":
        cmd_gallery(chat_id)
    elif text == "/reviews":
        cmd_reviews(chat_id)
    elif text.startswith("/add_review"):
        args = text[len("/add_review"):].strip()
        cmd_add_review(chat_id, args)
    elif text.startswith("/del_review"):
        args = text[len("/del_review"):].strip()
        cmd_del_review(chat_id, args)
    elif text == "/contacts":
        cmd_contacts(chat_id)
    elif text.startswith("/set_contact"):
        args = text[len("/set_contact"):].strip()
        cmd_set_contact(chat_id, args)
    elif text == "/requests":
        cmd_requests(chat_id)
    elif text.startswith("/"):
        tg_send(chat_id, f"❌ Неизвестная команда: {text}\n/help — список команд")

def run_bot():
    """Main bot polling loop."""
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        log.error("NAUMOVA_BOT_TOKEN not set! Create a bot via @BotFather and set the token.")
        log.error("Export: export NAUMOVA_BOT_TOKEN=123456:ABC-DEF...")
        log.error("Then run this script again.")
        print("=" * 50)
        print("❌ NAUMOVA_BOT_TOKEN не указан!")
        print("")
        print("1. Открой @BotFather в Telegram")
        print("2. Создай нового бота: /newbot")
        print("3. Назови, например: Naumova Admin Bot")
        print("4. Скопируй токен")
        print("5. Запусти скрипт с токеном:")
        print("   export NAUMOVA_BOT_TOKEN=123456789:ABCdef...")
        print("   python3 naumova-admin-bot.py")
        print("=" * 50)
        return False
    
    offset = 0
    log.info(f"Starting Naumova Admin Bot...")
    log.info(f"Web root: {WEB_ROOT}")
    log.info(f"DB: {DB_PATH}")
    log.info(f"Allowed users: {ALLOWED_USERS}")
    
    # Send startup notification
    for uid in ALLOWED_USERS.split(","):
        uid = uid.strip()
        if uid:
            tg_send(uid, "🟢 <b>Админ-бот Naumova запущен!</b>\n\nОтправляй фото — они попадут на сайт.\n/help — список команд")
    
    # Polling loop with exponential backoff
    backoff = 1
    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": json.dumps(["message"]),
                },
                timeout=35,
            )
            data = resp.json()
            
            if data.get("ok"):
                backoff = 1  # Reset backoff on success
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        process_update(update)
                    except Exception as e:
                        log.error(f"Error processing update {update['update_id']}: {e}")
            else:
                log.error(f"API error: {data}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                
        except requests.exceptions.Timeout:
            # Timeout is normal with long polling
            pass
        except requests.exceptions.ConnectionError as e:
            log.error(f"Connection error: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    init_db()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        log.info("Shutting down...")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    run_bot()