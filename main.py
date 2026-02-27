import os
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client(
    "force_add_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Track added members count (temporary memory)
user_added_count = {}

@app.on_message(filters.group & filters.new_chat_members)
async def count_added_members(client, message: Message):
    inviter = message.from_user.id
    added_members = len(message.new_chat_members)

    if inviter in user_added_count:
        user_added_count[inviter] += added_members
    else:
        user_added_count[inviter] = added_members


@app.on_message(filters.group & filters.text)
async def check_member_added(client, message: Message):
    user_id = message.from_user.id

    # Skip admins
    member = await app.get_chat_member(message.chat.id, user_id)
    if member.status in ["administrator", "creator"]:
        return

    added = user_added_count.get(user_id, 0)

    if added < 4:
        try:
            await message.delete()
            await message.reply_text(
                "⚠️ Pehle 4 members add karo phir message karo!"
            )
        except:
            pass

app.run()
