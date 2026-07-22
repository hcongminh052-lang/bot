import json
import os
import asyncio
import random
import re
import urllib.parse
import pytz
import discord
from discord.ext import commands, tasks
from datetime import datetime
import io
import aiohttp
from bs4 import BeautifulSoup

BOT_GAME_ID = 1228264831870701648

FEED_CHANNEL_IDS = [
    1292304060342603840
]

IS_FEED_ENABLED = True

def is_valid_time():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    return 8 <= now.hour < 22

def clean_final_answer(text):
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'[^a-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s\-_,]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_real_question(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        if '?' in line and not line.startswith('💬') and not line.startswith('↩️'):
            clean_line = re.sub(r'\*\*|__|[*_`]', '', line)
            return clean_line.strip()
            
    for line in lines:
        if not line.startswith('💬') and not line.startswith('↩️') and "Reply" not in line:
            clean_line = re.sub(r'\*\*|__|[*_`]', '', line)
            return clean_line.strip()
            
    return None

async def duckduckgo_search_answer(clean_question):
    url = "https://lite.duckduckgo.com/lite/"
    data = {"q": clean_question}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers, timeout=5) as res:
                if res.status == 200:
                    html_text = await res.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
                    
                    for td in soup.find_all('td', class_='result-snippet'):
                        snippet_text = td.get_text().strip()
                        match = re.search(r'(?:có tên là|tên là|gọi là|chính là|là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠ][a-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s\(\)\[\]]+)', snippet_text)
                        if match:
                            raw_ans = match.group(1).strip()
                            final_ans = clean_final_answer(raw_ans)
                            words = final_ans.split()
                            if 1 <= len(words) <= 5:
                                return final_ans
    except Exception as e:
        print(f"❌ [DDG] Lỗi trích xuất: {e}", flush=True)
        
    return None

async def ask_free_ai(clean_question):
    prompt = f"Trả lời cực kỳ ngắn gọn. Chỉ trả về duy nhất tên/đáp án. Câu hỏi: {clean_question}"
    url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=7) as res:
                if res.status == 200:
                    raw_response = await res.text()
                    match = re.search(r'(?:có tên là|tên là|gọi là|chính là|là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠ][a-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s]+)', raw_response)
                    if match:
                        raw_response = match.group(1)
                        
                    answer = clean_final_answer(raw_response)
                    words = answer.split()
                    if 1 <= len(words) <= 6:
                        return answer
    except Exception as e:
        print(f"❌ [FREE AI] Lỗi truy vấn AI Service: {e}", flush=True)
        
    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"🔍 [SEARCH] Đang xử lý câu hỏi: {clean_question}", flush=True)
    
    ans = await duckduckgo_search_answer(clean_question)
    if ans:
        print(f"✅ [DDG] Tìm thấy đáp án từ DuckDuckGo: {ans}", flush=True)
        return ans
        
    print("⚠️ [DDG] Không tìm thấy, chuyển sang AI fallback...", flush=True)
    return await ask_free_ai(clean_question)

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

        if message.author.id == BOT_GAME_ID:
            question_text = ""
            if message.embeds:
                embed = message.embeds[0]
                question_text = embed.description if embed.description else (embed.title if embed.title else "")
            else:
                question_text = message.content

            if question_text:
                print(f"🎯 [BOT GAME] Phát hiện câu hỏi tại kênh {message.channel.id}: {question_text}", flush=True)
                
                answer = await solve_question(question_text)
                
                if answer:
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    await message.reply(answer)
                    print(f"✅ [FEED] Đã tự động phản hồi đáp án tìm thấy: {answer}", flush=True)
                else:
                    print("⚠️ [FEED] Không thể trích xuất được đáp án chính xác.", flush=True)

def start_feed_task(bot):
    asyncio.create_task(setup_message_listener(bot))
    
    @auto_feed_loop.before_loop
    async def before_auto_feed():
        await bot.wait_until_ready()
        
    if not auto_feed_loop.is_running():
        auto_feed_loop.start(bot)
