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

DEFAULT_KEYS = "AQ.Ab8RN6JhfU1IlDhs0UNCTJ3mgquJO9dJ5ZkWvJnylt2uH_lvwg, AQ.Ab8RN6J5Bt7pWbBmjGrSQzahbDdpYNBb34povPscYHIFhKg62A, AQ.Ab8RN6Jr_iO3darmmR2vZpxrWTlbEBrAfwx920oxJo-z18DG7A"
GEMINI_KEYS_RAW = os.getenv("GEMINI_API_KEYS", DEFAULT_KEYS)
GEMINI_API_KEYS = [k.strip() for k in GEMINI_KEYS_RAW.split(",") if k.strip() and "KEY1" not in k and "KEY2" not in k]

FALLBACK_GEMINI_MODELS = [
    "models/gemini-2.0-flash",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-flash-8b",
    "models/gemini-1.5-pro"
]

BAD_WORDS = ["nhân v", "nhân vật", "hình ảnh", "kết quả", "trả lời", "câu hỏi", "thông tin", "được biết", "xem thêm", "wiki", "fandom", "wikipedia", "big three", "heisei"]

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

def parse_extracted_phrase(raw_found):
    if not raw_found:
        return None
        
    cleaned = clean_final_answer(raw_found)
    cleaned = re.sub(r'^(?:món|món ăn|là|của|tên là|có tên là)\s+', '', cleaned, flags=re.IGNORECASE).strip()
    
    words = cleaned.split()
    if not words:
        return None
        
    if any(bad in cleaned.lower() for bad in BAD_WORDS):
        return None

    if 1 <= len(words) <= 5 and len(cleaned) >= 2:
        return cleaned
    elif len(words) > 5:
        return " ".join(words[:3])
        
    return None

async def fetch_allowed_gemini_models(session, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        async with session.get(url, timeout=5) as res:
            if res.status == 200:
                data = await res.json()
                valid_models = []
                for m in data.get("models", []):
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        model_name = m.get("name", "")
                        if model_name:
                            valid_models.append(model_name)
                if valid_models:
                    return valid_models
    except Exception:
        pass
    return FALLBACK_GEMINI_MODELS

async def ask_gemini_api(clean_question):
    if not GEMINI_API_KEYS:
        print("⚠️ [GEMINI API] Không tìm thấy API Key nào trong danh sách.", flush=True)
        return None

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"Đây là câu hỏi đố vui: '{clean_question}'. Hãy suy luận chính xác và trả lời CHÍNH XÁC duy nhất TÊN CỦA ĐÁP ÁN (từ 1 đến 4 từ). Không viết thêm bất kỳ từ thừa nào."
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 30
        }
    }

    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        for key_index, api_key in enumerate(GEMINI_API_KEYS, start=1):
            allowed_models = await fetch_allowed_gemini_models(session, api_key)
            print(f"📋 [GEMINI API] Key #{key_index} phát hiện {len(allowed_models)} mô hình khả dụng.", flush=True)

            for model_path in allowed_models:
                formatted_model = model_path if model_path.startswith("models/") else f"models/{model_path}"
                url = f"https://generativelanguage.googleapis.com/v1beta/{formatted_model}:generateContent?key={api_key}"
                try:
                    print(f"🌐 [GEMINI API] Thử Key #{key_index} - Model {formatted_model}...", flush=True)
                    async with session.post(url, json=payload, headers=headers, timeout=6) as res:
                        if res.status == 200:
                            data = await res.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    raw_text = parts[0].get("text", "").strip()
                                    ans = clean_final_answer(raw_text)
                                    if ans:
                                        return ans
                        else:
                            err_body = await res.text()
                            print(f"⚠️ [GEMINI API] Lỗi HTTP {res.status}: {err_body[:100]}", flush=True)
                except Exception as e:
                    print(f"❌ [GEMINI API ERROR]: {e}", flush=True)

    return None

async def fetch_wikipedia_api(clean_question):
    keywords = re.sub(r'^(?:cho tôi biết|bạn có biết|hãy cho biết|từng|đã)\s+', '', clean_question, flags=re.IGNORECASE)
    search_q = urllib.parse.quote(keywords)
    url = f"https://vi.wikipedia.org/w/api.php?action=query&list=search&srsearch={search_q}&format=json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        print("🌐 [WIKIPEDIA API] Đang tra cứu Wikipedia...", flush=True)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=4) as res:
                if res.status == 200:
                    data = await res.json()
                    search_results = data.get("query", {}).get("search", [])
                    for item in search_results:
                        snippet = item.get("snippet", "")
                        clean_snippet = re.sub(r'<[^>]+>', '', snippet)
                        
                        match = re.search(r'(?:học viện|trường|món ăn)\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠa-zA-Z0-9\s]{2,20})', clean_snippet, re.IGNORECASE)
                        if match:
                            ans = parse_extracted_phrase(match.group(0))
                            if ans:
                                return ans
    except Exception:
        pass
    return None

async def fetch_web_search(clean_question):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    
    search_q = clean_question

    searx_instances = [
        "https://searx.be/search",
        "https://searx.tiekoetter.com/search",
        "https://search.mdosch.de/search"
    ]
    
    print("🌐 [WEB SEARCH] Đang tìm kiếm tổng hợp trên Web...", flush=True)
    async with aiohttp.ClientSession() as session:
        for instance in searx_instances:
            try:
                params = {"q": search_q, "format": "json"}
                async with session.get(instance, params=params, headers=headers, timeout=5) as res:
                    if res.status == 200:
                        data = await res.json()
                        results = data.get("results", [])
                        for result in results:
                            snippet_text = result.get("content", "")
                            title_text = result.get("title", "")
                            
                            quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', title_text + " " + snippet_text)
                            for match in quoted_matches:
                                ans = parse_extracted_phrase(match)
                                if ans:
                                    return ans
            except Exception:
                continue
                
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            payload = {"q": search_q, "b": ""}
            async with session.post(ddg_url, data=payload, headers=headers, timeout=5) as res:
                if res.status == 200:
                    html_text = await res.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
                    for result in soup.find_all('div', class_='result'):
                        snippet_tag = result.find('a', class_='result__snippet')
                        snippet_text = snippet_tag.get_text().strip() if snippet_tag else ""
                        
                        quoted_matches = re.findall(r'["\'«“](.*?)["\'»”]', snippet_text)
                        for match in quoted_matches:
                            ans = parse_extracted_phrase(match)
                            if ans:
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

    ans_wiki = await fetch_wikipedia_api(clean_question)
    if ans_wiki:
        print(f"✅ [KẾT QUẢ WIKIPEDIA]: {ans_wiki}\n============================================================\n", flush=True)
        return ans_wiki

    ans_web = await fetch_web_search(clean_question)
    if ans_web:
        print(f"✅ [KẾT QUẢ WEB SEARCH]: {ans_web}\n============================================================\n", flush=True)
        return ans_web

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
