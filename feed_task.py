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

GEMINI_KEYS_RAW = os.getenv("GEMINI_API_KEYS", "AIzaSy_KEY1, AIzaSy_KEY2, AIzaSy_KEY3")
GEMINI_API_KEYS = [k.strip() for k in GEMINI_KEYS_RAW.split(",") if k.strip() and "KEY" not in k]

GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b"
]

ANSWER_CACHE = {}

BAD_WORDS = ["nhân v", "nhân vật", "hình ảnh", "kết quả", "trả lời", "câu hỏi", "thông tin", "được biết", "xem thêm", "genshin", "impact", "wiki", "fandom"]

def clean_final_answer(text):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
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

def parse_extracted_phrase(raw_found):
    if not raw_found:
        return None
        
    cleaned = clean_final_answer(raw_found)
    cleaned = re.sub(r'^(?:món|món ăn|là|của|tên là|có tên là)\s+', '', cleaned, flags=re.IGNORECASE).strip()
    
    if any(bad in cleaned.lower() for bad in BAD_WORDS):
        return None

    words = cleaned.split()
    if 1 <= len(words) <= 5 and len(cleaned) >= 2:
        return cleaned
    elif len(words) > 5:
        return " ".join(words[:3])
        
    return None

def parse_best_answer(raw_text):
    if not raw_text:
        return None
        
    print(f"  ├─ 📄 [GEMINI RAW RESPONSE]: {repr(raw_text)}", flush=True)
    
    text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    
    quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', text)
    for match in quoted_matches:
        cleaned_quote = clean_final_answer(match)
        if 1 <= len(cleaned_quote.split()) <= 6:
            return cleaned_quote

    text = re.sub(r'\*\*|__|\*|_|`', '', text).strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    filtered_lines = []
    for line in lines:
        lower_line = line.lower()
        if any(lower_line.startswith(prefix) for prefix in [
            "the user", "here is", "based on", "the answer", "câu trả lời", "đáp án", "theo tôi"
        ]):
            continue
        filtered_lines.append(line)
        
    target_text = filtered_lines[0] if filtered_lines else (lines[0] if lines else text)
    target_text = re.sub(r'^(?:đáp án|câu trả lời|kết quả|tên món ăn)(?: là)?:\s*', '', target_text, flags=re.IGNORECASE)
    
    cleaned = clean_final_answer(target_text)
    words = cleaned.split()
    
    if 1 <= len(words) <= 6 and len(cleaned) >= 2:
        return cleaned
    elif len(words) > 6:
        return " ".join(words[:4])
        
    return None

async def ask_duckduckgo_web_search(clean_question):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(clean_question)}"
    
    try:
        print("🌐 [DDG WEB] Đang cào dữ liệu Google/DDG Search...", flush=True)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=6) as res:
                if res.status == 200:
                    html_text = await res.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
                    results = soup.find_all('div', class_='result')
                    
                    for result in results:
                        title_tag = result.find('a', class_='result__title')
                        snippet_tag = result.find('a', class_='result__snippet')
                        
                        title_text = title_tag.get_text().strip() if title_tag else ""
                        snippet_text = snippet_tag.get_text().strip() if snippet_tag else ""
                        
                        quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', title_text)
                        for match in quoted_matches:
                            ans = parse_extracted_phrase(match)
                            if ans and ans.lower() not in ["genshin impact", "furina", "fandom"]:
                                return ans
                                
                        if '|' in title_text:
                            possible_name = title_text.split('|')[0].strip()
                            ans = parse_extracted_phrase(possible_name)
                            if ans and ans.lower() not in ["genshin impact", "furina", "fandom"]:
                                return ans

                        match = re.search(r'(?:là|có tên là|tên là)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠa-zA-Z0-9\s\-_]{2,25})', snippet_text, re.IGNORECASE)
                        if match:
                            ans = parse_extracted_phrase(match.group(1))
                            if ans:
                                return ans
    except Exception as e:
        print(f"  └─ ❌ [DDG WEB EXCEPTION]: {e}", flush=True)
        
    return None

async def ask_gemini_api(clean_question):
    if not GEMINI_API_KEYS:
        print("  └─ ⚠️ [GEMINI] Chưa cấu hình danh sách GEMINI_API_KEYS.", flush=True)
        return None

    if clean_question in ANSWER_CACHE:
        print(f"  ├─ ⚡ [CACHE HIT]: Lấy đáp án từ bộ nhớ tạm -> {ANSWER_CACHE[clean_question]}", flush=True)
        return ANSWER_CACHE[clean_question]

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": "Bạn là hệ thống giải đố trắc nghiệm. Nhiệm vụ duy nhất: Trả lời NGẮN GỌN BẰNG TIẾNG VIỆT chính xác tên entity/đáp án (từ 1 đến 4 từ). KHÔNG giải thích, KHÔNG viết tiếng Anh, KHÔNG chào hỏi, KHÔNG lặp lại câu hỏi."
                }
            ]
        },
        "contents": [
            {
                "parts": [
                    {
                        "text": f"Câu hỏi: {clean_question}\nĐáp án chính xác:"
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 40
        }
    }

    for key_idx, api_key in enumerate(GEMINI_API_KEYS, start=1):
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            for retry in range(3):
                try:
                    print(f"🌐 [GEMINI API] Key #{key_idx} | Model: {model} | Retry: {retry}", flush=True)
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload, timeout=10) as res:
                            print(f"  ├─ 📥 [HTTP STATUS]: {res.status}", flush=True)
                            
                            if res.status == 200:
                                data = await res.json()
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts:
                                        raw_text = parts[0].get("text", "").strip()
                                        ans = parse_best_answer(raw_text)
                                        if ans:
                                            ANSWER_CACHE[clean_question] = ans
                                            return ans
                            elif res.status == 429:
                                wait_time = (2 ** retry) + random.uniform(0.5, 1.5)
                                print(f"  ├─ ⚠️ [RATE LIMIT 429]: Chờ {wait_time:.1f}s trước khi đổi key/thử lại...", flush=True)
                                await asyncio.sleep(wait_time)
                                if retry == 2:
                                    break
                            else:
                                err_text = await res.text()
                                print(f"  └─ ⚠️ [GEMINI ERR BODY]: {err_text[:150]}", flush=True)
                                break
                except Exception as e:
                    print(f"  └─ ❌ [GEMINI EXCEPTION]: {type(e).__name__} - {e}", flush=True)
                    break

    return None

async def solve_question(question_text):
    clean_question = extract_real_question(question_text)
    if not clean_question:
        return None
        
    print(f"\n==================== [ BẮT ĐẦU GIẢI ĐỐ ] ====================", flush=True)
    print(f"🔍 [SEARCH] Câu hỏi đã trích xuất: {clean_question}", flush=True)

    ans_gemini = await ask_gemini_api(clean_question)
    if ans_gemini:
        print(f"✅ [KẾT QUẢ GEMINI]: {ans_gemini}\n============================================================\n", flush=True)
        return ans_gemini

    ans_ddg = await ask_duckduckgo_web_search(clean_question)
    if ans_ddg:
        print(f"✅ [KẾT QUẢ DDG WEB]: {ans_ddg}\n============================================================\n", flush=True)
        return ans_ddg

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
