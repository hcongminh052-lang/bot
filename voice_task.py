import discord
import asyncio
from discord.ext import tasks

# ID Kênh Voice bạn muốn bot vào treo cố định
HUB_CHANNEL_ID = 1490301863692865597

@tasks.loop(seconds=30)  # Giãn cách 30 giây để an toàn cho API
async def voice_keepalive_loop(bot):
    if not bot.is_ready():
        return

    hub_channel = bot.get_channel(HUB_CHANNEL_ID)
    if not hub_channel:
        print(f"❌ [Voice] Không tìm thấy kênh thoại với ID {HUB_CHANNEL_ID}")
        return

    # Lấy trạng thái kết nối Voice hiện tại của bot trong Server
    vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)

    try:
        # TRƯỜNG HỢP 1: Bot chưa vào Voice hoặc bị văng phòng
        if vc is None or not vc.is_connected():
            print("📡 [Voice] Đang tiến hành kết nối vào kênh chỉ định...", flush=True)
            
            # 1. Kết nối vào phòng bằng lệnh cơ bản để tránh lỗi biến argument
            vc = await hub_channel.connect(reconnect=True, timeout=20)
            await asyncio.sleep(1.5) # Chờ 1.5 giây cho luồng kết nối thiết lập xong ổn định
            
            # 2. Ép tài khoản tự động Tắt mic (self_mute) và Tắt tai nghe (self_deafen) từ phía Client
            await hub_channel.guild.change_voice_state(channel=hub_channel, self_mute=True, self_deafen=True)
            print("🔒 [Voice] Đã treo máy ổn định + Khóa Mic & Tai nghe thành công!", flush=True)
            return

        # TRƯỜNG HỢP 2: Bot đang ở sai phòng (Do bị Admin khác kéo đi)
        if vc.channel.id != HUB_CHANNEL_ID:
            print(f"⚠️ [Voice] Phát hiện bot bị kéo sang phòng khác ({vc.channel.name}). Đang quay về phòng cũ...", flush=True)
            await vc.disconnect(force=True)
            await asyncio.sleep(2) 
            
            vc = await hub_channel.connect(reconnect=True, timeout=20)
            await asyncio.sleep(1.5)
            await hub_channel.guild.change_voice_state(channel=hub_channel, self_mute=True, self_deafen=True)
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
    if member.id == bot.user.id:
        hub_channel = bot.get_channel(HUB_CHANNEL_ID)
        if not hub_channel: return

        # Tình huống A: Bot bị Kick hẳn ra khỏi phòng Voice
        if after.channel is None:
            print("⚠️ [Voice] Bot bị kick ra khỏi phòng! Đang kích hoạt kết nối lại...", flush=True)
            if voice_keepalive_loop.is_running():
                voice_keepalive_loop.restart(bot)
        
        # Tình huống B: Bot bị mở Mic hoặc mở Tai nghe ra thủ công
        elif after.channel.id == HUB_CHANNEL_ID:
            if not after.self_mute or not after.self_deafen:
                print("🔒 [Voice Check] Phát hiện trạng thái Mic bị thay đổi, tiến hành khóa lại...", flush=True)
                try:
                    await hub_channel.guild.change_voice_state(channel=hub_channel, self_mute=True, self_deafen=True)
                except:
                    pass
