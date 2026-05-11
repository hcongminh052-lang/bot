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
        print(f"❌ [Voice] Không tìm thấy ID kênh Hub: {HUB_CHANNEL_ID}")
        return

    # Lấy voice_client hiện tại của bot trong server chứa Hub
    vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)

    try:
        # TRƯỜNG HỢP 1: Bot hoàn toàn không ở trong voice hoặc bị mất kết nối
        if vc is None or not vc.is_connected():
            print("📡 [Voice] Phát hiện Bot đứng ngoài, đang kết nối vào Hub...")
            await hub_channel.connect(reconnect=True, timeout=20)
            print("✅ [Voice] Kết nối thành công!")
            return # Thoát để chờ vòng lặp sau

        # TRƯỜNG HỢP 2: Bot ở một mình trong phòng JTC cũ (không phải Hub)
        elif len(vc.channel.members) == 1 and vc.channel.id != HUB_CHANNEL_ID:
            print("🔄 [Voice] Phòng vắng người, quay về Hub...")
            await vc.disconnect(force=True)
            await asyncio.sleep(2)
            await hub_channel.connect(reconnect=True)
            return

        # TRƯỜNG HỢP 3: Bot đang kẹt ở Hub (JTC không move đi)
        elif vc.channel.id == HUB_CHANNEL_ID:
            # Kiểm tra xem có ai khác trong Hub không (thường là bot JTC hoặc người dùng)
            # Nếu sau 5s vẫn ở Hub, ta tiến hành reset
            await asyncio.sleep(5)
            # Cần lấy lại vc sau khi sleep để check trạng thái mới nhất
            current_vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)
            if current_vc and current_vc.channel.id == HUB_CHANNEL_ID:
                print("⚠️ [Voice] Bot bị kẹt ở Hub, đang reset kết nối...")
                await current_vc.disconnect(force=True)
                await asyncio.sleep(2)
                await hub_channel.connect(reconnect=True)

    except Exception as e:
        # Bỏ qua lỗi nếu bot đã vào được rồi (tránh spam log đỏ)
        if "Already connected" in str(e):
            pass
        else:
            print(f"❌ [Voice Error]: {e}")

async def check_voice_status(bot, member, before, after):
    """Hàm xử lý sự kiện khi bot bị kick hoặc văng voice"""
    if member.id == bot.user.id and after.channel is None:
        print("⚠️ [Voice] Bot vừa bị văng khỏi voice! Sẽ tự động kiểm tra lại...")
        # Đợi một chút cho Discord ổn định trạng thái rồi mới gọi loop
        await asyncio.sleep(5)
        # Kiểm tra nếu loop chưa chạy thì mới gọi, hoặc để loop 30s tự lo
        if not voice_keepalive_loop.is_running():
            await voice_keepalive_loop(bot)
