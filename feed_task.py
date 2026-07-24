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

IS_FEED_ENABLED = True

@tasks.loop(hours=4, minutes=5)
async def auto_feed_loop(bot_instance):
    if not IS_FEED_ENABLED:
        return

    vn_tz = timezone(timedelta(hours=7))
    current_vn_hour = datetime.now(vn_tz).hour
    
    if not (8 <= current_vn_hour < 22):
        print(f"⏰ [FEED SKIP] Hiện tại là {current_vn_hour}h VN (Ngoài khung giờ 8h-22h). Bỏ qua lượt gửi.", flush=True)
        return

    chosen_channel_id = random.choice(FEED_CHANNEL_IDS)
    try:
        channel = bot_instance.get_channel(chosen_channel_id) or await bot_instance.fetch_channel(chosen_channel_id)
    except Exception:
        channel = None

    if channel:
        try:
            if auto_feed_loop.current_loop > 0:
                extra_wait = random.randint(60, 300)
                await asyncio.sleep(extra_wait)
            
            if not IS_FEED_ENABLED:
                return

            current_vn_hour = datetime.now(vn_tz).hour
            if 8 <= current_vn_hour < 22:
                await channel.send(".feed")
            
        except Exception:
            pass

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
    
    @auto_feed_loop.before_loop
    async def before_auto_feed():
        await bot.wait_until_ready()
        
        vn_tz = timezone(timedelta(hours=7))
        now = datetime.now(vn_tz)
        if now.hour < 8:
            target_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
            wait_seconds = (target_8am - now).total_seconds()
            print(f"⏰ Chờ {wait_seconds:.0f}s cho đến đúng 8:00 sáng VN...", flush=True)
            await asyncio.sleep(wait_seconds)
        
    if not auto_feed_loop.is_running():
        auto_feed_loop.start(bot)
