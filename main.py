@app.on_message(filters.group & filters.text)
async def filter_system(client, message):

    # Ignore channel messages
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

    # Delete links
    patterns = [r"https?://", r"t\.me/", r"@", r"youtube\.com", r"youtu\.be"]
    if any(re.search(p, message.text.lower()) for p in patterns):
        await punish(client, chat_id, user_id, message)
        return

    # Check added count
    cursor.execute("SELECT added FROM users WHERE user_id=?", (user_id,))
    added = cursor.fetchone()[0]

    if added < 4:
        await punish(client, chat_id, user_id, message)
