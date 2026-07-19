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
from googlesearch import search
from bs4 import BeautifulSoup
import io

BOT_GAME_ID = 1381506157591527464

FEED_CHANNEL_IDS = [
    1214564167520886804
]

def is_valid_time():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    return 8 <= now.hour < 22

def google_search_answer(question_text):
    clean_question = re.sub(r'hay reply trực tiếp.*', '', question_text, flags=re.IGNORECASE).strip()
    print(f"🔍 [GOOGLE] Đang tra cứu từ khóa: {clean_question}", flush=True)
    
    keywords = ["Fontaine", "Mondstadt", "Liyue", "Inazuma", "Sumeru", "Natlan", "Snezhnaya", "Khaenri'ah"]
    
    for kw in keywords:
        if kw.lower() in clean_question.lower():
            return kw
    try:
        search_query = f"{clean_question} Genshin Impact wiki"
        urls = list(search(search_query, num_results=3, lang="vi"))
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        for url in urls:
            try:
                res = requests.get(url, headers=headers, timeout=4)
                if res.status == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    page_text = soup.get_text().lower()
                    
                    for kw in keywords:
                        if kw.lower() in page_text:
                            return kw
            except Exception:
                continue
    except Exception as e:
        print(f"❌ [GOOGLE] Lỗi khi thực hiện tra cứu: {e}", flush=True)
        
    return None

@tasks.loop(hours=4, minutes=30)
async def auto_feed_loop(bot_instance):
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
        if message.channel.id not in FEED_CHANNEL_IDS:
            return

        if message.author.id == BOT_GAME_ID and message.embeds:
            embed = message.embeds[0]
            title = embed.title if embed.title else ""
            description = embed.description if embed.description else ""
            
            if "CÂU HỎI FEED" in title or "Reply trực tiếp" in description:
                print(f"🎯 [BOT GAME] Phát hiện câu hỏi tại kênh {message.channel.id}: {description}", flush=True)
                
                loop = asyncio.get_event_loop()
                answer = await loop.run_in_executor(None, google_search_answer, description)
                
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
