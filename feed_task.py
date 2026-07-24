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
LAST_FEED_TIME = None
INTERVAL_SECONDS = 5 * 3600

async def send_feed_message(bot_instance):
    global LAST_FEED_TIME
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
                vn_tz = timezone(timedelta(hours=7))
                LAST_FEED_TIME = datetime.now(vn_tz)
                print(f"🌾 [FEED SUCCESS] Đã gửi .feed lúc {LAST_FEED_TIME.strftime('%H:%M:%S')}", flush=True)
        except Exception as e:
            print("❌ [FEED ERROR]:", e, flush=True)

@tasks.loop(minutes=1)
async def feed_checker_loop(bot_instance):
    global LAST_FEED_TIME
    if not IS_FEED_ENABLED:
        return

    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)

    if not (8 <= now.hour < 22):
        return

    if LAST_FEED_TIME is None:
        print("🚀 [FEED START] Khởi động bot trong khung giờ 8h-22h, thực hiện gửi lượt đầu tiên...", flush=True)
        await send_feed_message(bot_instance)
        return

    if LAST_FEED_TIME.day != now.day and now.hour >= 8:
        print("🌅 [FEED NEW DAY] Đã sang ngày mới (sau 8h sáng), kích hoạt lượt feed đầu tiên...", flush=True)
        await send_feed_message(bot_instance)
        return

    elapsed_seconds = (now - LAST_FEED_TIME).total_seconds()
    if elapsed_seconds >= INTERVAL_SECONDS:
        print(f"⏰ [FEED TRIGGER] Đã đủ chu kỳ 4 tiếng 5 phút ({elapsed_seconds/60:.1f} phút). Đang gửi tiếp...", flush=True)
        await send_feed_message(bot_instance)

async def setup_message_listener(bot_instance):
    @bot_instance.listen('on_message')
    async def handle_feed_commands(message):
        global IS_FEED_ENABLED, LAST_FEED_TIME

        if message.content == "!feed off":
            IS_FEED_ENABLED = False
            await message.reply("🛑 Đã tạm dừng vòng lặp tự động gửi `.feed`.")
            return

        if message.content == "!feed on":
            IS_FEED_ENABLED = True
            await message.reply("🌾 Đã bắt đầu lại vòng lặp tự động gửi `.feed`.")
            return

        if message.author.id == bot_instance.user.id and message.content == ".feed":
            vn_tz = timezone(timedelta(hours=7))
            LAST_FEED_TIME = datetime.now(vn_tz)

def start_feed_task(bot):
    asyncio.create_task(setup_message_listener(bot))
    
    @feed_checker_loop.before_loop
    async def before_feed_checker():
        await bot.wait_until_ready()
        
    if not feed_checker_loop.is_running():
        feed_checker_loop.start(bot)
