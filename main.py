import json
import os
import asyncio
import random
import signal
import traceback
import discord
from discord.ext import commands
from keep_alive import keep_alive
from feed_task import start_feed_task
from boss_task import start_boss_task

prefix = "!"
TOKEN = os.getenv("DISCORD_TOKEN")
bot = commands.Bot(command_prefix=prefix,
                   help_command=None,
                   case_insensitive=True,
                   self_bot=True)

# Khai báo trạng thái cày EXP (Mặc định là True để tự chạy khi Render restart)
farm_exp = True
exp_task = None

def listToString(s):
    str1 = ""
    for i in s:
        str1 += i
        str1 += " "
    return str1

# Vòng lặp cày EXP chạy ngầm
async def exp_farm_loop():
    await bot.wait_until_ready()
    channel_id = 1381302690335952988
    
    while True:
        if farm_exp:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    # Lấy danh sách emoji từ server chứa channel này
                    emoji_list = [em for em in channel.guild.emojis if not em.animated]
                    if emoji_list:
                        so_luong = random.randint(1, 1)
                        chosen = random.sample(emoji_list, so_luong)
                        text = "".join(str(em) for em in chosen)
                        await channel.send(text)
                        print(f"[{channel.guild.name}] Đã gửi EXP: {text}")
                except Exception as e:
                    print(f"Lỗi gửi EXP: {e}")
            else:
                print("Không tìm thấy kênh cày EXP!")
            
            # Delay ngẫu nhiên từ 65 đến 95 giây (tránh dính rate limit / slowmode)
            await asyncio.sleep(random.randint(65, 95))
        else:
            # Nếu tạm dừng cày EXP thì kiểm tra lại sau mỗi 5 giây
            await asyncio.sleep(5)

@bot.command()
async def cmd(ctx):
    msg = (
        "➤ !allchannels | !ac\n"
        "└ Hiển thị toàn bộ các kênh trong máy chủ.\n\n"

        "➤ !showhiddenvoice | !shdv\n"
        "└ Quét các kênh thoại bị ẩn và hiển thị người đang tham gia.\n\n"

        "➤ !showvoice | !sv\n"
        "└ Hiển thị các kênh thoại công khai cùng thành viên hiện diện.\n\n"

        "➤ !webhook | !wh\n"
        "└ Gửi tin nhắn bằng webhook mang tên/avatar của chính người dùng dùng lệnh.\n\n"

        "➤ !fake \n"
        "└ Giả danh một member khác trong server để gửi tin.\n\n"

        "➤ !clearwebhook | !cw\n"
        "└ Xoá toàn bộ webhook trong server.\n\n"
    )
    await ctx.send(msg)

@bot.event
async def on_ready():
    global exp_task
    print(f'✅ Bot {bot.user} đã lên sóng!')
    
    start_feed_task(bot)
    start_boss_task(bot)

    # Tự động kích hoạt task cày EXP chạy ngầm
    if exp_task is None or exp_task.done():
        exp_task = asyncio.create_task(exp_farm_loop())
        print("===== BẮT ĐẦU CÀY EXP TỰ ĐỘNG =====")

@bot.command()
async def kao(ctx):
    await ctx.message.delete()
    await ctx.send("┬─┬ノ( º _ ºノ)")

@bot.command(aliases=["ac"])
async def allchanels(ctx):
    vao_duoc = ""
    khong_vao_duoc = ""
    dem1 = 0
    dem2 = 0
    for ch in ctx.guild.channels:
        perms = ch.permissions_for(ctx.author)
        if perms.view_channel:
            dem1 += 1
            vao_duoc += f"[{dem1}] {ch.name.lower()}\n"
        else:
            dem2 += 1
            khong_vao_duoc += f"[{dem2}] {ch.name.lower()}\n"

    msg = "**=== KÊNH VÀO ĐƯỢC ===**\n"
    msg += vao_duoc if vao_duoc else "Không có\n"
    msg += "\n**=== KÊNH KHÔNG VÀO ĐƯỢC ===**\n"
    msg += khong_vao_duoc if khong_vao_duoc else "Không có"
    await ctx.send(msg)

@bot.command(aliases=["shdv"])
async def showhiddenvoice(ctx):
    ds_voice = []
    for i in ctx.guild.channels:
        if i.type == discord.ChannelType.voice:
            if i.permissions_for(ctx.guild.me).connect == False:
                voice_channel = discord.utils.get(ctx.guild.channels, id=i.id)
                members = voice_channel.members
                ten_members = '\n - - -'.join([x.name for x in members])
                ds_voice.append(members)
                if ten_members.strip() == "":
                    await ctx.send(f"**[Hidden]: ** {voice_channel.name}\n> *No members inside*")
                else:
                    await ctx.send(f"**[Hidden]: ** {voice_channel.name}\n> {ten_members}")
    await ctx.send(f"**Succesfully: ** {len(ds_voice)} **hidden channels**")

@bot.command(aliases=["sv"])
async def showvoice(ctx):
    ds_voice = []
    for i in ctx.guild.channels:
        if i.type == discord.ChannelType.voice:
            if i.permissions_for(ctx.guild.me).connect == True:
                voice_channel = discord.utils.get(ctx.guild.channels, id=i.id)
                members = voice_channel.members
                ten_members = '\n - - -'.join([x.name for x in members])
                ds_voice.append(members)
                if ten_members.strip() == "":
                    await ctx.send(f"**[Chanels]: ** {voice_channel.name}\n> *No members inside*")
                else:
                    await ctx.send(f"**[Chanels]: ** {voice_channel.name}\n> {ten_members}")
    await ctx.send(f"**Succesfully: ** {len(ds_voice)} **channels**")

@bot.command(aliases=["wh"])
async def webhook(ctx, *args):
    text = listToString(args)
    try:
        webhook = await ctx.channel.create_webhook(name=ctx.author.name)
        await webhook.send(text, username=ctx.author.name, avatar_url=ctx.author.avatar_url)
        await webhook.delete()
    except:
        await ctx.send("Lỗi khi chạy")

@bot.command()
async def fake(ctx, mem: discord.Member, *args):
    await ctx.message.delete()
    text = listToString(args)
    try:
        webhook = await ctx.channel.create_webhook(name=mem.name)
        if mem.nick != mem.name:
            await webhook.send(text, username=mem.nick, avatar_url=mem.avatar_url)
        else:
            await webhook.send(text, username=mem.name, avatar_url=mem.avatar_url)
        await webhook.delete()
    except:
        await ctx.send("Lỗi khi chạy")

@bot.command(aliases=["cw"])
async def clearwebhook(ctx):
    webhooks = await ctx.guild.webhooks()
    for webhook in webhooks:
        try:
            await webhook.delete()
        except:
            continue
    await ctx.send("Done!")

@bot.command(aliases=["clm"])
async def clearmessage(ctx, soluong):
    await ctx.message.delete()
    demtn = 0
    async for message in ctx.channel.history(limit=9999):
        await message.delete()
        await asyncio.sleep(1)
        demtn += 1
    await ctx.send(f":wastebasket: Đã xoá {demtn} tin nhắn!")

@bot.command(aliases=["dlm"])
async def deletmessage(ctx, soluong):
    await ctx.message.delete()
    if int(soluong) == 0:
        await ctx.send("Warning: Không thể xoá 0 tin nhắn")
    elif 1 <= int(soluong) <= 9999:
        gioihan = int(soluong)
        demtn = 0
        async for message in ctx.channel.history(limit=9999):
            if message.author == bot.user:
                await message.delete()
                await asyncio.sleep(1)
                demtn += 1
            if demtn == gioihan:
                break
        await ctx.send(f":wastebasket: Đã xoá {demtn} tin nhắn!")
    else:
        await ctx.send("Warning: Vượt quá giới hạn xoá tin nhắn")

@bot.command()
async def allem(ctx):
    await ctx.message.delete()
    print("Tong emoji trong server:", len(ctx.guild.emojis))
    for em in ctx.guild.emojis:
        print(em.name, em.id)

@bot.command(aliases=["se"])
async def startexp(ctx):
    await ctx.message.delete()
    global farm_exp
    farm_exp = True
    print("===== ĐÃ BẬT CÀY EXP =====")

@bot.command(aliases=["xe"])
async def stopexp(ctx):
    await ctx.message.delete()
    global farm_exp
    farm_exp = False
    print("===== ĐÃ TẮT CÀY EXP =====")

keep_alive()
bot.run(TOKEN)
