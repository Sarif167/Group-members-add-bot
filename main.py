import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import web

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

app = Client(
    "force_add_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_added_count = {}

@app.on_message(filters.group & filters.new_chat_members)
async def count_added_members(client, message: Message):
    if message.from_user:
        inviter = message.from_user.id
        added_members = len(message.new_chat_members)

        user_added_count[inviter] = user_added_count.get(inviter, 0) + added_members


@app.on_message(filters.group & filters.text)
async def check_member_added(client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id

    member = await app.get_chat_member(message.chat.id, user_id)
    if member.status in ["administrator", "creator"]:
        return

    added = user_added_count.get(user_id, 0)

    if added < 4:
        try:
            await message.delete()
            await message.reply_text("⚠️ Pehle 4 members add karo phir message karo!")
        except:
            pass


# -------- Health Check Server --------
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get("/", handle)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()


async def main():
    await start_web_server()
    await app.start()
    print("Bot Started Successfully!")
    await idle()

from pyrogram import idle

asyncio.run(main())
