import json
import os
import asyncio
import random
import signal
import traceback
import discord
import voice_task
from discord.ext import commands
from keep_alive import keep_alive
from voice_task import voice_keepalive_loop, check_voice_status
from feed_task import start_feed_task
from react_task import process_channel, save_checkpoints, channel_checkpoints

prefix = "!"
intents = discord.Intents.all()
TOKEN = os.getenv("DISCORD_TOKEN")
bot = commands.Bot(command_prefix=prefix,
                   help_command=None,
                   case_insensitive=True,
                   intents=intents,
                   self_bot = True)

def shutdown_handler():
    print("Saving checkpoint before exit...")
    save_checkpoints(channel_checkpoints)

signal.signal(signal.SIGINT, lambda s, f: shutdown_handler())

def listToString(s):
    str1 = ""
    for i in s:
        str1 += i
        str1 += " "
    return str1

@bot.command()
async def cmd(ctx):
    msg = (
        "➤ !allchanels | !ac\n"
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
    print(f'✅ Bot {bot.user} đã lên sóng!')

    if not voice_task.voice_keepalive_loop.is_running():
        voice_task.voice_keepalive_loop.start()
        print("🚀 [System] Đã kích hoạt vòng lặp Voice Keepalive")
        
    start_feed_task(bot)

@bot.event
async def on_voice_state_update(member, before, after):
    await check_voice_status(bot, member, before, after)

@bot.command()
async def kao(ctx):
    await ctx.message.delete()
    await ctx.send("┬─┬ノ( º _ ºノ)")

@bot.command(aliases = ["ac"])
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

@bot.command(aliases = ["shdv"])
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

@bot.command(aliases = ["sv"])
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

@bot.command(aliases = ["wh"])
async def webhook(ctx, *args):
    text = listToString(args)
    try:
        webhook = await ctx.channel.create_webhook(name = ctx.author.name)
        await webhook.send(text, username=ctx.author.name, avatar_url=ctx.author.avatar_url)
        await webhook.delete()
    except:
        await ctx.send("Lỗi khi chạy")

@bot.command()
async def fake(ctx, mem:discord.Member, *args):
    await ctx.message.delete()
    text = listToString(args)
    try:
        webhook = await ctx.channel.create_webhook(name = mem.name)
        if mem.nick != mem.name:
            await webhook.send(text, username=mem.nick, avatar_url=mem.avatar_url)
        else:
            await webhook.send(text, username=mem.name, avatar_url=mem.avatar_url)
        await webhook.delete()
    except:
        await ctx.send("Lỗi khi chạy")

@bot.command(aliases = ["cw"])
async def clearwebhook(ctx):
    webhooks = await ctx.guild.webhooks()
    for webhook in webhooks:
        try:
            await webhook.delete()
        except:
            continue
    await ctx.send("Done!")

@bot.command(aliases = ["clm"])
async def clearmessage(ctx, soluong):
    await ctx.message.delete()
    demtn = 0
    async for message in ctx.channel.history(limit=9999):
        await message.delete()
        await asyncio.sleep(1)
        demtn += 1
    await ctx.send(f":wastebasket: Đã xoá {demtn} tin nhắn!")

@bot.command(aliases = ["dlm"])
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

last_message_id = None
@bot.command(aliases = ["or"])
async def oldreact(ctx):
    try:
        await ctx.message.delete()
    except:
        pass
    react_config = {
        1229716511401316404: [
            1194533745286451271,
            1194533743109611550,
            1194196518228463646,
            1194196538067529802,
            1194200700696137748,
            1286272027141083137
        ],
        1229716774195433472: [
            1194533745286451271,
            1194533743109611550,
            1194196518228463646,
            1194196538067529802,
            1194200700696137748,
            1286272027141083137,
            "❤️",
            1194196216985169951,
            1194196752803315772,
            1195014108085489866,
            1211715677497331732,
            1279164617117143113
        ],
        1380893805162528878: [
            1194533745286451271,
            "❤️",
            1194196216985169951,
            1194196752803315772,
            1195014108085489866,
            1211715677497331732,
            1279164617117143113
        ],
        1302993772006609007: [
            1194533745286451271,
            1194196216985169951,
            1211715677497331732,
            1195014108085489866,
            1196006750403440710,
            1196008739665358858,
            1194281783659864114
        ],
        1281154949077798912: [
            1194533745286451271,
            1194196216985169951,
            1211715677497331732,
            1195014108085489866,
            1196006750403440710,
            1196008739665358858,
            1194281783659864114
        ],
        1281155099590135878: [
            1194533745286451271,
            "❤️",
            1194196216985169951,
            1194196752803315772,
            1195014108085489866,
            1211715677497331732,
            1279164617117143113
        ],
        1281155158922760273: [
            1194533745286451271,
            1194196216985169951,
            1211715677497331732,
            1195014108085489866,
            1196006750403440710,
            1196008739665358858,
            1194281783659864114
        ],
        1281155174253199444: [
            1194533745286451271,
            "❤️",
            1194196216985169951,
            1194196752803315772,
            1195014108085489866,
            1211715677497331732,
            1279164617117143113
        ],
        1281155289625923676: [
            1194533745286451271,
            1194196216985169951,
            1211715677497331732,
            1195014108085489866,
            1196006750403440710,
            1196008739665358858,
            1194281783659864114
        ],
        1281155308684574723: [
            1194533745286451271,
            "❤️",
            1194196216985169951,
            1194196752803315772,
            1195014108085489866,
            1211715677497331732,
            1279164617117143113
        ]
    }

    print("========== FINAL FORM START ==========")
    semaphore = asyncio.Semaphore(1)
    async def limited_process(cid, eids):
        async with semaphore:
            await process_channel(bot, cid, eids)

    tasks = [limited_process(cid, eids) for cid, eids in react_config.items()]
    await asyncio.gather(*tasks)

    print("========== FINAL FORM DONE ==========")

@bot.command()
async def allem(ctx):
    await ctx.message.delete()
    print("Tong emoji trong server:", len(ctx.guild.emojis))

    for em in ctx.guild.emojis:
        print(em.name, em.id)

farm_exp = False
@bot.command(aliases=["se"])
async def startexp(ctx):
    await ctx.message.delete()
    global farm_exp
    farm_exp = True
    channel = bot.get_channel(1381302690335952988)

    emoji_list = [em for em in ctx.guild.emojis if not em.animated]

    print("===== BAT DAU CAY EXP =====")
    print("Emoji thuong load duoc:", len(emoji_list))

    while farm_exp:
        try:
            so_luong = random.randint(1, 1)
            chosen = random.sample(emoji_list, so_luong)
            text = "".join(str(em) for em in chosen)
            await channel.send(text)
            print("Da gui:", text)
        except Exception as e:
            print("Loi gui:", e)
        await asyncio.sleep(random.randint(60, 90))

@bot.command(aliases=["xe"])
async def stopexp(ctx):
    await ctx.message.delete()
    global farm_exp
    farm_exp = False
    print("===== DA DUNG CAY EXP =====")

keep_alive()
bot.run(TOKEN, bot = False)
