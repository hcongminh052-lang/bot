import discord
import asyncio
from discord.ext import tasks
import traceback

# ID kênh "Hub - Join to create"
HUB_CHANNEL_ID = 1490301863692865597 
GLOBAL_BOT = None 

@tasks.loop(seconds=30)
async def voice_keepalive_loop():
    global GLOBAL_BOT
    bot = GLOBAL_BOT
    
    if bot is None or not bot.is_ready():
        return

    try:
        hub_channel = bot.get_channel(HUB_CHANNEL_ID)
        if not hub_channel:
            print(f"❌ [Voice] Không tìm thấy kênh ID: {HUB_CHANNEL_ID}")
            return

        # Tìm voice_client trong server chứa kênh Hub
        vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)

        # TRƯỜNG HỢP 1: Bot hoàn toàn không ở trong voice
        if vc is None or not vc.is_connected():
            print("📡 [Voice] Bot đang ngoài voice, tiến hành kết nối vào Hub...")
            await hub_channel.connect(reconnect=True, timeout=20)
            print("✅ [Voice] Đã kết nối lại!")
        
        # TRƯỜNG HỢP 2: Bot ở một mình trong phòng JTC cũ (không phải Hub)
        elif len(vc.channel.members) == 1 and vc.channel.id != HUB_CHANNEL_ID:
            print("🔄 [Voice] Phòng vắng người, quay về Hub...")
            await vc.disconnect(force=True)
            await asyncio.sleep(2)
            await hub_channel.connect(reconnect=True)
            
        # TRƯỜNG HỢP 3: Bot kẹt ở Hub quá lâu (JTC không move đi)
        elif vc.channel.id == HUB_CHANNEL_ID:
            # Nếu ở Hub quá 10 giây mà không bị move đi, thử reset kết nối
            await asyncio.sleep(10)
            current_vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)
            if current_vc and current_vc.channel.id == HUB_CHANNEL_ID:
                print("⚠️ [Voice] Kẹt tại Hub, đang reset...")
                await current_vc.disconnect(force=True)
                await asyncio.sleep(2)
                await hub_channel.connect(reconnect=True)

    except Exception as e:
        print(f"❌ [Voice Error]: {e}")
        # traceback.print_exc() # Mở dòng này nếu muốn xem chi tiết lỗi kỹ thuật

async def check_voice_status(bot, member, before, after):
    """Hàm bổ trợ khi bot bị kick hoặc văng voice"""
    if member.id == bot.user.id and after.channel is None:
        print("⚠️ [Voice] Bot bị văng khỏi kênh. Vòng lặp sẽ tự động đưa bot trở lại sau tối đa 30s.")
        # Không cần gọi thủ công nữa, hãy để loop 30s tự làm việc của nó cho ổn định
