import json
import os
import asyncio
import random
import re
import urllib.parse
import requests
import pytz
import discord
from discord.ext import commands, tasks
from datetime import datetime
import io
from bs4 import BeautifulSoup

BOT_GAME_ID = 1381506157591527464

FEED_CHANNEL_IDS = [
    1214564167520886804
]

IS_FEED_ENABLED = True

def is_valid_time():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    return 8 <= now.hour < 22

def clean_final_answer(text):
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'[^a-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s\-_]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

async def google_search_answer(question_text):
    try:
        lines = [line.strip() for line in question_text.split('\n') if line.strip()]
        if not lines:
            return None
            
        clean_question = lines[0]
        clean_question = re.sub(r'\*\*|__', '', clean_question)
        
        print(f"🔍 [GOOGLE] Đang tìm kiếm từ in đậm cho câu hỏi: {clean_question}", flush=True)

        query = urllib.parse.quote_plus(clean_question)
        url = f"https://www.google.com/search?q={query}&hl=vi"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as res:
                if res.status == 200:
                    html_text = await res.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
                    
                    for bold_tag in soup.find_all(['em', 'strong', 'b']):
                        bold_text = bold_tag.get_text().strip()
                        cleaned = clean_final_answer(bold_text)
                        if cleaned and cleaned.lower() not in clean_question.lower():
                            words = cleaned.split()
                            if 1 <= len(words) <= 4:
                                return cleaned

                    for g_item in soup.find_all('div', class_='VwiC3b'):
                        snippet_text = g_item.get_text().strip()
                        match = re.search(r'(?:có tên là|tên là|gọi là|chính là|là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠ][a-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s\(\)\[\]]+)', snippet_text)
                        if match:
                            raw_ans = match.group(1).strip()
                            final_ans = clean_final_answer(raw_ans)
                            words = final_ans.split()
                            if 1 <= len(words) <= 4:
                                return final_ans

    except Exception as e:
        print(f"❌ [GOOGLE] Lỗi trích xuất từ in đậm: {e}", flush=True)
        
    return None

@tasks.loop(hours=4, minutes=30)
async def auto_feed_loop(bot_instance):
    if not IS_FEED_ENABLED:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Vòng lặp .feed đang tạm dừng.", flush=True)
        return

    if not is_valid_time():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Ngoài khung giờ hoạt động (8h-22h). Bỏ qua lượt này.", flush=True)
        return

    chosen_channel_id = random.choice(FEED_CHANNEL_IDS)
    channel = bot_instance.get_channel(chosen_channel_id)
    
    if channel:
        try:
            if auto_feed_loop.current_loop > 0:
                extra_wait = random.randint(60, 300)
                print(f"--- Đang chờ {extra_wait}s trước khi farm đợt tiếp theo ---", flush=True)
                await asyncio.sleep(extra_wait)
            
            if not IS_FEED_ENABLED:
                return

            await channel.send(".feed")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌾 Đã gửi .feed vào kênh ngẫu nhiên: {chosen_channel_id}", flush=True)
            
        except discord.errors.HTTPException as e:
            print(f"🚫 Lỗi Discord: {e}", flush=True)
        except Exception as e:
            print(f"❌ Lỗi khi farm: {e}", flush=True)
    else:
        print(f"❌ Không tìm thấy hoặc thiếu quyền xem kênh: {chosen_channel_id}", flush=True)

async def setup_message_listener(bot_instance):
    @bot_instance.event
    async def on_message(message):
        global IS_FEED_ENABLED

        if message.content == "!feed off":
            IS_FEED_ENABLED = False
            await message.reply("🛑 Đã tạm dừng vòng lặp tự động gửi `.feed`.")
            print("⚙️ [HỆ THỐNG] Vòng lặp .feed đã chuyển sang: TẠM DỪNG.", flush=True)
            return

        if message.content == "!feed on":
            IS_FEED_ENABLED = True
            await message.reply("🌾 Đã bắt đầu lại vòng lặp tự động gửi `.feed`.")
            print("⚙️ [HỆ THỐNG] Vòng lặp .feed đã chuyển sang: HOẠT ĐỘNG.", flush=True)
            return

        if message.channel.id not in FEED_CHANNEL_IDS:
            return

        if message.author.id == BOT_GAME_ID and message.embeds:
            embed = message.embeds[0]
            title = embed.title if embed.title else ""
            description = embed.description if embed.description else ""
            
            if "CÂU HỎI FEED" in title or "Reply trực tiếp" in description:
                print(f"🎯 [BOT GAME] Phát hiện câu hỏi tại kênh {message.channel.id}: {description}", flush=True)
                
                answer = await google_search_answer(description)
                
                if answer:
                    await asyncio.sleep(random.uniform(3.0, 5.0))
                    await message.reply(answer)
                    print(f"✅ [FEED] Đã tự động phản hồi đáp án tìm thấy: {answer}", flush=True)
                else:
                    print("⚠️ [FEED] Không thể trích xuất được đáp án chính xác từ Google.", flush=True)

def start_feed_task(bot):
    asyncio.create_task(setup_message_listener(bot))
    
    @auto_feed_loop.before_loop
    async def before_auto_feed():
        await bot.wait_until_ready()
        
    if not auto_feed_loop.is_running():
        auto_feed_loop.start(bot)
