import os
import re
import time
import asyncio
import sqlite3
from pyrogram import Client, filters, idle
from pyrogram.types import ChatPermissions
from pyrogram.errors import FloodWait
from aiohttp import web

# ---------------- CONFIG ----------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("force_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    added INTEGER DEFAULT 0,
    warnings INTEGER DEFAULT 0,
    mute_until INTEGER DEFAULT 0,
    chat_id INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------------- TRACK ADDED MEMBERS ----------------
@app.on_message(filters.group & filters.new_chat_members)
async def track_members(client, message):
    if not message.from_user:
        return

    inviter = message.from_user.id
    count = len([m for m in message.new_chat_members if not m.is_bot])

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (inviter,))
    cursor.execute("UPDATE users SET added = added + ? WHERE user_id=?", (count, inviter))
    conn.commit()

# ---------------- FILTER SYSTEM ----------------
@app.on_message(filters.group & filters.text)
async def filter_system(client, message):

    # Ignore channel posts
    if message.sender_chat:
        return

    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    member = await client.get_chat_member(chat_id, user_id)
    if member.status in ["administrator", "creator"]:
        return

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    patterns = [r"https?://", r"t\.me/", r"@", r"youtube\.com", r"youtu\.be"]
    if any(re.search(p, message.text.lower()) for p in patterns):
        await punish(chat_id, user_id, message)
        return

    cursor.execute("SELECT added FROM users WHERE user_id=?", (user_id,))
    added = cursor.fetchone()[0]

    if added < 4:
        await punish(chat_id, user_id, message)

# ---------------- PUNISH ----------------
async def punish(chat_id, user_id, message):
    await message.delete()

    cursor.execute("SELECT warnings FROM users WHERE user_id=?", (user_id,))
    warnings = cursor.fetchone()[0] + 1

    if warnings >= 2:
        mute_until = int(time.time()) + 1200

        await app.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions()
        )

        cursor.execute("""
        UPDATE users 
        SET warnings=0, mute_until=?, chat_id=? 
        WHERE user_id=?
        """, (mute_until, chat_id, user_id))
        conn.commit()

        await app.send_message(chat_id, "🔇 User muted for 20 minutes!")

    else:
        cursor.execute("UPDATE users SET warnings=? WHERE user_id=?",
                       (warnings, user_id))
        conn.commit()

        await app.send_message(chat_id, f"⚠ Warning {warnings}/2")

# ---------------- AUTO UNMUTE ----------------
async def check_mutes():
    while True:
        now = int(time.time())

        cursor.execute("""
        SELECT user_id, chat_id FROM users 
        WHERE mute_until <= ? AND mute_until > 0
        """, (now,))
        users = cursor.fetchall()

        for user_id, chat_id in users:
            await app.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )

            cursor.execute("UPDATE users SET mute_until=0 WHERE user_id=?", (user_id,))
            conn.commit()

            await app.send_message(chat_id, "🔓 User automatically unmuted!")

        await asyncio.sleep(30)

# ---------------- HEALTH CHECK ----------------
async def health(request):
    return web.Response(text="Bot running")

async def run_web():
    app_web = web.Application()
    app_web.router.add_get("/", health)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# ---------------- MAIN ----------------
async def main():
    print("Bot Starting...")

    while True:
        try:
            await app.start()
            break
        except FloodWait as e:
            print(f"FloodWait: Sleeping {e.value}s")
            await asyncio.sleep(e.value)

    asyncio.create_task(check_mutes())
    await run_web()

    print("Bot Started Successfully!")
    await idle()

asyncio.run(main())
