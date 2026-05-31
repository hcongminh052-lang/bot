import discord
from discord.ext import tasks
import asyncio
import random
from datetime import datetime

FEED_CHANNEL_IDS = [
    1340657013683650651,
    1381241446409175040,
    1214564134356779118,
    1214564167520886804
]

@tasks.loop(hours=3)
async def auto_feed_loop(bot):
    chosen_channel_id = random.choice(FEED_CHANNEL_IDS)
    channel = bot.get_channel(chosen_channel_id)
    
    if channel:
        try:
            if auto_feed_loop.current_loop > 0:
                extra_wait = random.randint(60, 300) # Chờ ngẫu nhiên 1-5 phút
                print(f"--- Đang chờ {extra_wait}s trước khi farm đợt tiếp theo ---", flush=True)
                await asyncio.sleep(extra_wait)
            
            # 🌾 BƯỚC 2: Gửi lệnh vào kênh được chọn ngẫu nhiên
            await channel.send(".feed")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌾 Đã gửi .feed vào kênh ngẫu nhiên: {chosen_channel_id}", flush=True)
            
        except discord.errors.HTTPException as e:
            print(f"🚫 Lỗi Discord (Có thể bị giới hạn chat): {e}", flush=True)
        except Exception as e:
            print(f"❌ Lỗi khi farm: {e}", flush=True)
    else:
        print(f"❌ Không tìm thấy hoặc thiếu quyền xem kênh: {chosen_channel_id}. Sẽ thử lại ở chu kỳ sau.", flush=True)

def start_feed_task(bot):
    if not auto_feed_loop.is_running():
        auto_feed_loop.start(bot)
