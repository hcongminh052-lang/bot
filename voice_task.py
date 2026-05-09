import discord
import asyncio
from discord.ext import tasks

HUB_CHANNEL_ID = 1490301863692865597 
GLOBAL_BOT = None # Thêm biến này

@tasks.loop(seconds=30)
async def voice_keepalive_loop(): # Bỏ tham số bot ở đây
    bot = GLOBAL_BOT
    if not bot or not bot.is_ready():
        return

    hub_channel = bot.get_channel(HUB_CHANNEL_ID)
    if not hub_channel:
        return

    vc = discord.utils.get(bot.voice_clients, guild=hub_channel.guild)

    # TRƯỜNG HỢP 1: Bot hoàn toàn không ở trong voice
    if vc is None or not vc.is_connected():
        try:
            await hub_channel.connect()
        except:
            pass
    
    # TRƯỜNG HỢP 2: Ở một mình trong phòng JTC cũ
    elif len(vc.channel.members) == 1 and vc.channel.id != HUB_CHANNEL_ID:
        try:
            await vc.disconnect(force=True)
            await asyncio.sleep(2)
            await hub_channel.connect()
        except:
            pass
            
    # TRƯỜNG HỢP 3: Kẹt ở Hub
    elif vc.channel.id == HUB_CHANNEL_ID:
        await asyncio.sleep(5)
        if vc.channel.id == HUB_CHANNEL_ID:
             try:
                 await vc.disconnect(force=True)
                 await asyncio.sleep(2)
                 await hub_channel.connect()
             except:
                 pass

async def check_voice_status(bot, member, before, after):
    if member.id == bot.user.id and after.channel is None:
        await asyncio.sleep(5)
        # Gọi thẳng hàm handle logic bên trong loop thay vì gọi cả loop
        await voice_keepalive_loop()
