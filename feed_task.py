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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COHERE_API_KEY = "cohere_zJai2mbS3aUXjpb9DrRZSEnBctXbunyl3FooG9mP4Il2Cg"

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

def parse_best_answer(raw_text):
    if not raw_text:
        return None
        
    text = re.sub(r'\*\*|__|\*|_|`', '', raw_text).strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    target_text = lines[0] if lines else text
    
    match = re.search(r'(?:là|có tên là|tên là|gọi là|chính là|đáp án|đáp án là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠa-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s\-_,]{3,})', target_text, re.IGNORECASE)
    if match:
        target_text = match.group(1).strip()
        
    cleaned = clean_final_answer(target_text)
    cleaned = re.sub(r'^(đáp án(?: là)?|tên(?: là)?|gọi(?: là)?|chính(?: là)?|là|món(?: ăn)?)\s+', '', cleaned, flags=re.IGNORECASE).strip()
    
    words = cleaned.split()
    
    if 1 <= len(words) <= 6 and len(cleaned) >= 3:
        return cleaned
    elif len(words) > 6:
        return " ".join(words[:4])
        
    return None

async def ask_cohere_api(clean_question):
    if not COHERE_API_KEY:
        return None

    url = "https://api.cohere.com/v1/chat"
    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "command-r-plus",
        "message": f"Trả lời câu hỏi game sau. CHỈ XUẤT DUY NHẤT TÊN/ĐÁP ÁN (1-4 từ), không viết câu, không giải thích:\n\n{clean_question}",
        "temperature": 0.1
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=5) as res:
                if res.status == 200:
                    data = await res.json()
                    raw_text = data.get("text", "").strip()
                    return parse_best_answer(raw_text)
                else:
                    print(f"  └─ ⚠️ [COHERE API] HTTP Status: {res.status}", flush=True)
    except Exception as e:
        print(f"  └─ ❌ [COHERE API ERROR]: {e}", flush=True)

    return None

async def ask_gemini_rest(clean_question):
    if not GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"Trả lời câu hỏi game sau. CHỈ XUẤT DUY NHẤT TÊN/ĐÁP ÁN (1-4 từ), không viết câu:\n\n{clean_question}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=5) as res:
                if res.status == 200:
                    data = await res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                        return parse_best_answer(raw_text)
                elif res.status == 429:
                    print("  └─ ⚠️ [GEMINI REST] Bị Rate Limit (429)", flush=True)
    except Exception as e:
        print(f"  └─ ❌ [GEMINI REST ERROR]: {e}", flush=True)

    return None

async def ask_duckduckgo_web(clean_question):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(clean_question)}"
    print(f"🌐 [DDG WEB] Đang tìm kiếm trên Web...", flush=True)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=6) as res:
                if res.status == 200:
                    html_text = await res.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
                    snippets = soup.find_all('a', class_='result__snippet')
                    combined_text = " ".join([s.get_text() for s in snippets[:4]])
                    
                    if combined_text:
                        match = re.search(r'(?:là|có tên là|tên là|món ăn đặc biệt(?: của [^là]+)? là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠa-zA-Z0-9ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư\s\-_,]{3,})', combined_text, re.IGNORECASE)
                        if match:
                            raw_found = match.group(1).strip()
                            cleaned = clean_final_answer(raw_found)
                            cleaned = re.sub(r'^(món|là|của)\s+', '', cleaned, flags=re.IGNORECASE).strip()
                            words = cleaned.split()
                            if 1 <= len(words) <= 5 and len(cleaned) >= 3:
                                return cleaned
    except Exception as e:
        print(f"  └─ ❌ [DDG WEB ERROR]: {e}", flush=True)
        
    return None

async def ask_pollinations_fallback(clean_question):
    prompt = f"Trả lời câu hỏi game: {clean_question}. CHỈ XUẤT ĐÁP ÁN (1 đến 4 từ)."
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://text.pollinations.ai/{encoded_prompt}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=6) as res:
                if res.status == 200:
                    raw_text = await res.text()
                    return parse_best_answer(raw_text)
    except Exception:
        pass
                
    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"\n==================== [ BẮT ĐẦU GIẢI ĐỐ ] ====================", flush=True)
    print(f"🔍 [SEARCH] Câu hỏi đã trích xuất: {clean_question}", flush=True)

    ans_cohere = await ask_cohere_api(clean_question)
    if ans_cohere:
        print(f"✅ [KẾT QUẢ COHERE]: {ans_cohere}\n============================================================\n", flush=True)
        return ans_cohere

    ans_gemini = await ask_gemini_rest(clean_question)
    if ans_gemini:
        print(f"✅ [KẾT QUẢ GEMINI]: {ans_gemini}\n============================================================\n", flush=True)
        return ans_gemini

    print("⚠️ [FALLBACK] Chuyển sang DuckDuckGo Web Search...", flush=True)
    ans_ddg = await ask_duckduckgo_web(clean_question)
    if ans_ddg:
        print(f"✅ [KẾT QUẢ DDG WEB]: {ans_ddg}\n============================================================\n", flush=True)
        return ans_ddg

    print("⚠️ [FALLBACK] Chuyển sang Pollinations AI...", flush=True)
    ans_fallback = await ask_pollinations_fallback(clean_question)
    if ans_fallback:
        print(f"✅ [KẾT QUẢ POLLINATIONS]: {ans_fallback}\n============================================================\n", flush=True)
        return ans_fallback
        
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
