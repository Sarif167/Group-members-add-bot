import os
import re
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import ChatPermissions
from aiohttp import web

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== FILTER ==========
@app.on_message(filters.group & filters.text)
async def filter_system(client, message):

    if message.sender_chat:
        return

    if not message.from_user:
        return

    member = await client.get_chat_member(message.chat.id, message.from_user.id)

    if member.status in ["administrator", "creator"]:
        return

    patterns = ["http", "t.me", "@"]

    if any(p in message.text.lower() for p in patterns):
        await message.delete()
        await message.reply("⚠ Links not allowed!")

# ========== HEALTH CHECK ==========
async def health(request):
    return web.Response(text="Bot running")

async def run_web():
    web_app = web.Application()
    web_app.router.add_get("/", health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# ========== MAIN ==========
async def main():
    await app.start()
    await run_web()
    print("Bot Started Successfully!")
    await idle()

asyncio.run(main())
