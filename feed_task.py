import discord
from discord.ext import tasks
import asyncio
import re
import time

# --- CẤU HÌNH ---
FEED_CHANNEL_ID = 1214564167520886804
NEXT_FEED_TIME = 0  # Biến lưu số phút cần chờ

@tasks.loop(minutes=1)
async def auto_feed_loop(bot):
    global NEXT_FEED_TIME
    
    # 1. Kiểm tra nếu vẫn còn thời gian chờ
    if NEXT_FEED_TIME > 0:
        NEXT_FEED_TIME -= 1
        print(f"⏳ Đang chờ... Còn {NEXT_FEED_TIME} phút nữa.")
        return

    # 2. Thực hiện lệnh feed khi hết thời gian chờ
    channel = bot.get_channel(FEED_CHANNEL_ID)
    if not channel:
        print("❌ Không tìm thấy kênh để feed!")
        return

    try:
        await channel.send(".feed")
        print("🌾 Đã gửi lệnh .feed")
        
        # Đợi 5 giây để bot Ram phản hồi
        await asyncio.sleep(5)
        
        # 3. Quét lịch sử để tìm tin nhắn phản hồi của bot Ram
        async for message in channel.history(limit=5):
            if message.author.bot and ("đợi đến" in message.content or "phút tới" in message.content):
                content = message.content
                wait_minutes = 0

                # A. Ưu tiên: Tìm mã Discord Timestamp <t:1234567890:R> (Cái bảng trỏ chuột vào)
                timestamp_match = re.search(r'<t:(\d+):', content)
                
                if timestamp_match:
                    target_unix = int(timestamp_match.group(1))
                    current_unix = int(time.time())
                    # Tính số phút chênh lệch + 1 phút dự phòng
                    wait_minutes = ((target_unix - current_unix) // 60) + 1
                    print(f"🎯 Nhận diện Timestamp: Đích lúc {time.ctime(target_unix)}")
                
                # B. Dự phòng: Lọc theo text thông thường (nếu không thấy mã)
                else:
                    number_match = re.search(r'(\d+)', content)
                    if number_match:
                        val = int(number_match.group(1))
                        if "giờ" in content:
                            wait_minutes = val * 60
                        else:
                            wait_minutes = val + 1 # +1 phút cho an toàn

                # Cập nhật thời gian chờ
                if wait_minutes > 0:
                    NEXT_FEED_TIME = wait_minutes
                    print(f"🕒 Bot Ram yêu cầu chờ: {NEXT_FEED_TIME} phút.")
                    return # Thoát vòng lặp history sau khi tìm thấy

        # Nếu gửi .feed thành công mà không thấy báo chờ (có thể đã feed thành công)
        # Mặc định 30p sau check lại cho an toàn
        NEXT_FEED_TIME = 30
                
    except Exception as e:
        print(f"❌ Lỗi hệ thống Feed: {e}")

def start_feed_task(bot):
    if not auto_feed_loop.is_running():
        auto_feed_loop.start(bot)
