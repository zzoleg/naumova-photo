#!/usr/bin/env python3
"""Initialize the media database for Alena Naumova photographer site."""
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = "/var/www/site-ofskin/webroot/media.db"

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

# Insert initial reviews from wfolio
reviews_data = [
    ("Анастасия", "Алёна — не просто фотограф, это художник, который видит душу. Съёмка прошла на одном дыхании, результат превзошёл все ожидания. Спасибо за такие тёплые и живые кадры!", "https://www.instagram.com/", "", 1, 1),
    ("Екатерина", "Очень долго искала «своего» фотографа. После съёмки с Алёной поняла — нашла. Она создала невероятно уютную атмосферу, я забыла о камере и просто наслаждалась процессом. Фото — магия!", "https://www.instagram.com/", "", 1, 2),
    ("Мария", "Семейная съёмка с Алёной — это был наш лучший семейный день! Дети были в восторге, а мы получили кадры, которые будем пересматривать всю жизнь. Огромное спасибо!", "https://www.instagram.com/", "", 1, 3),
    ("Ольга", "Я всегда стеснялась камеры, но Алёна помогла мне раскрыться и увидеть себя по-новому. Фотографии получились очень красивыми и естественными. Обязательно приду ещё!", "https://www.instagram.com/", "", 1, 4),
    ("Виктория", "Love story с Алёной — это было волшебно! Она так тонко чувствует эмоции и умеет поймать самый важный момент. Спасибо за нашу историю любви в фотографиях ❤️", "https://www.instagram.com/", "", 1, 5),
]

c.executemany(
    "INSERT OR IGNORE INTO reviews (author, text, social_link, avatar, is_published, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
    reviews_data
)

# Initial settings
settings = [
    ('site_title', 'Alena Naumova — Женский и семейный фотограф Минск'),
    ('phone', '+375293247202'),
    ('whatsapp', 'https://wa.me/375293247202'),
    ('telegram', 'https://t.me/alena_naumova_photo'),
    ('instagram', 'https://www.instagram.com/alena_naumova_photo'),
    ('email', 'alena@naumova.photo'),
    ('city', 'Минск, Беларусь'),
    ('last_updated', datetime.now().isoformat()),
]

c.executemany(
    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
    settings
)

conn.commit()
conn.close()
print(f"Database created at {DB_PATH}")
print(f"  - media table: ready for photos/videos")
print(f"  - reviews table: 5 sample reviews inserted")
print(f"  - settings table: contact info saved")