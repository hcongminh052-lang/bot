import asyncio
import random
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import tasks

FEED_CHANNEL_IDS = [
    1381241446409175040,
    1214564134356779118,
    1292304060342603840
]

import asyncio
import random
from datetime import datetime, timezone, timedelta
import discord

FEED_CHANNEL_IDS = [
    1292304060342603840
]

IS_FEED_ENABLED = True

def get_next_feed_delay():
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)
    
    today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
    
    schedule = [
        today_8am,
        today_8am + timedelta(hours=4, minutes=30),
        today_8am + timedelta(hours=9),
        today_8am + timedelta(hours=13, minutes=30)
    ]
    
    for slot in schedule:
        if now < slot:
            return (slot - now).total_seconds()
            
    tomorrow_8am = today_8am + timedelta(days=1)
    return (tomorrow_8am - now).total_seconds()

async def send_feed_message(bot_instance):
    if not IS_FEED_ENABLED:
        return

    chosen_channel_id = random.choice(FEED_CHANNEL_IDS)
    try:
        channel = bot_instance.get_channel(chosen_channel_id) or await bot_instance.fetch_channel(chosen_channel_id)
    except Exception:
        channel = None

    if channel:
        try:
            extra_wait = random.randint(3, 10)
            await asyncio.sleep(extra_wait)
            
            if IS_FEED_ENABLED:
                await channel.send(".feed")
                print("🌾 [FEED] Đã gửi thành công .feed", flush=True)
        except Exception as e:
            print("❌ [FEED ERROR]:", e, flush=True)

async def feed_scheduler_loop(bot_instance):
    await bot_instance.wait_until_ready()
    
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)
    
    if 8 <= now.hour < 22:
        print("🚀 Khởi động bot trong khung giờ hoạt động (8h-22h), thực hiện gửi .feed ngay...", flush=True)
        await send_feed_message(bot_instance)
    
    while True:
        delay = get_next_feed_delay()
        print(f"⏰ [FEED SCHEDULER] Chờ {delay:.0f}s cho lượt gửi tiếp theo...", flush=True)
        await asyncio.sleep(delay)
        await send_feed_message(bot_instance)

async def setup_message_listener(bot_instance):
    @bot_instance.listen('on_message')
    async def handle_feed_commands(message):
        global IS_FEED_ENABLED

        if message.content == "!feed off":
            IS_FEED_ENABLED = False
            await message.reply("🛑 Đã tạm dừng vòng lặp tự động gửi `.feed`.")
            return

        if message.content == "!feed on":
            IS_FEED_ENABLED = True
            await message.reply("🌾 Đã bắt đầu lại vòng lặp tự động gửi `.feed`.")
            return

def start_feed_task(bot):
    asyncio.create_task(setup_message_listener(bot))
    asyncio.create_task(feed_scheduler_loop(bot))
