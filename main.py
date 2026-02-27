import os
import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

app = Client("smart_force_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

db = mongo["force_bot"]
users_db = db["users"]
mute_db = db["mutes"]

@app.on_message(filters.group & filters.new_chat_members)
async def track_members(client, message):
    if not message.from_user:
        return

    inviter_id = message.from_user.id

    for member in message.new_chat_members:
        if member.is_bot or member.is_deleted:
            continue

        await users_db.update_one(
            {"_id": inviter_id},
            {"$addToSet": {"added_members": member.id}},
            upsert=True
        )

@app.on_message(filters.group)
async def filter_system(client, message):

    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    member = await client.get_chat_member(chat_id, user_id)
    if member.status in ["administrator", "creator"]:
        return

    if message.text:
        patterns = [r"https?://", r"t\.me/", r"@", r"youtube\.com", r"youtu\.be"]
        if any(re.search(p, message.text.lower()) for p in patterns):
            await punish(client, chat_id, user_id, message)
            return

    if message.forward_date:
        await punish(client, chat_id, user_id, message)
        return

    user_data = await users_db.find_one({"_id": user_id})
    count = len(user_data.get("added_members", [])) if user_data else 0

    if count < 4:
        await punish(client, chat_id, user_id, message)
        return

async def punish(client, chat_id, user_id, message):

    await message.delete()

    user = await users_db.find_one({"_id": user_id})
    warnings = user.get("warnings", 0) + 1 if user else 1

    if warnings >= 2:
        mute_until = int(time.time()) + 1200

        await client.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(),
            until_date=mute_until
        )

        await mute_db.update_one(
            {"_id": user_id},
            {"$set": {"chat_id": chat_id, "until": mute_until}},
            upsert=True
        )

        await users_db.update_one(
            {"_id": user_id},
            {"$set": {"warnings": 0}},
            upsert=True
        )

        await client.send_message(chat_id, "🔇 User muted for 20 minutes!")

    else:
        await users_db.update_one(
            {"_id": user_id},
            {"$set": {"warnings": warnings}},
            upsert=True
        )
        await client.send_message(chat_id, f"⚠ Warning {warnings}/2")

async def check_mutes():
    while True:
        now = int(time.time())
        mutes = mute_db.find({"until": {"$lte": now}})

        async for mute in mutes:
            await app.restrict_chat_member(
                mute["chat_id"],
                mute["_id"],
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )

            await app.send_message(mute["chat_id"], "🔓 User automatically unmuted!")
            await mute_db.delete_one({"_id": mute["_id"]})

        await asyncio.sleep(30)

async def main():
    asyncio.create_task(check_mutes())
    print("Restart-Safe Smart Bot Started!")
    await app.start()
    from pyrogram import idle

from pyrogram.errors import FloodWait
from pyrogram import idle

async def main():
    asyncio.create_task(check_mutes())
    from pyrogram.errors import FloodWait
from pyrogram import idle
from aiohttp import web

# Dummy web server for Koyeb health check
async def health(request):
    return web.Response(text="Bot is running")

async def run_web():
    app_web = web.Application()
    app_web.router.add_get("/", health)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

async def main():
    print("Restart-Safe Smart Bot Started!")

    # FloodWait safe start
    while True:
        try:
            await app.start()
            break
        except FloodWait as e:
            print(f"FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)

    # Start mute checker AFTER bot started
    asyncio.create_task(check_mutes())

    # Start web server
    await run_web()

    await idle()

asyncio.run(main())
