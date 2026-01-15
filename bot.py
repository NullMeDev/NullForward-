# Copyright (C) @SamZGamer
# Channel: https://t.me/DINOCHECKER

import os
from io import BytesIO
import logging
import asyncio
import random
from collections import defaultdict, deque
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, STICKER_IDS
from map_utils import load_map, add_mapping

# Basic config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress verbose logs
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session.session").setLevel(logging.WARNING)
logging.getLogger("pyrogram.connection.connection").setLevel(logging.WARNING)

app = Client("forwarder_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Queues
media_group_buffer = defaultdict(list)
media_group_queue = deque()
forward_queue = asyncio.Queue()

processing_album = False
processing_forward = False

FORWARD_MAP = load_map()
MAX_MESSAGE_LENGTH = 4096


# ----------------------- COMMANDS -----------------------

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    sticker = random.choice(STICKER_IDS)
    try:
        await message.reply_sticker(sticker)
    except Exception:
        await message.reply_video(sticker)

    await message.reply_text(
        "👋 **Hey there!**\n\n"
        "🛰️ Welcome to **Forwarder Bot** — your personal Telegram message relay system!\n\n"
        "📨 **This bot automatically forwards:**\n"
        "  ➜ 📥 __Text messages__\n"
        "  ➜ 🖼️ __Media (photo/video/docs)__\n"
        "  ➜ 🖼️📁 __Full__ **media albums** __as proper Telegram albums__\n\n"
        "📦 **Your chats are mapped from source ➝ target with full caption support.**\n"
        "⚡ **It's fast, reliable, and Docker-powered.**\n\n"
        "ℹ️ **Use it inside your deployment or fork and customize it for yourself.**\n\n"
        "🧑‍💻 Dev= @SamZGamer(Join Channel for More◇ https://t.me/DINOCHECKER)\n\n"
        "__Ready when you are... just send a message in your source chat!__",
        disable_web_page_preview=True,
        quote=True
    )


@app.on_message(filters.command("logs") & filters.user(OWNER_ID))
async def send_logs(client, message):
    try:
        await message.reply_document("logs.txt", caption="🗂️ Logs file")
    except Exception as e:
        await message.reply_text(f"❌ Couldn't send logs: `{e}`")


@app.on_message(filters.command("setmap") & filters.user(OWNER_ID))
async def setmap_cmd(client, message: Message):
    try:
        response = await message.ask(
            "**🔄 Set a new forward mapping**\n\n"
            "Please send the `source_chat` and `target_chat`, separated by a space.\n\n"
            "You can use:\n"
            "• Chat IDs: `-1001234567890 -1009876543210`\n"
            "• Usernames: `@source_channel @target_channel`\n"
            "• Mixed: `-1001234567890 @target_channel`\n\n"
            "Example:\n`-1001234567890 @target_channel`",
            timeout=120
        )

        parts = response.text.strip().split()
        if len(parts) != 2:
            return await response.reply("⚠️ Please provide exactly 2 chat identifiers separated by space.")

        src_input, tgt_input = parts[0], parts[1]
        
        # Helper function to parse chat input
        async def parse_chat_input(chat_input):
            # If it looks like an integer (including negative), treat as ID
            if chat_input.lstrip('-').replace('-', '').isdigit():
                chat_id = int(chat_input)
                chat_obj = await client.get_chat(chat_id)
                return chat_obj
            else:
                # Remove @ if present and get by username
                username = chat_input.lstrip('@')
                chat_obj = await client.get_chat(username)
                return chat_obj

        # Validate both chats
        try:
            src_chat = await parse_chat_input(src_input)
            tgt_chat = await parse_chat_input(tgt_input)
        except Exception as e:
            return await response.reply(f"❌ Invalid chat identifier(s): {e}")

        src_id = src_chat.id
        tgt_id = tgt_chat.id

        add_mapping(src_id, tgt_id)
        FORWARD_MAP.clear()
        FORWARD_MAP.update(load_map())

        await response.reply(
            f"✅ Mapping saved:\n\n"
            f"**Source:** {src_chat.title or src_chat.username} (`{src_id}`)\n"
            f"**Target:** {tgt_chat.title or tgt_chat.username} (`{tgt_id}`)"
        )

    except asyncio.TimeoutError:
        await message.reply("⏰ Timeout. Please try `/setmap` again.")


@app.on_message(filters.command("showmap") & filters.user(OWNER_ID))
async def show_map_cmd(client, message: Message):
    mappings = load_map()
    if not mappings:
        return await message.reply("⚠️ No source ➝ target mappings found yet.")

    msg = "**📌 Current Source ➝ Target Mappings:**\n\n"
    for src_id_str, tgt_id in mappings.items():
        try:
            src_id = int(src_id_str)
            src_chat = await client.get_chat(src_id)
            tgt_chat = await client.get_chat(tgt_id)
            
            src_name = src_chat.title or src_chat.username or f"Chat {src_id}"
            tgt_name = tgt_chat.title or tgt_chat.username or f"Chat {tgt_id}"
            
            # Show username if available
            src_username = f" (@{src_chat.username})" if src_chat.username else ""
            tgt_username = f" (@{tgt_chat.username})" if tgt_chat.username else ""
            
            msg += f"• **{src_name}**{src_username} (`{src_id}`)\n  ➝ **{tgt_name}**{tgt_username} (`{tgt_id}`)\n\n"
        except Exception as e:
            msg += f"• `{src_id_str}` ➝ `{tgt_id}` (⚠️ Error fetching chat info: {e})\n\n"

    await message.reply(msg, disable_web_page_preview=True)


@app.on_message(filters.command("bash") & filters.user(OWNER_ID))
async def execution(client, message):
    status_message = await message.reply_text("`Processing ...`")

    try:
        cmd = message.text.split(" ", maxsplit=1)[1]
    except IndexError:
        return await status_message.edit("No command provided!")

    reply_to_ = message.reply_to_message or message

    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    stderr_output = stderr.decode().strip() or "😂"
    stdout_output = stdout.decode().strip() or "😐"

    output = (
        f"<b>QUERY:</b>\n<u>Command:</u>\n<code>{cmd}</code>\n"
        f"<u>PID</u>: <code>{process.pid}</code>\n\n"
        f"<b>stderr</b>: \n<code>{stderr_output}</code>\n\n"
        f"<b>stdout</b>: \n<code>{stdout_output}</code>"
    )

    if len(output) > MAX_MESSAGE_LENGTH:
        with BytesIO(output.encode()) as out_file:
            out_file.name = "exec.txt"
            await reply_to_.reply_document(
                document=out_file,
                caption=cmd[: MAX_MESSAGE_LENGTH // 4 - 1],
                disable_notification=True,
                quote=True,
            )
    else:
        await reply_to_.reply_text(output, quote=True)

    await status_message.delete()


# ----------------------- FORWARDING -----------------------

@app.on_message()
async def forward_handler(client, message: Message):
    src_chat_id = str(message.chat.id)
    if src_chat_id not in FORWARD_MAP:
        return

    if message.text and message.text.startswith(("/", ".")):
        return

    dst_chat_id = FORWARD_MAP[src_chat_id]

    if message.media_group_id:
        group_key = f"{src_chat_id}:{message.media_group_id}"
        media_group_buffer[group_key].append(message)

        if group_key not in media_group_queue:
            media_group_queue.append((src_chat_id, dst_chat_id, group_key))
            await process_album_queue(client)
    else:
        await forward_queue.put((message, dst_chat_id))
        await process_forward_queue(client)


async def process_forward_queue(client):
    global processing_forward
    if processing_forward:
        return

    processing_forward = True
    while not forward_queue.empty():
        message, dst_chat_id = await forward_queue.get()
        try:
            await message.copy(chat_id=dst_chat_id)
            await asyncio.sleep(0.5)  # keep order stable
        except FloodWait as e:
            logger.warning(f"🌊 FloodWait: sleeping for {e.value}s")
            await asyncio.sleep(e.value)
            await message.copy(chat_id=dst_chat_id)
        except Exception as e:
            logger.error(f"❌ Error forwarding single message: {e}")
    processing_forward = False


async def process_album_queue(client):
    global processing_album
    if processing_album:
        return

    processing_album = True
    while media_group_queue:
        src_chat_id, dst_chat_id, group_key = media_group_queue.popleft()
        await asyncio.sleep(2)  # wait for album parts

        messages = media_group_buffer[group_key]
        if not messages:
            continue

        messages = sorted(messages, key=lambda m: m.id)

        try:
            await client.copy_media_group(
                chat_id=dst_chat_id,
                from_chat_id=src_chat_id,
                message_id=messages[0].id
            )
            logger.info(f"📸 Forwarded album with {len(messages)} items")
        except FloodWait as e:
            logger.warning(f"⚠️ FloodWait while forwarding album: Sleeping {e.value}s")
            await asyncio.sleep(e.value)
            try:
                await client.copy_media_group(
                    chat_id=dst_chat_id,
                    from_chat_id=src_chat_id,
                    message_id=messages[0].id
                )
                logger.info(f"✅ Retried and forwarded album after FloodWait")
            except Exception as inner_e:
                logger.error(f"❌ Retry failed for album {group_key}: {inner_e}")
        except Exception as e:
            logger.error(f"❌ Error forwarding album {group_key}: {e}")
        finally:
            media_group_buffer.pop(group_key, None)

    processing_album = False


# ----------------------- RUN -----------------------

if __name__ == "__main__":
    try:
        logger.info("🎉 Bot Started!")
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as err:
        logger.error(err)
    finally:
        logger.info("Bot Stopped")