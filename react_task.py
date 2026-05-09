import discord
import asyncio
import random
import json
import os

# Cấu hình lưu trữ
checkpoint_file = "checkpoints.json"
current_delay = 0.35
min_delay = 0.2
max_delay = 1.5

def load_checkpoints():
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_checkpoints(data):
    with open(checkpoint_file, "w") as f:
        json.dump(data, f)

channel_checkpoints = load_checkpoints()

async def safe_add_reaction(msg, em, channel_id):
    global current_delay
    for lan_thu in range(5):
        try:
            await msg.add_reaction(em)
            print(f"[{channel_id}] + {em} -> {msg.id}")
            current_delay = max(current_delay * 1.01, 1.1)
            await asyncio.sleep(current_delay + random.uniform(0.2, 0.6))
            return True
        except discord.HTTPException as e:
            if e.status == 429:
                wait_time = getattr(e, "retry_after", 2)
                current_delay = min(current_delay * 1.35, max_delay)
                print(f"[{channel_id}] ⏳ RATE LIMIT {wait_time}s | delay={round(current_delay,2)}")
                await asyncio.sleep(wait_time + random.uniform(1, 2))
                continue
            elif e.status in [403, 404]:
                print(f"[{channel_id}] Error {e.status} skip msg {msg.id}")
                return False
            if "cloudflare" in str(e).lower():
                await asyncio.sleep(90)
                return False
            return False
        except Exception as e:
            print(f"[{channel_id}] Lỗi khác {e}")
            return False
    return False

async def process_channel(bot, channel_id, emoji_ids):
    global channel_checkpoints
    channel = bot.get_channel(channel_id)
    if not channel: return

    data = channel_checkpoints.get(str(channel_id), {})
    last_message_id = data.get("last_id") if isinstance(data, dict) else data
    emoji_index = data.get("emoji_index", 0) if isinstance(data, dict) else 0

    BATCH_SIZE = 2
    emoji_batch_raw = emoji_ids[emoji_index:emoji_index + BATCH_SIZE]
    emoji_batch = []
    for eid in emoji_batch_raw:
        if isinstance(eid, str): emoji_batch.append(eid)
        else:
            em = bot.get_emoji(eid)
            if em: emoji_batch.append(em)

    history = channel.history(limit=1000, before=discord.Object(id=int(last_message_id))) if last_message_id else channel.history(limit=1000)

    tong_quet = 0
    async for msg in history:
        new_checkpoint = msg.id
        tong_quet += 1
        my_reactions = [str(r.emoji) for r in msg.reactions if r.me]
        for em in emoji_batch:
            if str(em) not in my_reactions:
                await safe_add_reaction(msg, em, channel_id)

        if tong_quet % 20 == 0:
            channel_checkpoints[str(channel_id)] = {"last_id": str(new_checkpoint), "emoji_index": emoji_index}
            save_checkpoints(channel_checkpoints)

    next_index = (emoji_index + BATCH_SIZE) if (emoji_index + BATCH_SIZE) < len(emoji_ids) else 0
    channel_checkpoints[str(channel_id)] = {"last_id": str(new_checkpoint), "emoji_index": next_index}
    save_checkpoints(channel_checkpoints)
