import discord
import asyncio
from discord.ext import tasks

# ID kênh "Hub - Join to create" của bạn
HUB_CHANNEL_ID = 1490301863692865597 

@tasks.loop(seconds=30)
async def voice_keepalive_loop(bot):
    """Vòng lặp chạy mỗi 30 giây để kiểm tra và giữ bot trong voice"""
    if not bot.is_ready():
        return

    hub_channel = bot.get_channel(HUB_CHANNEL_ID)
    if not hub_channel:
        print("❌ Không tìm thấy ID kênh Hub trong Server!")
        return

    # Kiểm tra xem bot đang kết nối voice ở server nào
    # Lấy voice_client hiện tại của bot trong server đó
    vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)

    # TRƯỜNG HỢP 1: Bot hoàn toàn không ở trong voice
    if vc is None or not vc.is_connected():
        print("📡 Phát hiện Bot đứng ngoài, đang kết nối vào Hub...")
        try:
            await hub_channel.connect()
        except Exception as e:
            print(f"❌ Lỗi khi cố gắng vào Hub: {e}")
    
    # TRƯỜNG HỢP 2: Bot đang ở một mình trong phòng (thường là phòng JTC cũ đã vắng người)
    elif len(vc.channel.members) == 1 and vc.channel.id != HUB_CHANNEL_ID:
        print("🔄 Bot đang ở một mình, quay về Hub để tạo phòng mới cho 'xôm'...")
        try:
            # Ngắt kết nối dứt điểm để dọn dẹp các 'Unclosed connection'
            await vc.disconnect(force=True)
            await asyncio.sleep(2)
            await hub_channel.connect()
        except Exception as e:
            print(f"❌ Lỗi khi làm mới phòng: {e}")
            
    # TRƯỜNG HỢP 3: Bot đang kẹt ở Hub mà không được move đi
    elif vc.channel.id == HUB_CHANNEL_ID:
        # Đợi thêm một chút xem bot JTC có move mình đi không
        await asyncio.sleep(5)
        if vc.channel.id == HUB_CHANNEL_ID:
             print("⚠️ Bot bị kẹt ở Hub, đang thử vào lại...")
             await vc.disconnect(force=True)
             await asyncio.sleep(2)
             await hub_channel.connect()

async def check_voice_status(bot, member, before, after):
    """Hàm xử lý sự kiện khi có thay đổi trạng thái voice"""
    # Nếu đối tượng thay đổi là Bot và kênh mới (after.channel) là None (vừa bị out)
    if member.id == bot.user.id and after.channel is None:
        print("⚠️ Bot vừa bị văng khỏi voice! Sẽ kiểm tra lại trong giây lát...")
        # Đợi 5 giây rồi gọi loop kiểm tra ngay
        await asyncio.sleep(5)
        await voice_keepalive_loop(bot)
