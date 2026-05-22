import discord
from discord.ext import tasks
import asyncio
import random
from datetime import datetime

FEED_CHANNEL_ID = 1214564167520886804 

@tasks.loop(hours=2)
async def auto_feed_loop(bot):
    channel = bot.get_channel(FEED_CHANNEL_ID)
    if channel:
        try:
            if auto_feed_loop.current_loop > 0:
                extra_wait = random.randint(60, 300) # Chờ ngẫu nhiên 1-5 phút
                print(f"--- Đang chờ {extra_wait}s trước khi farm đợt tiếp theo ---")
                await asyncio.sleep(extra_wait)
            
            await channel.send(".feed")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌾 Đã gửi .feed vào kênh {FEED_CHANNEL_ID}")
        except Exception as e:
            print(f"❌ Lỗi khi farm: {e}")
    else:
        print(f"❌ Không tìm thấy kênh {FEED_CHANNEL_ID}. Kiểm tra lại quyền hạn của tài khoản.")

def start_feed_task(bot):
    if not auto_feed_loop.is_running():
        auto_feed_loop.start(bot)
