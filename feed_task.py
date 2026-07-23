import json
import os
import asyncio
import random
import re
import urllib.parse
import discord
from discord.ext import commands, tasks
import io
import aiohttp
from bs4 import BeautifulSoup

BOT_GAME_ID = 1228264831870701648

FEED_CHANNEL_IDS = [
    1292304060342603840
]

IS_FEED_ENABLED = True

GEMINI_API_KEY = "AQ.Ab8RN6Jr_iO3darmmR2vZpxrWTlbEBrAfwx920oxJo-z18DG7A"

def clean_final_answer(text):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = re.sub(r'\[[^\]]*\]', ' ', text)
    text = re.sub(r'[/_\\\-]', ' ', text)
    text = re.sub(r'[^\w\sàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệiíìỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđĐ]', '', text)
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

async def ask_gemini_api(clean_question):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"Đây là một câu hỏi đố vui trong game Genshin Impact/Anime: '{clean_question}'. Hãy chỉ trả lời đúng duy nhất TÊN CỦA ĐÁP ÁN (1 đến 3 từ), không giải thích, không thêm dấu chấm câu, không đưa thêm từ thừa."
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        print("🤖 [GEMINI AI] Đang gửi câu hỏi cho Gemini...", flush=True)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=5) as res:
                if res.status == 200:
                    data = await res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_response = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                        ans = clean_final_answer(text_response)
                        if ans:
                            return ans
    except Exception:
        pass
    return None

async def fetch_fandom_api(clean_question):
    url = f"https://genshin-impact.fandom.com/vi/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_question)}&format=json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        print("🌐 [FANDOM API] Đang truy vấn Fandom Wiki...", flush=True)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=4) as res:
                if res.status == 200:
                    data = await res.json()
                    search_results = data.get("query", {}).get("search", [])
                    for item in search_results:
                        snippet = item.get("snippet", "")
                        clean_snippet = re.sub(r'<[^>]+>', '', snippet)
                        
                        quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', clean_snippet)
                        if quoted_matches:
                            ans = clean_final_answer(quoted_matches[0])
                            if ans and len(ans.split()) <= 4:
                                return ans
    except Exception:
        pass
    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"\n==================== [ BẮT ĐẦU GIẢI ĐỐ ] ====================", flush=True)
    print(f"🔍 [SEARCH] Câu hỏi đã trích xuất: {clean_question}", flush=True)

    ans_gemini = await ask_gemini_api(clean_question)
    if ans_gemini:
        print(f"✅ [KẾT QUẢ GEMINI AI]: {ans_gemini}\n============================================================\n", flush=True)
        return ans_gemini

    ans_fandom = await fetch_fandom_api(clean_question)
    if ans_fandom:
        print(f"✅ [KẾT QUẢ FANDOM]: {ans_fandom}\n============================================================\n", flush=True)
        return ans_fandom

    print("❌ [KẾT QUẢ]: Thất bại toàn bộ các nguồn.\n============================================================\n", flush=True)
    return None

@tasks.loop(hours=4, minutes=30)
async def auto_feed_loop(bot_instance):
    if not IS_FEED_ENABLED:
        return

    chosen_channel_id = random.choice(FEED_CHANNEL_IDS)
    channel = bot_instance.get_channel(chosen_channel_id)
    
    if channel:
        try:
            if auto_feed_loop.current_loop > 0:
                extra_wait = random.randint(60, 300)
                await asyncio.sleep(extra_wait)
            
            if not IS_FEED_ENABLED:
                return

            await channel.send(".feed")
            
        except Exception:
            pass

async def setup_message_listener(bot_instance):
    @bot_instance.event
    async def on_message(message):
        global IS_FEED_ENABLED

        if message.content == "!feed off":
            IS_FEED_ENABLED = False
            await message.reply("🛑 Đã tạm dừng vòng lặp tự động gửi `.feed`.")
            return

        if message.content == "!feed on":
            IS_FEED_ENABLED = True
            await message.reply("🌾 Đã bắt đầu lại vòng lặp tự động gửi `.feed`.")
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
                answer = await solve_question(question_text)
                if answer:
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    await message.reply(answer)
                else:
                    print("⚠️ [FEED] Không thể trích xuất được đáp án chính xác.", flush=True)

def start_feed_task(bot):
    asyncio.create_task(setup_message_listener(bot))
    
    @auto_feed_loop.before_loop
    async def before_auto_feed():
        await bot.wait_until_ready()
        
    if not auto_feed_loop.is_running():
        auto_feed_loop.start(bot)
