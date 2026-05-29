import discord
import asyncio
from discord.ext import tasks

# ID Kênh Voice bạn muốn bot vào treo cố định
HUB_CHANNEL_ID = 1490301863692865597

@tasks.loop(seconds=30)  # Tăng lên 30 giây để an toàn, tránh spam API của Discord
async def voice_keepalive_loop(bot):
    if not bot.is_ready():
        return

    hub_channel = bot.get_channel(HUB_CHANNEL_ID)
    if not hub_channel:
        print(f"❌ [Voice] Không tìm thấy kênh thoại với ID {HUB_CHANNEL_ID}")
        return

    # Lấy trạng thái kết nối Voice hiện tại của bot trong Server đó
    vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)

    try:
        # TRƯỜNG HỢP 1: Bot chưa vào Voice hoặc bị mất kết nối (Văng phòng)
        if vc is None or not vc.is_connected():
            print("📡 [Voice] Đang tiến hành kết nối vào kênh chỉ định...", flush=True)
            
            # Kết nối vào phòng và ép buộc tắt Mic (self_mute), tắt Tai nghe (self_deafen)
            await hub_channel.connect(
                reconnect=True, 
                timeout=20, 
                self_mute=True, 
                self_deafen=True
            )
            print("🔒 [Voice] Đã treo máy ổn định + Khóa Mic & Tai nghe thành công!", flush=True)
            return

        # TRƯỜNG HỢP 2: Bot đang ở sai phòng (Do bị ai đó dùng quyền Admin kéo đi phòng khác)
        if vc.channel.id != HUB_CHANNEL_ID:
            print(f"⚠️ [Voice] Phát hiện bot bị kéo sang phòng khác ({vc.channel.name}). Đang quay về phòng cũ...", flush=True)
            await vc.disconnect(force=True)
            await asyncio.sleep(2)  # Đợi 2 giây cho việc ngắt kết nối hoàn tất sạch sẽ
            
            await hub_channel.connect(
                reconnect=True, 
                timeout=20, 
                self_mute=True, 
                self_deafen=True
            )
            print("🔒 [Voice] Đã quay về phòng chỉ định + Khóa Mic!", flush=True)

    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("🚨 [Voice] Dính giới hạn Rate Limit 429! Luồng voice tạm nghỉ 2 phút...", flush=True)
            await asyncio.sleep(120)
        else:
            print(f"❌ [Voice HTTP Error]: {e}", flush=True)
    except Exception as e:
        if "Already connected" in str(e):
            pass
        else:
            print(f"❌ [Voice Error]: {e}", flush=True)


async def check_voice_status(bot, member, before, after):
    """Xử lý sự kiện thời gian thực khi có tác động đến Voice của bot"""
    # Nếu sự kiện xảy ra tác động trực tiếp lên chính con Bot
    if member.id == bot.user.id:
        # Tình huống A: Bot bị Kick hẳn ra khỏi phòng Voice (Văng về trạng thái không ở phòng nào)
        if after.channel is None:
            print("⚠️ [Voice] Bot bị kick ra khỏi phòng! Đang kích hoạt kết nối lại lập tức...", flush=True)
            if voice_keepalive_loop.is_running():
                voice_keepalive_loop.restart(bot)
        
        # Tình huống B: Bot bị Admin Server tắt Mute hoặc tắt Deafen thủ công bằng quyền của Server
        elif after.channel.id == HUB_CHANNEL_ID:
            if not after.self_mute or not after.self_deafen:
                # Nếu phát hiện Mic hoặc Tai nghe bị mở ra, tiến hành kết nối đè để ép khóa lại
                vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)
                if vc and vc.is_connected():
                    try:
                        await hub_channel.connect(reconnect=True, timeout=10, self_mute=True, self_deafen=True)
                    except:
                        pass
