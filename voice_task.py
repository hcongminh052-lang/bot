import discord
import asyncio
from discord.ext import tasks

HUB_CHANNEL_ID = 1490301863692865597

@tasks.loop(seconds=20)
async def voice_keepalive_loop(bot):
    if not bot.is_ready():
        return

    hub_channel = bot.get_channel(HUB_CHANNEL_ID)
    if not hub_channel:
        return

    # Lấy voice_client hiện tại
    vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)

    try:
        # TRƯỜNG HỢP 1: Đang ở ngoài
        if vc is None or not vc.is_connected():
            print("📡 [Voice] Đang kết nối vào Hub...")
            # Thêm timeout để không bị treo bot nếu mạng lag
            await hub_channel.connect(reconnect=True, timeout=20)
            return

        # TRƯỜNG HỢP 2: Ở một mình trong phòng JTC (đã vắng người)
        if len(vc.channel.members) == 1 and vc.channel.id != HUB_CHANNEL_ID:
            print("🔄 [Voice] Phòng vắng, quay về Hub...")
            await vc.disconnect(force=True)
            # Không nối ngay, đợi loop sau cho chắc chắn đã thoát hẳn

        # TRƯỜNG HỢP 3: Kẹt ở Hub
        elif vc.channel.id == HUB_CHANNEL_ID:
            # Nếu có người ở Hub mà bot không được move đi sau 5s
            await asyncio.sleep(5)
            # Kiểm tra lại xem còn ở Hub không
            vc_check = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)
            if vc_check and vc_check.channel.id == HUB_CHANNEL_ID:
                if len(vc_check.channel.members) > 1:
                    print("⚠️ [Voice] Kẹt ở Hub, đang reset...")
                    await vc_check.disconnect(force=True)
                    await asyncio.sleep(2)
                    await hub_channel.connect(reconnect=True)

    except Exception as e:
        if "Already connected" in str(e):
            pass # Đã vào rồi thì thôi, không báo lỗi đỏ
        else:
            print(f"❌ [Voice Error]: {e}")

async def check_voice_status(bot, member, before, after):
    """Hàm xử lý sự kiện khi bot bị văng voice"""
    if member.id == bot.user.id and after.channel is None:
        print("⚠️ [Voice] Bot bị văng! Task sẽ tự đưa bot vào lại sau tối đa 20s.")
        # Lưu ý: Không cần gọi lại Task ở đây nếu Task đang running. 
        # Nếu muốn ép buộc chạy ngay, hãy dùng:
        if voice_keepalive_loop.is_running():
            voice_keepalive_loop.restart(bot)
