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

# Insert real reviews from wfolio
reviews_data = [
    ("Светлана", "Алена фотки супер!!! Только что с детьми смотрели им очень понравилось!!! и мне конечно)", "", 1, 1),
    ("Ольга", "Очень интересный взгляд изнутри", "", 1, 2),
    ("Анна", "Спасибо огромное за прекрасные фото и память!", "", 1, 3),
    ("Таццяна", "Алена! Я хочу поблагодарить тебя за меня настоящую на твоих фото♥️ Наша подготовка и сам процесс были очень легкие, вдохновляющие и расслабляющие! Когда я получила фото, просматривала все с улыбкой и большой благодарностью — за честность, искренность. Я на твоих фото живая и настоящая, спасибо тебе, что рассмотрела и показала меня. Спасибо тебе за меня♥️", "", 1, 4),
    ("Вероника", "Алена, благодарю тебя за чудесные кадры, фото позволили увидеть себя красивую, яркую, интересную, сильную, но в тоже время женственную!!! Восхищаюсь тем, как тебе удается подловить момент и запечатлить эмоцию, у тебя настоящий дар!!! ✨❤️", "", 1, 5),
    ("Татьяна", "Наша съемка была про честность. Про меня без прикрас. Получилось красиво и искренне... После нашей съемки люблю свои морщинки, веснушки, неидеальности еще больше! Спасибо, Алёна♥️🫂 Обязательно приду ещё!", "@tacciana_gotto", 1, 6),
    ("Екатерина", "Алёна, твои фотографии волшебны! Для меня это искусство. Съёмка получилась живая, лёгкая. Мне очень комфортно с тобой работать. Жду с нетерпением следующий раз. Спасибо за твоё видение меня.", "@katarios_vi", 1, 7),
    ("Яна", "Моя великолепная талантливейшая волшебница!!!!! Спасибо что словила объективом моего внутреннего чертенка и ранимую девочку... Твои фотографии передают всю глубину чувств — ты видишь нас настоящих. Благодаря тебе я вижу себя красивой и знакомлюсь с собой.", "", 1, 8),
    ("Анастасия", "Спасибо за невероятные эмоции, которые я получаю, глядя на эти фото!", "", 1, 9),
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